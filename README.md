# sddp-lab-manager

Helper CLI app for managing preprocessing, parallel execution and postprocessing tasks associated with Julia projects based on [`SDDPlab`](https://github.com/rjmalves/sddp-lab). Requires python `>= 3.10`.

This application enables the user to:

1. Define a set of replacement macros regarding the input data for generating batches of study cases
2. Handling parallel execution of the generated cases on a set of predefined entrypoints (Julia scripts)
3. Postprocessing all the generated outputs in a small set of files for analytics

## Install

Foi installing the CLI app, one might use pip directly in the cloned repository. Creating a virtual environment (`venv`) in strongly recomended:

```
git clone https://github.com/rjmalves/sddp-lab-manager.git
cd sddp-lab-manager
python3 -m venv ./venv
source ./venv/bin/activate
pip install .
sddp-lab-manager
```

For later usage, one must remember to always activate the environment or to call the entrypoint created during installation:

```
cd sddp-lab-manager
activate ./venv/bin/activate
sddp-lab-manager
# or
venv/bin/sddp-lab-manager
```

However, using [`uv`](https://docs.astral.sh/uv/) should make one's life much easier, without having to worry about the `venv`:

```
git clone https://github.com/rjmalves/sddp-lab-manager.git
cd sddp-lab-manager
uv sync
uv run sddp-lab-manager
```

## How-to

The CLI defines one command for each of the main user tasks. Each command requires an input `JSON` file with some configuration parameters about what should be done. This approach is preferred instead of demanding many `args` and `kwargs` on each call.

The commands are illustrated with some example `JSON` config files that are provided in the repository, together with two input datasets for being edited: `data-1dtoy` and `data-4ree`.

### edit

The `edit` command enables the user to create a set of study cases based on combinatorial replacements of any field of the [`SDDPlab`](https://github.com/rjmalves/sddp-lab) input files, associating the substitution with an user-provided label, and generating sets of input files following all the replacements that should be done.

A full example is provided in the `edit_config.json.example` file. In general, this file should contain the fields:

```json
{
    "base_case": "path/to/base/input/data",
    "target_dir": "path/to/directory/which/will/store/edited/data",
    "params": {
        "path/to/input/field/to/be/replaced": {
            "replacement_label_1": {
                ...
            },
            "replacement_label_2": {
                ...
            }
        },
        ...
    }
}
```

The most important field to be provided is the `params`, which should contain a mapping between paths to the input data that will be edited and the sets of replacements, which is given by pairs or labels and dynamic `JSON` content to be replaced. In the example `edit_config.json.example` file, the result is creating the `generated` folder, editing the input data from the `data-1dtoy` directory. Inside this folder, the following directories are created:

```
generated/
    data-1dtoy_10y_cvar1050
    data-1dtoy_10y_cvar5050
    data-1dtoy_10y_rn
    data-1dtoy_1y_cvar1050
    data-1dtoy_1y_cvar5050
    data-1dtoy_1y_rn
    data-1dtoy_3y_cvar1050
    data-1dtoy_3y_cvar5050
    data-1dtoy_3y_rn
```

The invocation is done with, using `uv` for example:

```
uv run sddp-lab-manager edit edit_config.json
```

### run

The `run` command enables the user to make a parallel execution of all the generated input data sets. However, each generated input data will be executed a number of times, depending on the configured entrypoints in the run `JSON` configuration file. This is done because the user might want to test different methods on the same input data set, which may not be parametrized purely through the data, but require diffent julia scripts.

Each entrypoint should be a `Julia` file and expect to receive the path to its input data as a CLI argument. The user may also provide an environment in the `environment` field containing the installed dependencies for all the entrypoints. Optionally, a precompiled image should be provided in the `image_name` field, for reducing the total required time for processing. The `processes` field allows the user to choose now many parallel processes will run the study cases, which are dispatched asynchronously.

A full example is provided in the `run_config.json.example` file. In general, this file should contain the fields:

```json
{
    "source_dir": "path/to/directory/with/edited/data",
    "target_dir": "path/to/directory/which/will/store/processed/data",
    "entrypoints": {
        "method_label_1": "path/to/julia/script/of/method/1",
        "method_label_2": "path/to/julia/script/of/method/2",
        ...
    },
    "environment": "/path/to/directory/with/the/full/Project.toml",
    "image_name": null,
    "processes": 2
}
```

In the example `run_config.json.example` file, the result is creating the `processed` folder, processing the data from the `generated` directory. Inside this folder, the following directories are created, and a julia entrypoint is called on each:

```
processed/
    data-1dtoy_10y_cvar1050/
        sddpjl_sddp_policy_outer_sim/
        sddpjl_sddp_policy_inner_sim/
        dualsddp_philpott_policy_inner_sim/
        dualsddp_dual_policy_inner_sim/
        dualsddp_reagan_policy_inner_sim/
    data-1dtoy_10y_cvar5050/
        sddpjl_sddp_policy_outer_sim/
        sddpjl_sddp_policy_inner_sim/
        dualsddp_philpott_policy_inner_sim/
        dualsddp_dual_policy_inner_sim/
        dualsddp_reagan_policy_inner_sim/
    ...
```

The invocation is done with, using `uv` for example:

```
uv run sddp-lab-manager run run_config.json
```

### postprocess

The `postprocess` command enables the user to aggregate the outputs obtained on each entrypoint, for each edited dataset. The configuration is simpler than the two previous commands, through another `JSON` file. 

To each output dataframe that is processed, two columns are added:
    - `case` : the label given by the `edit` command
    - `method` : the chosen entrypoint that produced the output with the `run` command

A full example is provided in the `postprocess_config.json.example` file. In general, this file should contain the fields:

```json
{
    "source_dir": "path/to/directory/with/processed/data",
    "target_dir": "path/to/directory/which/will/store/all/dataframes",
    "variables": {
        "variable_name_1": "relative_path_to_parquet_file_of_variable_1",
        "variable_name_2": "relative_path_to_parquet_file_of_variable_2",
        ...
    }
}
```

In the example `postprocess_config.json.example` file, the result is creating the `results` folder, processing the data from the `processed` directory. Inside this folder, the following files are created:

```
results/
    convergence.parquet
    cuts.parquet
    operation_buses.parquet
    operation_lines.parquet
    operation_hydros.parquet
    operation_thermals.parquet
    operation_system.parquet
```

The invocation is done with, using `uv` for example:

```
uv run sddp-lab-manager postprocess postprocess_config.json
```
