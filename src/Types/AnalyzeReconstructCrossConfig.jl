"""
    AnalyzeReconstructCrossConfiguration.jl

Configuration types for the analyze-reconstruct-cross command.
Generates analysis reports and visualizations for cross-mast relationships.
"""
module AnalyzeReconstructCrossConfig

using ..MastTimeSeries: TimeSeriesSource
import ..Utils: from_dict, to_dict
using Parameters

export AnalyzeReconstructCrossConfiguration, AnalyzeReconstructCrossMast, AnalyzeReconstructCrossSettings

"""
    AnalyzeReconstructCrossMast

Configuration for a single mast in cross-mast analysis.

# Fields
- `name::String`: Unique name for the mast
- `input::TimeSeriesSource`: Input data source (data file and sensors configuration)
"""
@with_kw struct AnalyzeReconstructCrossMast
    name::String
    input::TimeSeriesSource
end

"""
    AnalyzeReconstructCrossSettings

Settings for cross-mast analysis output and report generation.

# Fields
- `output_dir::String`: Directory where analysis results will be saved (default: "./analyze-reconstruct-cross")
- `include_plots::Bool`: Whether to generate plots (default: true)
- `language::String`: Report language (default: "zh", Chinese)
"""
@with_kw struct AnalyzeReconstructCrossSettings
    output_dir::String = "./analyze-reconstruct-cross"
    include_plots::Bool = true
    language::String = "zh"  # Chinese by default
end

"""
    AnalyzeReconstructCrossConfiguration

Main configuration struct for analyze-reconstruct-cross command.

# Fields
- `masts::Vector{AnalyzeReconstructCrossMast}`: List of masts to analyze
- `analyze::AnalyzeReconstructCrossSettings`: Analysis output settings
"""
@with_kw struct AnalyzeReconstructCrossConfiguration
    masts::Vector{AnalyzeReconstructCrossMast}
    analyze::AnalyzeReconstructCrossSettings
end

# from_dict implementations
function from_dict(::Type{AnalyzeReconstructCrossMast}, dict::Dict{String, Any})::AnalyzeReconstructCrossMast
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    return AnalyzeReconstructCrossMast(name, input)
end

function from_dict(::Type{AnalyzeReconstructCrossSettings}, dict::Dict{String, Any})::AnalyzeReconstructCrossSettings
    output_dir = get(dict, "output_dir", "./analyze-reconstruct-cross")
    include_plots = get(dict, "include_plots", true)
    language = get(dict, "language", "zh")
    
    return AnalyzeReconstructCrossSettings(
        output_dir, include_plots, language
    )
end

function from_dict(::Type{AnalyzeReconstructCrossConfiguration}, dict::Dict{String, Any})::AnalyzeReconstructCrossConfiguration
    masts = [from_dict(AnalyzeReconstructCrossMast, Dict{String, Any}(m)) for m in dict["masts"]]
    analyze = from_dict(AnalyzeReconstructCrossSettings, Dict{String, Any}(dict["analyze"]))
    return AnalyzeReconstructCrossConfiguration(masts, analyze)
end

# to_dict implementations
function to_dict(mast::AnalyzeReconstructCrossMast)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => mast.name,
        "input" => to_dict(mast.input)
    )
end

function to_dict(settings::AnalyzeReconstructCrossSettings)::Dict{String, Any}
    return Dict{String, Any}(
        "output_dir" => settings.output_dir,
        "include_plots" => settings.include_plots,
        "language" => settings.language
    )
end

function to_dict(config::AnalyzeReconstructCrossConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "masts" => [to_dict(mast) for mast in config.masts],
        "analyze" => to_dict(config.analyze)
    )
end

end # module 