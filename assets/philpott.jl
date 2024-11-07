using DualSDDP
using DataFrames
using lab2mslbo: lab2mslbo
using Random: seed!

if length(ARGS) != 1
    println("Forneça um diretório como argumento")
else
    cd(ARGS[1])
    # Gets deck info
    M, data, = lab2mslbo.build_mslbo(".")

    risk = mk_primal_avar(data.risk_alpha; beta=data.risk_lambda)
    ub_iters = Int64.(2 .^ (1:1:floor(log2(data.num_iterations))))

    seed!(data.seed)
    primal_pb, primal_trajs, primal_lbs, primal_times = primalsolve(M, data.num_stages, risk, data.solver, data.state0, data.num_iterations; verbose=true)
    rec_ubs, rec_times = primalub(M, data.num_stages, risk, data.solver, primal_trajs, ub_iters; verbose=true)

    # Export convergence data
    lab2mslbo.export_primal_with_ub_convergence(
        data.num_iterations,
        primal_lbs,
        primal_times,
        rec_ubs,
        rec_times,
        data.writer,
        data.extension;
        output_path_without_extension=data.output_path * "/convergence_philpott",
    )


end
