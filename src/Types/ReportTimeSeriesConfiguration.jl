module ReportTimeSeriesConfiguration

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
Air density configuration (moved from CleanMastConfig for analyze functionality)
"""
struct AirDensityConfig
    density::Float64
    reference_height::Float64
end

"""
Configuration for a single mast in the report timeseries configuration (raw format)
"""
struct MastReportTimeSeriesConfigYAML
    name::String
    input::TimeSeriesSource         # Input data and sensors paths (consistent with TimeSeriesSource)
    airDensity::Union{AirDensityConfig, Nothing}
end

"""
Processed configuration for a single mast with loaded data
"""
struct MastReportTimeSeriesConfig
    name::String
    timeSeriesData::TimeSeriesData
    airDensity::Union{AirDensityConfig, Nothing}
end

"""
Output configuration for report timeseries results
"""
struct OutputConfig
    path::String               # Output directory path (relative to report timeseries configuration)
end

"""
Analysis toggles configuration - controls which analyses to run
"""
struct AnalysisToggles
    wind_temporal::Bool        # Wind temporal analysis (default: true)
    vertical_profile::Bool     # Vertical profile analysis (default: true)
    wind_frequency::Bool       # Wind frequency distribution (default: true)
    wind_rose::Bool           # Wind rose plots (default: true)
    turbulence::Bool          # Turbulence intensity analysis (default: true)
    weibull::Bool             # Weibull distribution (default: true)
    fifty_years_extreme::Bool # 50-year extreme wind (default: true)
end

"""
Raw report timeseries configuration as loaded from YAML/TOML
"""
struct ReportTimeSeriesConfigYAML
    masts::Vector{MastReportTimeSeriesConfigYAML}
    output::OutputConfig
    min_plot_height::Union{Float64, Nothing}  # Optional minimum height for plotting (default: 100.0)
    analysis::Union{AnalysisToggles, Nothing}  # Optional analysis toggles (default: all true)
end

"""
Processed report timeseries configuration with resolved paths and loaded data
"""
struct ReportTimeSeriesConfig
    masts::Vector{MastReportTimeSeriesConfig}
    output::OutputConfig
    configDir::String          # Directory containing the configuration file (for path resolution)
    min_plot_height::Float64   # Minimum height for plotting (default: 100.0)
    analysis::AnalysisToggles  # Analysis toggles (default: all true)
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

# Conversion functions for MastReportTimeSeriesConfigYAML
function from_dict(::Type{MastReportTimeSeriesConfigYAML}, dict::Dict{String, Any})::MastReportTimeSeriesConfigYAML
    air_density = if haskey(dict, "airDensity") && !isnothing(dict["airDensity"])
        from_dict(AirDensityConfig, Dict{String, Any}(dict["airDensity"]))
    else
        nothing
    end

    input_source = from_dict(TimeSeriesSource, Dict{String, Any}(dict["input"]))

    MastReportTimeSeriesConfigYAML(
        dict["name"],
        input_source,
        air_density
    )
end

function to_dict(config::MastReportTimeSeriesConfigYAML)::Dict{String, Any}
    result = Dict{String, Any}(
        "name" => config.name,
        "input" => to_dict(config.input)
    )
    if !isnothing(config.airDensity)
        result["airDensity"] = to_dict(config.airDensity)
    end
    return result
end

# Conversion functions for OutputConfig
function from_dict(::Type{OutputConfig}, dict::Dict{String, Any})::OutputConfig
    OutputConfig(dict["path"])
end

function to_dict(config::OutputConfig)::Dict{String, Any}
    Dict{String, Any}("path" => config.path)
end

# Conversion functions for AnalysisToggles
function from_dict(::Type{AnalysisToggles}, dict::Dict{String, Any})::AnalysisToggles
    AnalysisToggles(
        get(dict, "wind_temporal", true),
        get(dict, "vertical_profile", true),
        get(dict, "wind_frequency", true),
        get(dict, "wind_rose", true),
        get(dict, "turbulence", true),
        get(dict, "weibull", true),
        get(dict, "fifty_years_extreme", true)
    )
end

function to_dict(config::AnalysisToggles)::Dict{String, Any}
    Dict{String, Any}(
        "wind_temporal" => config.wind_temporal,
        "vertical_profile" => config.vertical_profile,
        "wind_frequency" => config.wind_frequency,
        "wind_rose" => config.wind_rose,
        "turbulence" => config.turbulence,
        "weibull" => config.weibull,
        "fifty_years_extreme" => config.fifty_years_extreme
    )
end

# Conversion functions for ReportTimeSeriesConfigYAML
function from_dict(::Type{ReportTimeSeriesConfigYAML}, dict::Dict{String, Any})::ReportTimeSeriesConfigYAML
    masts = [from_dict(MastReportTimeSeriesConfigYAML, Dict{String, Any}(m)) for m in dict["masts"]]
    output = from_dict(OutputConfig, Dict{String, Any}(dict["output"]))
    min_plot_height = haskey(dict, "min_plot_height") ? convert(Float64, dict["min_plot_height"]) : nothing
    analysis = haskey(dict, "analysis") && !isnothing(dict["analysis"]) ? from_dict(AnalysisToggles, Dict{String, Any}(dict["analysis"])) : nothing
    ReportTimeSeriesConfigYAML(masts, output, min_plot_height, analysis)
end

function to_dict(config::ReportTimeSeriesConfigYAML)::Dict{String, Any}
    result = Dict{String, Any}(
        "masts" => [to_dict(m) for m in config.masts],
        "output" => to_dict(config.output)
    )
    if !isnothing(config.min_plot_height)
        result["min_plot_height"] = config.min_plot_height
    end
    if !isnothing(config.analysis)
        result["analysis"] = to_dict(config.analysis)
    end
    return result
end

# Export all types and conversion functions
export MastReportTimeSeriesConfigYAML, MastReportTimeSeriesConfig,
       OutputConfig, ReportTimeSeriesConfigYAML, ReportTimeSeriesConfig,
       AirDensityConfig, AnalysisToggles, from_dict, to_dict

"""
    get_output_path(config::ReportTimeSeriesConfig, mast_name::String, analysis_type::String) -> String

