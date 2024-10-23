using DualSDDP
using DataFrames
using lab2mslbo: lab2mslbo
using Random: seed!

if length(ARGS) != 1
    println("Forneça um diretório como argumento")
else
    cd(ARGS[1])
    # Gets deck info
    M, data, solver, writer, extension = lab2mslbo.build_mslbo(".")
    output_path = data.output_path
    state0 = data.state0
    seed = data.seed
    risk = mk_primal_avar(data.risk_alpha; beta=data.risk_lambda)
    risk_dual = mk_copersp_avar(data.risk_alpha; beta=data.risk_lambda)
    nstages = data.num_stages
    niters = data.num_iterations
    ub_iters = Int64.(2 .^ (0:1:floor(log2(niters))))

    # Primal with outer and inner bounds
    seed!(seed)
    io_pb, io_lbs, io_ubs, io_times = problem_child_solve(M, nstages, risk, solver, state0, niters; verbose=true)

    # Export convergence data

    df = DataFrame(iteration=1:niters,
        lower_bound=io_lbs,
        simulation=fill(NaN, niters),
        upper_bound=io_ubs,
        time=io_times)

    mkpath(output_path)
    writer(output_path * "/convergence" * extension, df)


end
