import asyncio
import logging
from itertools import product
from logging import INFO
from multiprocessing import Pool, Queue
from os import listdir, makedirs
from pathlib import Path
from shutil import copytree

import pyjson5

from app.utils.log import Log
from app.utils.terminal import run_terminal
from app.utils.timing import time_and_log


class CaseRunning:
    MAIN_FILENAME = "main.jsonc"

    def __init__(self) -> None:
        self._logger = logging.getLogger("main")

    def log(self, msg: str, level: int = INFO):
        if self._logger is not None:
            self._logger.log(level, msg)

    def _read_json_config(self, config_file: str) -> dict:
        self.log(f"Reading configuration file [{config_file}]")
        with open(config_file) as f:
            self._config = pyjson5.load(f)

    def _generate_params_combination(self) -> list[tuple]:
        self._param_order = list(self._config["params"].keys())
        self._param_keys = [
            list(self._config["params"][k].keys()) for k in self._param_order
        ]
        self._combinations = list(product(*self._param_keys))
        self.log(
            f"Generating parameter combinations. Total = {len(self._combinations)}"
        )
        return self._combinations

    def _generate_deck_name(self, params: tuple):
        return "_".join(params)

    def _copy_deck(self, name: str):
        src_path = Path(self._config["base_case"]).resolve()
        dst_path = Path(self._config["target_dir"]).resolve()
        makedirs(dst_path, exist_ok=True)
        copytree(src_path, dst_path.joinpath(name))

    def _read_file(self, path: Path) -> dict:
        with open(path, "r") as f:
            return pyjson5.decode_io(f)

    def _write_file(self, path: Path, data: dict):
        with open(path, "w") as f:
            f.write(pyjson5.encode(data))

    def _recursive_access_and_change_dict(
        self, data: dict, parts: list, content: dict | list
    ):
        tmp_data = data
        for p in parts[:-1]:
            if "[" in p and "]" in p:
                # Access a list at index
                subparts = p.split("[")
                p_name = subparts[0]
                p_idx = int(subparts[1].rstrip("]"))
                tmp_data = tmp_data[p_name][p_idx]
            else:
                # Simply access object
                tmp_data = tmp_data[p]
        tmp_data[parts[-1]] = content

    def _edit_file_with_param_set(
        self, data_filepath: Path, param_name: str, param_content: str
    ):
        data = self._read_file(data_filepath)
        parts = param_name.split("/")
        self._recursive_access_and_change_dict(data, parts, param_content)
        self._write_file(data_filepath, data)

    def _edit_param_set(
        self, main_data: dict, input_path: Path, param_name: str, param_key: str
    ):
        # Access related file
        name_parts = param_name.split("/")
        if name_parts[0] == "files":
            data_filepath = input_path.joinpath(
                main_data["inputs"]["files"][name_parts[1]]
            )
            param_content = self._config["params"][param_name][param_key]
            self._edit_file_with_param_set(
                data_filepath, "/".join(name_parts[2:]), param_content
            )

    def _edit_deck(self, name: str, params: tuple):
        path = Path(self._config["target_dir"]).resolve().joinpath(name)
        main_data = self._read_file(path.joinpath(self.MAIN_FILENAME))
        input_path = path.joinpath(main_data["inputs"]["path"])
        for name, key in zip(self._param_order, params):
            self._edit_param_set(main_data, input_path, name, key)

    def _copy_and_edit_deck(self, params: tuple):
        name = self._generate_deck_name(params)
        self.log(f"Generating deck {name}...")
        self._copy_deck(name)
        self._edit_deck(name, params)

    def _path_for_target_deck_and_entrypoint(
        self, deck_name: str, entrypoint_name: str
    ) -> Path:
        return (
            Path(self._config["target_dir"])
            .resolve()
            .joinpath(deck_name)
            .joinpath(entrypoint_name)
        )

    def _source_deck_names(self) -> list[str]:
        source_path = Path(self._config["source_dir"]).resolve()
        return listdir(source_path)

    def _prepare_decks_for_entrypoints(self):
        # Creates the target dir for each source deck
        source_path = Path(self._config["source_dir"]).resolve()
        for d in self._source_deck_names():
            for name in self._config["entrypoints"].keys():
                copytree(
                    source_path.joinpath(d),
                    self._path_for_target_deck_and_entrypoint(d, name),
                )

    @staticmethod
    def _handle_single_deck(
        q: Queue,
        deck_name: str,
        deck_path: str,
        entrypoint_name: str,
        entrypoint_path: Path,
        environment: str,
        image_name: str,
    ):
        commands = [
            "julia",
            f"--project={environment}",
            f"-J{image_name}",
            str(entrypoint_path),
            deck_path,
        ]
        command_str = " ".join(commands)

        logger_name = f"{deck_name}-{entrypoint_name}"
        logger = Log.configure_process_logger(q, logger_name)
        logger.info(f"Running - {logger_name} - {command_str}")
        try:
            code, _ = asyncio.run(run_terminal(commands))
        except Exception as e:
            code = None
            logger.error(f"[{logger_name}] - Error: {str(e)}")
        logger.info(f"[{logger_name}] - Done: {code}")

    def _handle_decks_for_entrypoint(
        self, q: Queue, entrypoint_name: str, entrypoint_path: Path
    ):
        with time_and_log(
            message_root=f"Time for running {entrypoint_name}",
            logger=self._logger,
        ):
            with Pool(processes=self._config["processes"]) as pool:
                async_res = [
                    pool.apply_async(
                        CaseRunning._handle_single_deck,
                        (
                            q,
                            deck_name,
                            str(
                                self._path_for_target_deck_and_entrypoint(
                                    deck_name, entrypoint_name
                                )
                            ),
                            entrypoint_name,
                            entrypoint_path,
                            self._config["environment"],
                            self._config["image_name"],
                        ),
                    )
                    for deck_name in self._source_deck_names()
                ]
                [r.get(timeout=3600) for r in async_res]

    def handle(self, config_file: str, q: Queue):
        # Reads json config
        self._read_json_config(config_file)
        # Copy decks and prepare directories
        self._prepare_decks_for_entrypoints()
        # Handle each entrypoint
        for name, path in self._config["entrypoints"].items():
            self._handle_decks_for_entrypoint(q, name, Path(path))
