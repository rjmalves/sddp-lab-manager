import asyncio
import logging
from dataclasses import dataclass
from itertools import product
from logging import INFO
from multiprocessing import Pool, Queue
from os import listdir
from os.path import join
from pathlib import Path
from shutil import copytree

import pyjson5

from app.utils.log import Log
from app.utils.terminal import run_terminal
from app.utils.timing import time_and_log


@dataclass
class CaseParams:
    entrypoint_name: str
    entrypoint_path: str
    deck_name: str
    deck_path: str


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
        params: CaseParams,
        environment: str,
        image_name: str,
    ):
        commands = [
            "julia",
            f"--project={environment}",
            f"-J{image_name}" if image_name else "",
            str(params.entrypoint_path),
            params.deck_path,
        ]
        command_str = " ".join(commands)

        logger_name = f"{params.deck_name}-{params.entrypoint_name}"
        logger = Log.configure_process_logger(q, logger_name)
        logger.info(f"Running - {logger_name} - {command_str}")
        try:
            code, msg = asyncio.run(run_terminal(commands))
        except Exception as e:
            code = None
            logger.error(f"[{logger_name}] - Error: {str(e)}")
            return
        if code != 0:
            logger.warning(f"[{logger_name}] - {msg}")
        logger.info(f"[{logger_name}] - Done: {code}")
        with open(join(params.deck_path, "echo.log"), "w") as logfile:
            logfile.write(msg)

    def _handle_decks_for_combinations(
        self, q: Queue, params: list[CaseParams]
    ):
        with time_and_log(
            message_root="Time for running",
            logger=self._logger,
        ):
            with Pool(processes=self._config["processes"]) as pool:
                async_res = [
                    pool.apply_async(
                        CaseRunning._handle_single_deck,
                        (
                            q,
                            param,
                            self._config["environment"],
                            self._config["image_name"],
                        ),
                    )
                    for param in params
                ]
                [r.get(timeout=3600) for r in async_res]

    def _generate_deck_entrypoint_combinations(self) -> list[CaseParams]:
        # (entrypoint_name, entrypoint_path, deck_name, deck_path)
        entrypoints = list(
            (name, path) for name, path in self._config["entrypoints"].items()
        )
        deck_names = self._source_deck_names()
        pairs = list(product(entrypoints, deck_names))
        pairs = [
            tuple([
                *p[0],
                p[1],
                str(self._path_for_target_deck_and_entrypoint(p[1], p[0][0])),
            ])
            for p in pairs
        ]
        return [CaseParams(*p) for p in pairs]

    def handle(self, config_file: str, q: Queue):
        # Reads json config
        self._read_json_config(config_file)
        # Copy decks and prepare directories
        self._prepare_decks_for_entrypoints()
        # Generate deck - entrypoint combination
        combinations = self._generate_deck_entrypoint_combinations()
        # Handle each entrypoint
        self._handle_decks_for_combinations(q, combinations)
