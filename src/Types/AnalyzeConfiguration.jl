module AnalyzeConfiguration

using DataFrames
using Dates
import ..Utils: from_dict, to_dict
import ..MastTimeSeries: TimeSeriesData, SensorColumn
using YAML
using CSV

"""
Air density configuration (moved from CleanMastConfig for analyze functionality)
"""
struct AirDensityConfig
    density::Float64
    reference_height::Float64
end

"""
Configuration for a single mast in the analyze.yaml (raw format)
"""
struct MastAnalyzeConfigYAML
    name::String
    csv::String                     # Path to CSV file (relative or absolute)
    sensorConfig::String            # Path to sensor config YAML (relative or absolute)
    airDensity::Union{AirDensityConfig, Nothing}
end

"""
Processed configuration for a single mast with loaded data
"""
struct MastAnalyzeConfig
    name::String
    timeSeriesData::TimeSeriesData
    airDensity::Union{AirDensityConfig, Nothing}
end

"""
Configuration for DOCX report output
"""
struct DocxConfig
    sectionIndex::String        # Section index in the report (e.g., "3.2")
    sectionLevel::Int          # Section level (default: 2)
end

"""
Output configuration for analysis results
"""
struct OutputConfig
    path::String               # Output directory path (relative to analyze.yaml)
    docx::Union{DocxConfig, Nothing}
end

"""
Raw analyze configuration as loaded from YAML
"""
struct AnalyzeConfigYAML
    masts::Vector{MastAnalyzeConfigYAML}
    output::OutputConfig
end

"""
Processed analyze configuration with resolved paths and loaded data
"""
struct AnalyzeConfig
    masts::Vector{MastAnalyzeConfig}
    output::OutputConfig
    configDir::String          # Directory containing the analyze.yaml (for path resolution)
end

# Conversion functions for AirDensityConfig
function from_dict(::Type{AirDensityConfig}, dict::Dict{String, Any})::AirDensityConfig
    AirDensityConfig(
        convert(Float64, dict["density"]),
        convert(Float64, dict["reference_height"])
    )
end

function to_dict(config::AirDensityConfig)::Dict{String, Any}
    Dict{String, Any}(
        "density" => config.density,
        "reference_height" => config.reference_height
    )
end

# Conversion functions for MastAnalyzeConfigYAML
function from_dict(::Type{MastAnalyzeConfigYAML}, dict::Dict{String, Any})::MastAnalyzeConfigYAML
    air_density = if haskey(dict, "airDensity") && !isnothing(dict["airDensity"])
        from_dict(AirDensityConfig, Dict{String, Any}(dict["airDensity"]))
    else
        nothing
    end
    
    MastAnalyzeConfigYAML(
        dict["name"],
        dict["csv"],
        dict["sensorConfig"],
        air_density
    )
end

function to_dict(config::MastAnalyzeConfigYAML)::Dict{String, Any}
    Dict{String, Any}(
        "name" => config.name,
        "csv" => config.csv,
        "sensorConfig" => config.sensorConfig,
        "airDensity" => to_dict(config.airDensity)
    )
end

# Conversion functions for DocxConfig
function from_dict(::Type{DocxConfig}, dict::Dict{String, Any})::DocxConfig
    DocxConfig(
        dict["sectionIndex"],
        get(dict, "sectionLevel", 2)  # Default to level 2
    )
end

function to_dict(config::DocxConfig)::Dict{String, Any}
    Dict{String, Any}(
        "sectionIndex" => config.sectionIndex,
        "sectionLevel" => config.sectionLevel
    )
end

# Conversion functions for OutputConfig
function from_dict(::Type{OutputConfig}, dict::Dict{String, Any})::OutputConfig
    docx_config = haskey(dict, "docx") ? from_dict(DocxConfig, Dict{String, Any}(dict["docx"])) : nothing
    OutputConfig(
        dict["path"],
        docx_config
    )
end

function to_dict(config::OutputConfig)::Dict{String, Any}
    result = Dict{String, Any}("path" => config.path)
    if !isnothing(config.docx)
        result["docx"] = to_dict(config.docx)
    end
    result
end

# Conversion functions for AnalyzeConfigYAML
function from_dict(::Type{AnalyzeConfigYAML}, dict::Dict{String, Any})::AnalyzeConfigYAML
    masts = [from_dict(MastAnalyzeConfigYAML, Dict{String, Any}(m)) for m in dict["masts"]]
    output = from_dict(OutputConfig, Dict{String, Any}(dict["output"]))
    AnalyzeConfigYAML(masts, output)
end

function to_dict(config::AnalyzeConfigYAML)::Dict{String, Any}
    Dict{String, Any}(
        "masts" => [to_dict(m) for m in config.masts],
        "output" => to_dict(config.output)
    )
