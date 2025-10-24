module ReportMesoTimeSeriesConfiguration

using DataFrames
using Dates
import ..Utils: from_dict, to_dict
import ..MastTimeSeries: TimeSeriesData, TimeSeriesSource
using ..SensorColumns: SensorColumn
using ...CleanMastUtils: load_dict
using YAML
using TOML
using CSV

"""
Configuration for a single meso in the report meso-timeseries configuration (raw format)
"""
struct MesoReportMesoTimeSeriesConfigYAML
    name::String
    input::TimeSeriesSource
end

"""
Processed configuration for a single meso with loaded data
"""
struct MesoReportMesoTimeSeriesConfig
    name::String
    timeSeriesData::TimeSeriesData
end

"""
Output configuration for report meso-timeseries results
"""
struct OutputConfig
    path::String
end

"""
Raw report meso-timeseries configuration as loaded from YAML/TOML
"""
struct ReportMesoTimeSeriesConfigYAML
    mesos::Vector{MesoReportMesoTimeSeriesConfigYAML}
    output::OutputConfig
end

"""
Processed report meso-timeseries configuration with resolved paths and loaded data
"""
struct ReportMesoTimeSeriesConfig
    mesos::Vector{MesoReportMesoTimeSeriesConfig}
    output::OutputConfig
    configDir::String
end

# Conversion functions for MesoReportMesoTimeSeriesConfigYAML
function from_dict(::Type{MesoReportMesoTimeSeriesConfigYAML}, dict::Dict{String, Any})::MesoReportMesoTimeSeriesConfigYAML
    input_source = from_dict(TimeSeriesSource, Dict{String, Any}(dict["input"]))

    MesoReportMesoTimeSeriesConfigYAML(
        dict["name"],
        input_source
    )
end

function to_dict(config::MesoReportMesoTimeSeriesConfigYAML)::Dict{String, Any}
    result = Dict{String, Any}(
        "name" => config.name,
        "input" => to_dict(config.input)
    )
    return result
end

# Conversion functions for OutputConfig
function from_dict(::Type{OutputConfig}, dict::Dict{String, Any})::OutputConfig
    OutputConfig(dict["path"])
end

function to_dict(config::OutputConfig)::Dict{String, Any}
    Dict{String, Any}("path" => config.path)
end

# Conversion functions for ReportMesoTimeSeriesConfigYAML
function from_dict(::Type{ReportMesoTimeSeriesConfigYAML}, dict::Dict{String, Any})::ReportMesoTimeSeriesConfigYAML
    mesos = [from_dict(MesoReportMesoTimeSeriesConfigYAML, Dict{String, Any}(m)) for m in dict["mesos"]]
    output = from_dict(OutputConfig, Dict{String, Any}(dict["output"]))
    ReportMesoTimeSeriesConfigYAML(mesos, output)
end

function to_dict(config::ReportMesoTimeSeriesConfigYAML)::Dict{String, Any}
    result = Dict{String, Any}(
        "mesos" => [to_dict(m) for m in config.mesos],
        "output" => to_dict(config.output)
    )
    return result
end

# Export all types and conversion functions
export MesoReportMesoTimeSeriesConfigYAML, MesoReportMesoTimeSeriesConfig,
       OutputConfig, ReportMesoTimeSeriesConfigYAML, ReportMesoTimeSeriesConfig,
       from_dict, to_dict

"""
    get_output_path(config::ReportMesoTimeSeriesConfig, meso_name::String) -> String

Get the output directory path for a specific meso.
Creates the directory if it doesn't exist.

# Arguments
- `config::ReportMesoTimeSeriesConfig`: The report meso-timeseries configuration
- `meso_name::String`: Name of the meso

# Returns
- `String`: Full path to the output directory
"""
function get_output_path(config::ReportMesoTimeSeriesConfig, meso_name::String)::String
    output_dir = joinpath(config.output.path, meso_name)
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

Load sensor configuration from a YAML or TOML file and convert to SensorColumn objects.
"""
function load_sensor_config(sensor_config_path::String)::Vector{SensorColumn}
    if !isfile(sensor_config_path)
        error("Sensor config file not found: $sensor_config_path")
    end

    sensor_data = load_dict(sensor_config_path)

    sensors = SensorColumn[]
    for sensor_dict in sensor_data["sensors"]
        push!(sensors, from_dict(SensorColumn, Dict{String,Any}(sensor_dict)))
    end

    return sensors
end

"""
    load_timeseries_data(csv_path::String, sensor_config_path::String) -> TimeSeriesData

Load time series data from CSV and sensor configuration from YAML or TOML.
"""
function load_timeseries_data(csv_path::String, sensor_config_path::String)::TimeSeriesData
    if !isfile(csv_path)
        error("CSV file not found: $csv_path")
    end

    df = CSV.read(csv_path, DataFrame)
    sensors = load_sensor_config(sensor_config_path)

    return TimeSeriesData(df, sensors)
end

"""
    process_meso_config(meso_yaml::MesoReportMesoTimeSeriesConfigYAML, config_dir::String) -> MesoReportMesoTimeSeriesConfig

Process a single meso configuration by resolving paths and loading data.
"""
function process_meso_config(meso_yaml::MesoReportMesoTimeSeriesConfigYAML, config_dir::String)::MesoReportMesoTimeSeriesConfig
    csv_path = resolve_path(meso_yaml.input.data, config_dir)
    sensor_config_path = resolve_path(meso_yaml.input.sensors, config_dir)

    timeseries_data = load_timeseries_data(csv_path, sensor_config_path)

    return MesoReportMesoTimeSeriesConfig(
        meso_yaml.name,
        timeseries_data
    )
end

"""
    load_report_meso_timeseries_config(config_path::String) -> ReportMesoTimeSeriesConfig

Load and process report meso-timeseries configuration from a YAML, TOML, or JSON file.
Resolves all paths relative to the configuration file location and loads time series data.
"""
function load_report_meso_timeseries_config(config_path::String)::ReportMesoTimeSeriesConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end

    config_dir = dirname(abspath(config_path))

    config_dict = load_dict(config_path)
    config_yaml = from_dict(ReportMesoTimeSeriesConfigYAML, config_dict)

    processed_mesos = MesoReportMesoTimeSeriesConfig[]
    for meso_yaml in config_yaml.mesos
        try
            push!(processed_mesos, process_meso_config(meso_yaml, config_dir))
            @info "Loaded meso configuration: $(meso_yaml.name)"
        catch e
            @error "Failed to load meso $(meso_yaml.name): $e"
            rethrow(e)
        end
    end

    output_config = OutputConfig(
        resolve_path(config_yaml.output.path, config_dir)
    )

    return ReportMesoTimeSeriesConfig(
        processed_mesos,
        output_config,
        config_dir
    )
end

# Export helper functions
export resolve_path, load_sensor_config, load_timeseries_data,
       process_meso_config, load_report_meso_timeseries_config

end # module
