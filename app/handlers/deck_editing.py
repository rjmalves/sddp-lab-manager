import logging
from itertools import product
from logging import INFO
from os import makedirs
from pathlib import Path
from shutil import copytree

import pyjson5


class DeckEditing:
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
        deck_name = Path(self._config["base_case"]).resolve().parts[-1]
        return "_".join((deck_name,) + params)

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

    def handle(self, config_file: str):
        # Reads json config
        self._read_json_config(config_file)
        # Generate params combination
        combinations = self._generate_params_combination()
        # For each combination - copy from source deck
        # and edit deck
        for params in combinations:
            self._copy_and_edit_deck(params)
