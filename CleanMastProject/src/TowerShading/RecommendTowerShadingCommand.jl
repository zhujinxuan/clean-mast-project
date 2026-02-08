module RecommendTowerShadingCommand

using TOML
using ...Types.ProcessCleanConfig: ProcessCleanConfiguration
using ...Types.Utils: from_dict, strip_nothing_values
using ...CleanMastUtils: load_dict

export execute

"""
    execute(dir::String)

Generate tower-shading.toml configuration based on process-clean.toml.

# Arguments
- `dir::String`: Project directory containing process-clean.toml
"""
function execute(dir::String)
    # Read process-clean.toml
    process_clean_path = joinpath(dir, "process-clean.toml")
    if !isfile(process_clean_path)
        error("process-clean.toml not found. Please run 'recommend-process-clean' first.")
    end
    
    # Load process clean configuration
    config_dict = load_dict(process_clean_path)
    process_clean_config = from_dict(ProcessCleanConfiguration, config_dict)
    
    # Create tower shading configuration
    masts = map(process_clean_config.masts) do mast
        Dict(
            "name" => mast.name,
            "input" => Dict(
                "data" => mast.output.data,
                "sensors" => mast.output.sensors
            ),
            "output" => Dict(
                "data" => "./tower-shading/$(mast.name).parquet",
                "sensors" => nothing
            )
        )
    end
    
    # Create output configuration
    output_config = Dict("masts" => masts)
    
    # Write to tower-shading.toml
    output_path = joinpath(dir, "tower-shading.toml")
    open(output_path, "w") do io
        println(io, "# Tower Shading Configuration")
        println(io, "# Merges wind speed sensors at nearby heights (within 2m) to handle tower shading effects")
        println(io)
        TOML.print(io, strip_nothing_values(Dict{String, Any}(output_config)))
    end
    
    println("Generated tower-shading.toml at: $output_path")
end

end # module 