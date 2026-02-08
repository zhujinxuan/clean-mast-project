module RecommendReconstructSingleCommand

using TOML
using ...Types.TowerShadingConfig: TowerShadingConfiguration
using ...Types.Utils: from_dict, strip_nothing_values
using ...CleanMastUtils: load_dict

export execute

"""
    execute(dir::String)

Generate reconstruct-single.toml configuration based on tower-shading.toml.

# Arguments
- `dir::String`: Project directory containing tower-shading.toml
"""
function execute(dir::String)
    # Read tower-shading.toml
    tower_shading_path = joinpath(dir, "tower-shading.toml")
    if !isfile(tower_shading_path)
        error("tower-shading.toml not found. Please run 'recommend tower-shading' first.")
    end
    
    # Load tower shading configuration
    config_dict = load_dict(tower_shading_path)
    tower_shading_config = from_dict(TowerShadingConfiguration, config_dict)
    
    # Create reconstruct single configuration
    masts = map(tower_shading_config.masts) do mast
        Dict(
            "name" => mast.name,
            "input" => Dict(
                "data" => mast.output.data,
                "sensors" => mast.output.sensors
            ),
            "output" => Dict(
                "data" => "./reconstruct-single/$(mast.name).parquet",
                "sensors" => nothing
            )
        )
    end
    
    # Create output configuration
    output_config = Dict("masts" => masts)
    
    # Write to reconstruct-single.toml
    output_path = joinpath(dir, "reconstruct-single.toml")
    open(output_path, "w") do io
        println(io, "# Single Mast Reconstruction Configuration")
        println(io, "# Fills gaps using correlations between sensors on the same mast")
        println(io)
        TOML.print(io, strip_nothing_values(Dict{String, Any}(output_config)))
    end
    
    println("Generated reconstruct-single.toml at: $output_path")
end

end # module 