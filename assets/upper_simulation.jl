using SDDPlab: SDDPlab
using Random: seed!
using DataFrames
using SDDP
using inner_dp: inner_dp

e = CompositeException()

if length(ARGS) != 1
    println("Forneça um diretório como argumento")
else
    cd(ARGS[1])
    # Runs policy evaluation
    entrypoint = SDDPlab.Inputs.Entrypoint("main.jsonc", e)
    artifacts = SDDPlab.__run_tasks!(entrypoint, e)
    SDDPlab.__log_errors(e)

    # Build and eval ub model
    policy_index = findfirst(x -> isa(x, SDDPlab.Tasks.PolicyArtifact), artifacts)
    policy = artifacts[policy_index].policy

    # Transforms to vertex policy graph
    inner_policy, upper_bound, upper_bound_time = inner_dp.__build_and_compute_ub_model(entrypoint.inputs.files, policy)
    inner_dp.__update_convergence_file(entrypoint.inputs.files, upper_bound, upper_bound_time, e)

    # Generates fake policy artifact
    artifacts[2] = SDDPlab.Tasks.PolicyArtifact(
        artifacts[policy_index].task,
        inner_policy,
        entrypoint.inputs.files
    )

    # Runs simulation again
    simulation_index = findfirst(x -> isa(x, SDDPlab.Tasks.SimulationArtifact), artifacts)
    simulation = artifacts[simulation_index].task
    a = SDDPlab.Tasks.run_task(simulation, artifacts, e)
    SDDPlab.__save_results(a)
end
