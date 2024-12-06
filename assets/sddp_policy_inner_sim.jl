using SDDPlab: SDDPlab
using lab2mslbo: lab2mslbo
using JuMP

using HiGHS

optimizer = optimizer_with_attributes(HiGHS.Optimizer)
set_attribute(optimizer, "log_to_console", false)

e = CompositeException()

if length(ARGS) != 1
    println("Must provide a path as the first argument")
else
    cd(ARGS[1])

    # Runs policy evaluation
    entrypoint = SDDPlab.Inputs.Entrypoint("main.jsonc", optimizer, e)
    artifacts = SDDPlab.__run_tasks!(entrypoint, e)
    SDDPlab.__log_errors(e)

    files = entrypoint.inputs.files

    # Removes simulation outputs if generated
    rm("out/simulation"; force=true, recursive=true)

    # Build and eval ub model
    policy_index = findfirst(x -> isa(x, SDDPlab.Tasks.PolicyArtifact), artifacts)
    policy_task = artifacts[policy_index].task
    policy = artifacts[policy_index].policy
    ub_iterations = Int64.(2 .^ (4:1:floor(log2(policy_task.convergence.max_iterations))))

    cut_source_path = policy_task.results.path * "/cuts.parquet"
    cut_path = policy_task.results.path * "/cuts.json"

    reader = lab2mslbo.get_reader(files)
    cuts = reader(cut_source_path, e)
    lab2mslbo.translate_cut_df_to_json(cuts, cut_path)

    inner_policy, ubs, ub_times = lab2mslbo.__build_model_and_compute_ub_at_iterations(
        files, optimizer, cut_path, ub_iterations
    )

    lab2mslbo.__update_convergence_file(files, ub_iterations, ubs, ub_times, e)

    # Generates fake policy artifact and artifact vector
    task_definitions = SDDPlab.get_tasks(files)
    policy_task_index = findfirst(x -> isa(x, SDDPlab.Tasks.Policy), task_definitions)
    policy_task_definition = task_definitions[policy_task_index]

    artifacts = Vector{SDDPlab.Tasks.TaskArtifact}([
        SDDPlab.Tasks.InputsArtifact(entrypoint.inputs.path, files, optimizer),
        SDDPlab.Tasks.PolicyArtifact(
            policy_task_definition, inner_policy, files
        ),
    ])

    # Runs simulation again
    simulation_task_index = findfirst(x -> isa(x, SDDPlab.Tasks.Simulation), task_definitions)
    simulation_task_definition = task_definitions[simulation_task_index]
    a = SDDPlab.Tasks.run_task(simulation_task_definition, artifacts, e)
    SDDPlab.__save_results(a)
end
