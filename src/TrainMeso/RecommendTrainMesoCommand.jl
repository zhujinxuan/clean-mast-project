module RecommendTrainMesoCommand

using TOML
using ...Types.TowerShadingConfig: TowerShadingConfiguration
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoMast, TrainMesoModel, TrainMesoSource
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration, ParseSensorsFileConfig
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...ParseSensors.CommandParseSensors: load_and_normalize_config
using ...CleanMastUtils: load_dict
using ...TimeSeriesProcessing.IntervalDetection: get_interval_statistics
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries

export execute

"""
    calculate_tower_shading_valid_time(tower_shading_source::TimeSeriesSource, base_dir::String)::Float64

Calculate the valid time (in days) for tower-shading data by loading the TimeSeriesData 
and using interval statistics.

# Arguments
- `tower_shading_source::TimeSeriesSource`: Tower-shading output data source
- `base_dir::String`: Base directory for resolving relative paths

# Returns
- `Float64`: Valid time in days
"""
function calculate_tower_shading_valid_time(tower_shading_source::TimeSeriesSource, base_dir::String)::Float64
    try
        # Load tower-shading data using the proper load_timeseries function
        ts_data = load_timeseries(tower_shading_source, base_dir)
        
        # Get interval statistics
        stats = get_interval_statistics(ts_data)
        
        # Calculate valid time in days
        valid_time_days = (stats.total_points * stats.representative_interval.value) / (60 * 24)
        
        return valid_time_days
    catch e
        @warn "Failed to calculate valid time for tower-shading data: $e"
        return 0.0
    end
end

"""
    execute(dir::String)

Generate train-meso.toml configuration based on existing configurations.
Uses intelligent input source selection:
- If tower-shading valid time ≥ 150 days: use tower-shading as mast input
- If tower-shading valid time < 150 days: use reconstruct-cross as mast input

# Arguments
- `dir::String`: Project directory containing tower-shading.toml and parse-sensors.toml
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
    
    println("🔍 Analyzing mast data validity for input source selection...")
    
    # Build masts array with intelligent input source selection
    masts = map(tower_shading_config.masts) do mast
        # Calculate valid time for tower-shading data
        tower_shading_valid_time = calculate_tower_shading_valid_time(mast.output, dir)
        
        # Choose input source based on valid time
        if tower_shading_valid_time >= 150.0
            # Use tower-shading output as input
            input_source = mast.output
            println("  Using tower-shading for $(mast.name) ($(round(tower_shading_valid_time, digits=1)) days of valid data)")
        else
            # Use reconstruct-cross output as input
            reconstruct_cross_path = "./reconstruct-cross/$(mast.name)_reconstructed.csv" 
            reconstruct_cross_sensors = "./reconstruct-cross/$(mast.name)_reconstructed.sensors.yaml"
            input_source = TimeSeriesSource(reconstruct_cross_path, reconstruct_cross_sensors)
            println("  Using reconstruct-cross for $(mast.name) (tower-shading only has $(round(tower_shading_valid_time, digits=1)) days, < 150 days required)")
        end
        
        TrainMesoMast(
            mast.name,
            input_source,
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