Get the output directory path for a specific mast and analysis type.
Creates the directory if it doesn't exist.

# Arguments
- `config::ReportTimeSeriesConfig`: The report timeseries configuration
- `mast_name::String`: Name of the mast
- `analysis_type::String`: Type of analysis (e.g., "wind-temporal", "vertical-profile", etc.)

# Returns
- `String`: Full path to the output directory
"""
function get_output_path(config::ReportTimeSeriesConfig, mast_name::String, analysis_type::String)::String
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

Load sensor configuration from a YAML or TOML file and convert to SensorColumn objects.
"""
function load_sensor_config(sensor_config_path::String)::Vector{SensorColumn}
    if !isfile(sensor_config_path)
        error("Sensor config file not found: $sensor_config_path")
    end

    # Use load_dict to support both YAML and TOML formats
    sensor_data = load_dict(sensor_config_path)

    # Convert each sensor dict to SensorColumn
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
    
    # Load CSV data
    df = CSV.read(csv_path, DataFrame)
    
    # Load sensor configuration
    sensors = load_sensor_config(sensor_config_path)
    
    return TimeSeriesData(df, sensors)
end

"""
    process_mast_config(mast_yaml::MastReportTimeSeriesConfigYAML, config_dir::String) -> MastReportTimeSeriesConfig

Process a single mast configuration by resolving paths and loading data.
"""
function process_mast_config(mast_yaml::MastReportTimeSeriesConfigYAML, config_dir::String)::MastReportTimeSeriesConfig
    # Resolve paths relative to config directory
    csv_path = resolve_path(mast_yaml.input.data, config_dir)
    sensor_config_path = resolve_path(mast_yaml.input.sensors, config_dir)

    # Load time series data
    timeseries_data = load_timeseries_data(csv_path, sensor_config_path)

    return MastReportTimeSeriesConfig(
        mast_yaml.name,
        timeseries_data,
        mast_yaml.airDensity
    )
end

"""
    load_report_timeseries_config(config_path::String) -> ReportTimeSeriesConfig

Load and process report timeseries configuration from a YAML, TOML, or JSON file.
Resolves all paths relative to the configuration file location and loads time series data.
"""
function load_report_timeseries_config(config_path::String)::ReportTimeSeriesConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end

    # Get the directory containing the config file
    config_dir = dirname(abspath(config_path))

    # Load configuration using load_dict (supports YAML, TOML, JSON)
    config_dict = load_dict(config_path)
    config_yaml = from_dict(ReportTimeSeriesConfigYAML, config_dict)

    # Process each mast configuration
    processed_masts = MastReportTimeSeriesConfig[]
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
        resolve_path(config_yaml.output.path, config_dir)
    )

    # Set default min_plot_height if not specified
    min_plot_height = isnothing(config_yaml.min_plot_height) ? 100.0 : config_yaml.min_plot_height

    # Set default analysis toggles if not specified (all true)
    analysis_toggles = isnothing(config_yaml.analysis) ?
        AnalysisToggles(true, true, true, true, true, true, true) :
        config_yaml.analysis

    return ReportTimeSeriesConfig(
        processed_masts,
        output_config,
        config_dir,
        min_plot_height,
        analysis_toggles
    )
end

# Export helper functions
export resolve_path, load_sensor_config, load_timeseries_data,
       process_mast_config, load_report_timeseries_config

end # module 