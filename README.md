# sddp-lab-manager

Manager for helping with generating additional cases and parallel execution with sddp-lab.

## How-to

### Prepare generic sysimage with PackageCompiler

```
julia
] add PackageCompiler
using PackageCompiler
activate .
instantiate
create_sysimage(; sysimage_path="my-image.so", precompile_execution_file="my-entrypoint-file.jl")
```
