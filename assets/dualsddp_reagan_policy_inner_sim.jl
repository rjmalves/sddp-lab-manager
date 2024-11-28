using SDDPlab
using DualSDDP
using DataFrames
using lab2mslbo: lab2mslbo
using Random: seed!

e = CompositeException()

if length(ARGS) != 1
    println("Must provide a path as the first argument")
else
    cd(ARGS[1])
    # Gets deck info
    M, data = lab2mslbo.build_mslbo(".")

    ## ---------- DualSDDP calls ------------

    risk = mk_primal_avar(data.risk_alpha; beta=data.risk_lambda)

    seed!(data.seed)
    io_pb, io_lbs, io_ubs, io_times = problem_child_solve(M, data.num_stages, risk, data.solver, data.state0, data.num_iterations; verbose=true)

    # Export convergence data
    mkpath(data.output_path)
    lab2mslbo.export_problem_child_convergence(
        data.num_iterations,
        io_lbs,
        io_ubs,
        io_times,
        data.writer,
        data.extension;
        output_path_without_extension=data.output_path * "/convergence",
    )

    # Export cuts / vertices
    cut_path = data.output_path * "/cuts.json"
    DualSDDP.write_policy_to_file(io_pb, cut_path)

    ## --------- InnerBellmanFunction calls with DualSDDP policy ---------

    function vertex_name_parser(vertex_name::String)::String
        # Expects vertex name to be xN -> STORAGE[N]
        new_name = replace(vertex_name, "x" => "STORAGE[")
        return new_name * "]"
    end

    entrypoint = SDDPlab.Inputs.Entrypoint("main.jsonc", e)
    model = lab2mslbo.__build_ub_model(entrypoint.inputs.files)

    lab2mslbo.read_vertices_from_file(
        model,
        cut_path;
        dualcuts=false,
        vertex_name_parser=vertex_name_parser,
        vertex_selection=false,
    )

    # Generates fake policy artifact and artifacts vector
    task_definitions = SDDPlab.get_tasks(entrypoint.inputs.files)
    policy_task_index = findfirst(x -> isa(x, SDDPlab.Tasks.Policy), task_definitions)
    policy_task_definition = task_definitions[policy_task_index]

    artifacts = Vector{SDDPlab.Tasks.TaskArtifact}([
        SDDPlab.Tasks.InputsArtifact(entrypoint.inputs.path, entrypoint.inputs.files),
        SDDPlab.Tasks.PolicyArtifact(policy_task_definition, model, entrypoint.inputs.files),
    ])

    # Runs simulation
    simulation_task_index = findfirst(x -> isa(x, SDDPlab.Tasks.Simulation), task_definitions)
    simulation_task_definition = task_definitions[simulation_task_index]
    a = SDDPlab.Tasks.run_task(simulation_task_definition, artifacts, e)
    SDDPlab.__save_results(a)

end