end

# Export all types and conversion functions
export MastAnalyzeConfigYAML, MastAnalyzeConfig, 
       DocxConfig, OutputConfig, AnalyzeConfigYAML, AnalyzeConfig,
       AirDensityConfig, from_dict, to_dict

"""
    get_output_path(config::AnalyzeConfig, mast_name::String, analysis_type::String) -> String

Get the output directory path for a specific mast and analysis type.
Creates the directory if it doesn't exist.

# Arguments
- `config::AnalyzeConfig`: The analysis configuration
- `mast_name::String`: Name of the mast
- `analysis_type::String`: Type of analysis (e.g., "wind-temporal", "vertical-profile", etc.)

# Returns
- `String`: Full path to the output directory
"""
function get_output_path(config::AnalyzeConfig, mast_name::String, analysis_type::String)::String
    output_dir = joinpath(config.output.path, mast_name, analysis_type)
    mkpath(output_dir)
    return output_dir
end

# Export the function
export get_output_path

"""
    resolve_path(path::String, base_dir::String) -> String

Resolve a path relative to a base directory. If the path is absolute, return it as-is.
Otherwise, join it with the base directory.
"""
function resolve_path(path::String, base_dir::String)::String
    isabspath(path) ? path : normpath(joinpath(base_dir, path))
end

"""
    load_sensor_config(sensor_config_path::String) -> Vector{SensorColumn}

Load sensor configuration from a YAML file and convert to SensorColumn objects.
"""
function load_sensor_config(sensor_config_path::String)::Vector{SensorColumn}
    if !isfile(sensor_config_path)
        error("Sensor config file not found: $sensor_config_path")
    end
    
    sensor_yaml = YAML.load_file(sensor_config_path)
    
    # Convert each sensor dict to SensorColumn
    sensors = SensorColumn[]
    for sensor_dict in sensor_yaml["sensors"]
        push!(sensors, from_dict(SensorColumn, Dict{String,Any}(sensor_dict)))
    end
    
    return sensors
end

"""
    load_timeseries_data(csv_path::String, sensor_config_path::String) -> TimeSeriesData

Load time series data from CSV and sensor configuration from YAML.
"""
function load_timeseries_data(csv_path::String, sensor_config_path::String)::TimeSeriesData
    if !isfile(csv_path)
        error("CSV file not found: $csv_path")
    end
    
    # Load CSV data
    df = CSV.read(csv_path, DataFrame)
    
    # Load sensor configuration
    sensors = load_sensor_config(sensor_config_path)
    
    return TimeSeriesData(df, sensors)
end

"""
    process_mast_config(mast_yaml::MastAnalyzeConfigYAML, config_dir::String) -> MastAnalyzeConfig

Process a single mast configuration by resolving paths and loading data.
"""
function process_mast_config(mast_yaml::MastAnalyzeConfigYAML, config_dir::String)::MastAnalyzeConfig
    # Resolve paths relative to config directory
    csv_path = resolve_path(mast_yaml.csv, config_dir)
    sensor_config_path = resolve_path(mast_yaml.sensorConfig, config_dir)
    
    # Load time series data
    timeseries_data = load_timeseries_data(csv_path, sensor_config_path)
    
    return MastAnalyzeConfig(
        mast_yaml.name,
        timeseries_data,
        mast_yaml.airDensity
    )
end

"""
    load_analyze_config(config_path::String) -> AnalyzeConfig

Load and process analyze configuration from a YAML file.
Resolves all paths relative to the YAML file location and loads time series data.
"""
function load_analyze_config(config_path::String)::AnalyzeConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end
    
    # Get the directory containing the config file
    config_dir = dirname(abspath(config_path))
    
    # Load YAML configuration
    yaml_dict = Dict{String, Any}(YAML.load_file(config_path))
    config_yaml = from_dict(AnalyzeConfigYAML, yaml_dict)
    
    # Process each mast configuration
    processed_masts = MastAnalyzeConfig[]
    for mast_yaml in config_yaml.masts
        try
            push!(processed_masts, process_mast_config(mast_yaml, config_dir))
            @info "Loaded mast configuration: $(mast_yaml.name)"
        catch e
            @error "Failed to load mast $(mast_yaml.name): $e"
            rethrow(e)
        end
    end
    
    # Create output config with resolved path
    output_config = OutputConfig(
        resolve_path(config_yaml.output.path, config_dir),
        config_yaml.output.docx
    )
    
    return AnalyzeConfig(
        processed_masts,
        output_config,
        config_dir
    )
end

# Export helper functions
export resolve_path, load_sensor_config, load_timeseries_data, 
       process_mast_config, load_analyze_config

end # module 