using SDDPlab
using SDDP
using DualSDDP
using DataFrames
using lab2mslbo: lab2mslbo
using Random: seed!
using JuMP

using HiGHS
optimizer = optimizer_with_attributes(HiGHS.Optimizer)
set_attribute(optimizer, "log_to_console", false)

e = CompositeException()

if length(ARGS) != 1
    println("Must provide a path as the first argument")
else
    cd(ARGS[1])
    # Gets deck info
    M, data = lab2mslbo.build_mslbo(".", optimizer)

    ## ---------- DualSDDP calls ------------

    risk = mk_primal_avar(data.risk_alpha; beta=data.risk_lambda)
    ub_iters = Int64.(2 .^ (4:1:floor(log2(data.num_iterations))))

    seed!(data.seed)
    primal_pb, primal_trajs, primal_lbs, primal_times = primalsolve(M, data.num_stages, risk, optimizer, data.state0, data.num_iterations; verbose=true)
    rec_ubs, rec_times = primalub(M, data.num_stages, risk, optimizer, primal_trajs, ub_iters; verbose=true)

    # Export convergence data
    mkpath(data.output_path)
    lab2mslbo.export_primal_with_ub_convergence(
        data.num_iterations,
        primal_lbs,
        primal_times,
        rec_ubs,
        rec_times,
        data.writer,
        data.extension;
        output_path_without_extension=data.output_path * "/convergence",
    )

    # Export cuts
    cut_path = data.output_path * "/cuts.json"
    DualSDDP.write_cuts_to_file(primal_pb, cut_path)

    ## --------- InnerBellmanFunction calls with DualSDDP policy ---------

    function vertex_name_parser(vertex_name::String)::String
        # Expects vertex name to be xN -> STORAGE[N]
        new_name = replace(vertex_name, "x" => "STORAGE[")
        return new_name * "]"
    end

    lab2mslbo.translate_cuts_states(cut_path, vertex_name_parser)

    entrypoint = SDDPlab.Inputs.Entrypoint("main.jsonc", optimizer, e)
    policy = SDDPlab.Tasks.__build_model(entrypoint.inputs.files)
    SDDP.read_cuts_from_file(policy, cut_path)

    # Transforms to vertex policy graph
    inner_policy, upper_bound, upper_bound_time = lab2mslbo.__build_and_compute_ub_model(
        entrypoint.inputs.files, policy, optimizer
    )

    # Generates fake policy artifact and artifacts vector
    task_definitions = SDDPlab.get_tasks(entrypoint.inputs.files)
    policy_task_index = findfirst(x -> isa(x, SDDPlab.Tasks.Policy), task_definitions)
    policy_task_definition = task_definitions[policy_task_index]

    artifacts = Vector{SDDPlab.Tasks.TaskArtifact}([
        SDDPlab.Tasks.InputsArtifact(entrypoint.inputs.path, entrypoint.inputs.files, optimizer),
        SDDPlab.Tasks.PolicyArtifact(policy_task_definition, policy, entrypoint.inputs.files),
    ])

    # Runs simulation
    simulation_task_index = findfirst(x -> isa(x, SDDPlab.Tasks.Simulation), task_definitions)
    simulation_task_definition = task_definitions[simulation_task_index]
    a = SDDPlab.Tasks.run_task(simulation_task_definition, artifacts, e)
    SDDPlab.__save_results(a)

end
