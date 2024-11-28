using SDDPlab: SDDPlab

e = CompositeException()

if length(ARGS) != 1
    println("Must provide a path as the first argument")
else
    cd(ARGS[1])
    SDDPlab.main(; e=e)
end
