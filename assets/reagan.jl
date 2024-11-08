using DualSDDP
using DataFrames
using lab2mslbo: lab2mslbo
using Random: seed!

if length(ARGS) != 1
    println("Forneça um diretório como argumento")
else
    cd(ARGS[1])
    # Gets deck info
    M, data = lab2mslbo.build_mslbo(".")
    output_path = data.output_path
    risk = mk_primal_avar(data.risk_alpha; beta=data.risk_lambda)
    risk_dual = mk_copersp_avar(data.risk_alpha; beta=data.risk_lambda)

    # Primal with outer and inner bounds
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
        output_path_without_extension=data.output_path * "/convergence_reagan",
    )


end
