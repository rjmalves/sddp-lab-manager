using SDDPlab: SDDPlab
using JuMP

using HiGHS
optimizer = optimizer_with_attributes(HiGHS.Optimizer)
set_attribute(optimizer, "log_to_console", false)

e = CompositeException()

if length(ARGS) != 1
    println("Must provide a path as the first argument")
else
    cd(ARGS[1])
    SDDPlab.main(optimizer; e=e)
end
