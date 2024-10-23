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

    seed!(seed)
    primal_pb, primal_trajs, primal_lbs, primal_times = primalsolve(M, nstages, risk, solver, state0, niters; verbose=true)
    rec_ubs, rec_times = primalub(M, nstages, risk, solver, primal_trajs, ub_iters; verbose=true)

    # Export convergence data
    dense_ubs = fill(NaN, niters)
    for ub_pair in rec_ubs
        dense_ubs[ub_pair[1]] = ub_pair[2]
    end
    dense_rec_times = fill(NaN, niters)
    for (ub_pair, time) in zip(rec_ubs, rec_times)
        dense_rec_times[ub_pair[1]] = time
    end

    df = DataFrame(iteration=1:niters,
        lower_bound=primal_lbs,
        simulation=fill(NaN, niters),
        upper_bound=dense_ubs,
        primal_time=primal_times,
        upper_bound_time=dense_rec_times,
        time=primal_times + replace(dense_rec_times, NaN => 0.0))

    mkpath(output_path)
    writer(output_path * "/convergence" * extension, df)


end
