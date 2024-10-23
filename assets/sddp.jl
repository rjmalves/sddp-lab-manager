using SDDPlab: SDDPlab

e = CompositeException()

if length(ARGS) != 1
    println("Forneça um diretório como argumento")
else
    cd(ARGS[1])
    SDDPlab.main(; e=e)
end
