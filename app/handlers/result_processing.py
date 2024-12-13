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

    def _reduce_df_to_statistics(self, df: pl.DataFrame) -> pl.DataFrame:
        grouping_columns = [
            c for c in df.columns if c not in ["scenario", "value"]
        ]
        df_min = (
            df.group_by(grouping_columns, maintain_order=True)
            .agg(pl.col("value").min())
            .with_columns(pl.lit("min").alias("scenario"))
        )
        df_max = (
            df.group_by(grouping_columns, maintain_order=True)
            .agg(pl.col("value").max())
            .with_columns(pl.lit("max").alias("scenario"))
        )
        df_mean = (
            df.group_by(grouping_columns, maintain_order=True)
            .agg(pl.col("value").mean())
            .with_columns(pl.lit("mean").alias("scenario"))
        )
        df_std = (
            df.group_by(grouping_columns, maintain_order=True)
            .agg(pl.col("value").std())
            .with_columns(pl.lit("std").alias("scenario"))
        )
        df_median = (
            df.group_by(grouping_columns, maintain_order=True)
            .agg(pl.col("value").quantile(0.50))
            .with_columns(pl.lit("median").alias("scenario"))
        )
        df_statistics = [df_min, df_max, df_mean, df_std, df_median]
        for quantile in [
            5,
            10,
            15,
            20,
            25,
            30,
            35,
            40,
            45,
            55,
            60,
            65,
            70,
            75,
            80,
            85,
            90,
            95,
        ]:
            df_q = (
                df.group_by(grouping_columns, maintain_order=True)
                .agg(pl.col("value").quantile(quantile / 100.0))
                .with_columns(
                    pl.lit(f"p{str(quantile).zfill(2)}").alias("scenario")
                )
            )
            df_statistics.append(df_q)
        return pl.concat(df_statistics)

    def _assemble_simulation_variable_df(
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
                df = self._reduce_df_to_statistics(df)
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
        # Casts String columns to Enum
        string_columns = [
            colname
            for (coltype, colname) in zip(df.dtypes, df.columns)
            if coltype == pl.String
        ]
        string_col_unique_values = {
            c: pl.Enum(df[c].unique()) for c in string_columns
        }
        df = df.with_columns(
            pl.col(c).cast(string_col_unique_values[c]) for c in string_columns
        )
        return df

    def _assemble_policy_variable_df(
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
        # Casts String columns to Enum
        string_columns = [
            colname
            for (coltype, colname) in zip(df.dtypes, df.columns)
            if coltype == pl.String
        ]
        string_col_unique_values = {
            c: pl.Enum(df[c].unique()) for c in string_columns
        }
        df = df.with_columns(
            pl.col(c).cast(string_col_unique_values[c]) for c in string_columns
        )
        return df

    def _assemble_variable_df(
        self, variable_kind: str, var_relative_path: str
    ) -> Union[pl.DataFrame, None]:
        mapping = {
            "policy": self._assemble_policy_variable_df,
            "simulation": self._assemble_simulation_variable_df,
        }
        return mapping[variable_kind](var_relative_path)

    def _export_result_df(self, df: pl.DataFrame, var_name: str):
        result_dir = self._config["target_dir"]
        makedirs(result_dir, exist_ok=True)
        path = join(result_dir, var_name + ".parquet")
        df.write_parquet(path)

    def _handle_variable(
        self, var_kind: str, var_name: str, var_relative_path: str
    ):
        self.log(f"Postprocessing variable {var_name}...")
        df = self._assemble_variable_df(var_kind, var_relative_path)
        if df is not None:
            self._export_result_df(df, var_name)

    def handle(self, config_file: str):
        self._read_json_config(config_file)
        for kind, variables in self._config["variables"].items():
            for name, path in variables.items():
                self._handle_variable(kind, name, path)
