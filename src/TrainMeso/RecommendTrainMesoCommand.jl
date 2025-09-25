module RecommendTrainMesoCommand

using TOML
using ...Types.TowerShadingConfig: TowerShadingConfiguration
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoMast, TrainMesoModel, TrainMesoSource
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration, ParseSensorsFileConfig
using ...Types.ReconstructCrossConfig: ReconstructCrossConfiguration
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...ParseSensors.CommandParseSensors: load_and_normalize_config
using ...CleanMastUtils: load_dict
using ...TimeSeriesProcessing.IntervalDetection: get_interval_statistics
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries

export execute

"""
    calculate_tower_shading_valid_days(tower_shading_source::TimeSeriesSource, base_dir::String)::Float64

Calculate the valid time (in days) for tower-shading data by loading the TimeSeriesData 
and using interval statistics.

# Arguments
- `tower_shading_source::TimeSeriesSource`: Tower-shading output data source
- `base_dir::String`: Base directory for resolving relative paths

# Returns
- `Float64`: Valid time in days
"""
function calculate_tower_shading_valid_days(tower_shading_source::TimeSeriesSource, base_dir::String)::Float64
    # Load tower-shading data using the proper load_timeseries function
    ts_data = load_timeseries(tower_shading_source, base_dir)

    # Get interval statistics
    stats = get_interval_statistics(ts_data)

    # Calculate valid time in days
    valid_time_days = (stats.total_points * stats.representative_interval.value) / (60 * 24)

    return valid_time_days
end

"""
    load_reconstruct_cross_source(dir::String)::Union{Nothing, Dict{String, TimeSeriesSource}}

Load reconstruct-cross.toml from the given directory and build a lookup of mast name => output TimeSeriesSource.

- If the file does not exist, returns `nothing`.

# Arguments
- `dir::String`: Directory containing reconstruct-cross.toml

# Returns
- `Union{Nothing, Dict{String, TimeSeriesSource}}`: `nothing` when the file is missing; otherwise a Dict mapping mast names to their output sources.
"""
function load_reconstruct_cross_source(dir :: String) :: Union{Nothing, Dict{String, TimeSeriesSource}}
    reconstruct_cross_config_path = joinpath(dir, "reconstruct-cross.toml")
    if !isfile(reconstruct_cross_config_path)
        return nothing
    end
    cross_config_dict = load_dict(reconstruct_cross_config_path)
    cross_config = from_dict(ReconstructCrossConfiguration, cross_config_dict)
    return Dict{String, TimeSeriesSource}(
    mast.name =>  mast.output
        for mast in cross_config.masts
    )
end

"""
    choose_train_mast_input_source(dir::String, towershading_source::TimeSeriesSource, cross_source::Union{Nothing, TimeSeriesSource})::TimeSeriesSource

Select the mast input source used for training.
When tower-shading source is not long enough (150 days), try to use reconstruct-cross result.

# Arguments
- `dir::String`: Project base directory used to resolve relative paths
- `towershading_source::TimeSeriesSource`: Tower-shading output source for the mast
- `cross_source::Union{Nothing, TimeSeriesSource}`: Optional reconstruct-cross source for the mast

# Returns
- `TimeSeriesSource`: The selected input source for training
"""
function choose_train_mast_input_source(dir :: String, towershading_source:: TimeSeriesSource, cross_source :: Union{Nothing, TimeSeriesSource}) :: TimeSeriesSource
    if isnothing(cross_source)
        return towershading_source
    end
    tower_shading_valid_days = calculate_tower_shading_valid_days(towershading_source, dir)
    if tower_shading_valid_days < 150.0
        return cross_source
    end
    return towershading_source
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
    reconstruct_cross_source_dict = load_reconstruct_cross_source(dir)
    
    # Build masts array with intelligent input source selection
    masts = map(tower_shading_config.masts) do mast
        cross_source = isnothing(reconstruct_cross_source_dict) ? nothing : get(reconstruct_cross_source_dict, mast.name, nothing)
        input_source = choose_train_mast_input_source(dir, mast.output, cross_source)

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