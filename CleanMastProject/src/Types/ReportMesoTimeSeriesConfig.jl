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

# Export helper functions
# Note: process_meso_config and load_report_meso_timeseries_config have been moved to
# ReportMesoTimeSeriesCommand module to avoid circular dependencies with MastTimeSeries
# load_timeseries_data removed - use load_timeseries(TimeSeriesSource(...), base_dir) directly
export resolve_path, load_sensor_config

end # module
