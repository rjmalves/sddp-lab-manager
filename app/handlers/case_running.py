import asyncio
import logging
from logging import INFO
from multiprocessing import Pool, Queue
from os import listdir
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
