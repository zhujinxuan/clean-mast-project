module ReportReconstructSingleConfiguration

using DataFrames
using CSV
import ..Utils: from_dict, to_dict
import ..MastTimeSeries: TimeSeriesData, SensorColumn, TimeSeriesSource, load_timeseries
import ..ReportTimeSeriesConfiguration: resolve_path
using YAML

"""
Configuration for reconstruction data (before/after) using TimeSeriesSource
"""
struct ReconstructionDataConfig
    input::TimeSeriesSource  # Time series source with data and sensors paths
end

"""
Configuration for a single mast in the report reconstruct-single YAML
"""
struct MastReconstructReportConfig
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
Output configuration for report results
"""
struct ReconstructOutputConfig
    dir::Union{String, Nothing}  # Output directory (default: ./report-reconstruct-single)
end

"""
Raw report reconstruct-single configuration as loaded from YAML
"""
struct ReportReconstructSingleConfigYAML
    masts::Vector{MastReconstructReportConfig}
    output::Union{ReconstructOutputConfig, Nothing}
end

"""
Processed report reconstruct-single configuration with resolved paths and loaded data
"""
struct ReportReconstructSingleConfig
    masts::Vector{ProcessedMastReconstructConfig}
    outputDir::String
    configDir::String  # Directory containing the YAML (for path resolution)
end

# Conversion functions
function from_dict(::Type{ReconstructionDataConfig}, dict::Dict{String, Any})::ReconstructionDataConfig
    ReconstructionDataConfig(
        from_dict(TimeSeriesSource, Dict{String, Any}(dict["input"]))
    )
end

function to_dict(config::ReconstructionDataConfig)::Dict{String, Any}
    Dict{String, Any}(
        "input" => to_dict(config.input)
    )
end

function from_dict(::Type{MastReconstructReportConfig}, dict::Dict{String, Any})::MastReconstructReportConfig
    MastReconstructReportConfig(
        dict["name"],
        from_dict(ReconstructionDataConfig, Dict{String, Any}(dict["before_reconstruction"])),
        from_dict(ReconstructionDataConfig, Dict{String, Any}(dict["after_reconstruction"]))
    )
end

function to_dict(config::MastReconstructReportConfig)::Dict{String, Any}
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

function from_dict(::Type{ReportReconstructSingleConfigYAML}, dict::Dict{String, Any})::ReportReconstructSingleConfigYAML
    masts = [from_dict(MastReconstructReportConfig, Dict{String, Any}(m)) for m in dict["masts"]]
    output = haskey(dict, "output") ? from_dict(ReconstructOutputConfig, Dict{String, Any}(dict["output"])) : nothing
    ReportReconstructSingleConfigYAML(masts, output)
end

function to_dict(config::ReportReconstructSingleConfigYAML)::Dict{String, Any}
    result = Dict{String, Any}(
        "masts" => [to_dict(m) for m in config.masts]
    )
    if !isnothing(config.output)
        result["output"] = to_dict(config.output)
    end
    result
end

"""
    process_mast_reconstruct_config(mast_config::MastReconstructReportConfig, config_dir::String) -> ProcessedMastReconstructConfig

Process a single mast configuration by resolving paths and loading data using load_timeseries.
"""
function process_mast_reconstruct_config(mast_config::MastReconstructReportConfig, config_dir::String)::ProcessedMastReconstructConfig
    # Load time series data using load_timeseries with automatic path resolution
    before_data = load_timeseries(mast_config.before_reconstruction.input, config_dir)
    after_data = load_timeseries(mast_config.after_reconstruction.input, config_dir)

    return ProcessedMastReconstructConfig(
        mast_config.name,
        before_data,
        after_data
    )
end

"""
    load_report_reconstruct_single_config(config_path::String) -> ReportReconstructSingleConfig

Load and process report reconstruct-single configuration from a YAML file.
"""
function load_report_reconstruct_single_config(config_path::String)::ReportReconstructSingleConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end
    
    # Get the directory containing the config file
    config_dir = dirname(abspath(config_path))
    
    # Load YAML configuration
    yaml_dict = Dict{String, Any}(YAML.load_file(config_path))
    config_yaml = from_dict(ReportReconstructSingleConfigYAML, yaml_dict)
    
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
        joinpath(config_dir, "report-reconstruct-single")
    end

    return ReportReconstructSingleConfig(
        processed_masts,
        output_dir,
        config_dir
    )
end

# Export all types and functions
export ReconstructionDataConfig, MastReconstructReportConfig, ProcessedMastReconstructConfig,
       ReconstructOutputConfig, ReportReconstructSingleConfigYAML, ReportReconstructSingleConfig,
       process_mast_reconstruct_config, load_report_reconstruct_single_config

end # module 