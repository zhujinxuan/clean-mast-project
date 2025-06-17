module AnalyzeReconstructSingleConfiguration

using DataFrames
using CSV
import ..Utils: from_dict, to_dict
import ..MastTimeSeries: TimeSeriesData, SensorColumn
import ..AnalyzeConfiguration: resolve_path, load_sensor_config, load_timeseries_data
using YAML

"""
Configuration for reconstruction data (before/after)
"""
struct ReconstructionDataConfig
    csv::String              # Path to CSV file
    sensorConfig::String     # Path to sensor config YAML
end

"""
Configuration for a single mast in the analyze reconstruct-single YAML
"""
struct MastReconstructAnalyzeConfig
    name::String
    before_reconstruction::ReconstructionDataConfig
    after_reconstruction::ReconstructionDataConfig
end

"""
Processed configuration for a single mast with loaded data
"""
struct ProcessedMastReconstructConfig
    name::String
    beforeData::TimeSeriesData
    afterData::TimeSeriesData
end

"""
Output configuration for analysis results
"""
struct ReconstructOutputConfig
    dir::Union{String, Nothing}  # Output directory (default: ./analyze-reconstruct-single)
end

"""
Raw analyze reconstruct-single configuration as loaded from YAML
"""
struct AnalyzeReconstructSingleConfigYAML
    masts::Vector{MastReconstructAnalyzeConfig}
    output::Union{ReconstructOutputConfig, Nothing}
end

"""
Processed analyze reconstruct-single configuration with resolved paths and loaded data
"""
struct AnalyzeReconstructSingleConfig
    masts::Vector{ProcessedMastReconstructConfig}
    outputDir::String
    configDir::String  # Directory containing the YAML (for path resolution)
end

# Conversion functions
function from_dict(::Type{ReconstructionDataConfig}, dict::Dict{String, Any})::ReconstructionDataConfig
    ReconstructionDataConfig(
        dict["csv"],
        dict["sensorConfig"]
    )
end

function to_dict(config::ReconstructionDataConfig)::Dict{String, Any}
    Dict{String, Any}(
        "csv" => config.csv,
        "sensorConfig" => config.sensorConfig
    )
end

function from_dict(::Type{MastReconstructAnalyzeConfig}, dict::Dict{String, Any})::MastReconstructAnalyzeConfig
    MastReconstructAnalyzeConfig(
        dict["name"],
        from_dict(ReconstructionDataConfig, Dict{String, Any}(dict["before_reconstruction"])),
        from_dict(ReconstructionDataConfig, Dict{String, Any}(dict["after_reconstruction"]))
    )
end

function to_dict(config::MastReconstructAnalyzeConfig)::Dict{String, Any}
    Dict{String, Any}(
        "name" => config.name,
        "before_reconstruction" => to_dict(config.before_reconstruction),
        "after_reconstruction" => to_dict(config.after_reconstruction)
    )
end

function from_dict(::Type{ReconstructOutputConfig}, dict::Dict{String, Any})::ReconstructOutputConfig
    ReconstructOutputConfig(
        get(dict, "dir", nothing)
    )
end

function to_dict(config::ReconstructOutputConfig)::Dict{String, Any}
    result = Dict{String, Any}()
    if !isnothing(config.dir)
        result["dir"] = config.dir
    end
    result
end

function from_dict(::Type{AnalyzeReconstructSingleConfigYAML}, dict::Dict{String, Any})::AnalyzeReconstructSingleConfigYAML
    masts = [from_dict(MastReconstructAnalyzeConfig, Dict{String, Any}(m)) for m in dict["masts"]]
    output = haskey(dict, "output") ? from_dict(ReconstructOutputConfig, Dict{String, Any}(dict["output"])) : nothing
    AnalyzeReconstructSingleConfigYAML(masts, output)
end

function to_dict(config::AnalyzeReconstructSingleConfigYAML)::Dict{String, Any}
    result = Dict{String, Any}(
        "masts" => [to_dict(m) for m in config.masts]
    )
    if !isnothing(config.output)
        result["output"] = to_dict(config.output)
    end
    result
end

"""
    process_mast_reconstruct_config(mast_config::MastReconstructAnalyzeConfig, config_dir::String) -> ProcessedMastReconstructConfig

Process a single mast configuration by resolving paths and loading data.
"""
function process_mast_reconstruct_config(mast_config::MastReconstructAnalyzeConfig, config_dir::String)::ProcessedMastReconstructConfig
    # Resolve paths for before reconstruction data
    before_csv_path = resolve_path(mast_config.before_reconstruction.csv, config_dir)
    before_sensor_path = resolve_path(mast_config.before_reconstruction.sensorConfig, config_dir)
    
    # Resolve paths for after reconstruction data
    after_csv_path = resolve_path(mast_config.after_reconstruction.csv, config_dir)
    after_sensor_path = resolve_path(mast_config.after_reconstruction.sensorConfig, config_dir)
    
    # Load time series data
    before_data = load_timeseries_data(before_csv_path, before_sensor_path)
    after_data = load_timeseries_data(after_csv_path, after_sensor_path)
    
    return ProcessedMastReconstructConfig(
        mast_config.name,
        before_data,
        after_data
    )
end

"""
    load_analyze_reconstruct_single_config(config_path::String) -> AnalyzeReconstructSingleConfig

Load and process analyze reconstruct-single configuration from a YAML file.
"""
function load_analyze_reconstruct_single_config(config_path::String)::AnalyzeReconstructSingleConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end
    
    # Get the directory containing the config file
    config_dir = dirname(abspath(config_path))
    
    # Load YAML configuration
    yaml_dict = Dict{String, Any}(YAML.load_file(config_path))
    config_yaml = from_dict(AnalyzeReconstructSingleConfigYAML, yaml_dict)
    
    # Process each mast configuration
    processed_masts = ProcessedMastReconstructConfig[]
    for mast_yaml in config_yaml.masts
        try
            push!(processed_masts, process_mast_reconstruct_config(mast_yaml, config_dir))
            @info "Loaded mast reconstruction configuration: $(mast_yaml.name)"
        catch e
            @error "Failed to load mast $(mast_yaml.name): $e"
            rethrow(e)
        end
    end
    
    # Determine output directory
    output_dir = if !isnothing(config_yaml.output) && !isnothing(config_yaml.output.dir)
        resolve_path(config_yaml.output.dir, config_dir)
    else
        joinpath(config_dir, "analyze-reconstruct-single")
    end
    
    return AnalyzeReconstructSingleConfig(
        processed_masts,
        output_dir,
        config_dir
    )
end

# Export all types and functions
export ReconstructionDataConfig, MastReconstructAnalyzeConfig, ProcessedMastReconstructConfig,
       ReconstructOutputConfig, AnalyzeReconstructSingleConfigYAML, AnalyzeReconstructSingleConfig,
       process_mast_reconstruct_config, load_analyze_reconstruct_single_config

end # module 