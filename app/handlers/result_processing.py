import logging
from logging import INFO
from os import listdir, makedirs
from os.path import isdir, isfile, join
from typing import Union

import polars as pl
import pyjson5


class ResultProcessing:
    def __init__(self) -> None:
        self._logger = logging.getLogger("main")

    def log(self, msg: str, level: int = INFO):
        if self._logger is not None:
            self._logger.log(level, msg)

    def _read_json_config(self, config_file: str) -> dict:
        self.log(f"Reading configuration file [{config_file}]")
        with open(config_file) as f:
            self._config = pyjson5.load(f)

    def _assemble_variable_df(
        self, var_relative_path: str
    ) -> Union[pl.DataFrame, None]:
        dfs: list[pl.DataFrame] = []
        for casename in listdir(self._config["source_dir"]):
            casepath = join(self._config["source_dir"], casename)
            if not isdir(casepath):
                continue
            for methodname in listdir(casepath):
                methodpath = join(casepath, methodname)
                if not isdir(methodpath):
                    continue
                filepath = join(methodpath, var_relative_path)
                if not isfile(filepath):
                    continue
                df = pl.read_parquet(filepath)
                df = df.with_columns(
                    case=pl.lit(casename), method=pl.lit(methodname)
                )
                dfs.append(df)
        if len(dfs) == 0:
            return None
        df = pl.concat(dfs, how="diagonal")
        cols = df.columns
        var_columns = [c for c in cols if c not in ["case", "method"]]
        df = df[["case", "method"] + var_columns]
        return df

    def _export_result_df(self, df: pl.DataFrame, var_name: str):
        result_dir = self._config["target_dir"]
        makedirs(result_dir, exist_ok=True)
        path = join(result_dir, var_name + ".parquet")
        df.write_parquet(path)

    def _handle_variable(self, var_name: str, var_relative_path: str):
        self.log(f"Postprocessing variable {var_name}...")
        df = self._assemble_variable_df(var_relative_path)
        if df is not None:
            self._export_result_df(df, var_name)

    def handle(self, config_file: str):
        self._read_json_config(config_file)
        for name, path in self._config["variables"].items():
            self._handle_variable(name, path)
