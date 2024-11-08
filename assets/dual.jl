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

    risk = mk_primal_avar(data.risk_alpha; beta=data.risk_lambda)
    risk_dual = mk_copersp_avar(data.risk_alpha; beta=data.risk_lambda)

    seed!(data.seed)
    primal_pb, primal_trajs, primal_lbs, primal_times = primalsolve(M, data.num_stages, risk, data.solver, data.state0, data.num_iterations; verbose=true)

    seed!(data.seed)
    dual_pb, dual_ubs, dual_times = dualsolve(M, data.num_stages, risk_dual, data.solver, data.state0, data.num_iterations; verbose=true)

    # Export convergence data
    mkpath(data.output_path)
    lab2mslbo.export_primal_with_dual_ub_convergence(
        data.num_iterations,
        primal_lbs,
        primal_times,
        dual_ubs,
        dual_times,
        data.writer,
        data.extension;
        output_path_without_extension=data.output_path * "/convergence_dual",
    )



end
