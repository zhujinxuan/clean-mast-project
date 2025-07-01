module RecommendTrainMesoCommand

using TOML
using ...Types.TowerShadingConfig: TowerShadingConfiguration
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoMast, TrainMesoModel, TrainMesoSource
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration, ParseSensorsFileConfig
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...ParseSensors.CommandParseSensors: load_and_normalize_config
using ...CleanMastUtils: load_dict

export execute

"""
    execute(dir::String)

Generate train-meso.toml configuration based on existing configurations.

# Arguments
- `dir::String`: Project directory containing reconstruct-single.toml and parse-sensors.toml
"""
function execute(dir::String)
    # Read reconstruct-single.toml for mast information
    tower_shading_path = joinpath(dir, "tower-shading.toml")
    if !isfile(tower_shading_path)
        error("tower-shading.toml not found. Please run 'recommend tower-shading' first.")
    end
    
    # Load configurations
    tower_shading_config_dict = load_dict(tower_shading_path)
    tower_shading_config = from_dict(TowerShadingConfiguration, tower_shading_config_dict)
    
    # Read parse-sensors.toml to find meso data
    parse_sensors_path = joinpath(dir, "parse-sensors.toml")
    if !isfile(parse_sensors_path)
        error("parse-sensors.toml not found. This file is needed to identify meso data sources.")
    end
    
    parse_sensors_config = load_and_normalize_config(parse_sensors_path)
    
    # Build masts array from tower-shading configuration
    masts = map(tower_shading_config.masts) do mast
        TrainMesoMast(
            mast.name,
            mast.output,
        )
    end

    mesos = map(parse_sensors_config.mesos) do meso
        TrainMesoSource(
            meso.name,
            meso.output,
        )
    end
    
    # Build models array - separate entry for each method
    models = mapreduce(vcat, collect(Iterators.product(masts, mesos)); init=[]) do (mast, meso)
        base_path = "./meso-models/$(mast.name)/$(meso.name)"
        
        map([("windspeed", "16-sector"), ("windspeed", "1-sector"), ("winddirection", "constant-offset")]) do (method_type, method)
            TrainMesoModel(
                 mast.name,
                 meso.name,
                 method,
                 "$(base_path)/$(method_type)/$(method).jld2"
            )
        end
    end
    
    # Create output configuration
    result = TrainMesoConfiguration(
        masts,
        mesos,
        models
    )
    output_dict = to_dict(result)
    
    # Write to train-meso.toml
    output_path = joinpath(dir, "train-meso.toml")
    open(output_path, "w") do io
        TOML.print(io, output_dict)
    end
    
    println("Generated train-meso.toml at: $output_path")
    
    if isempty(mesos)
        println("Warning: No mesoscale data sources found in parse-sensors.toml")
        println("Make sure your parse-sensors.toml includes mesos entries (e.g., ERA5, MERRA2).")
    else
        println("Found $(length(mesos)) mesoscale data source(s):")
        for meso in mesos
            println("  - $(meso.name)")
        end
        println("Will train $(length(models)) models total (3 models × $(length(masts)) masts × $(length(mesos)) mesos)")
    end
end

end # module 