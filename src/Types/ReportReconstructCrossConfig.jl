"""
    ReportReconstructCrossConfig.jl

Configuration types for the report reconstruct-cross command.
Generates analysis reports and visualizations for cross-mast relationships.
"""
module ReportReconstructCrossConfig

using ..MastTimeSeries: TimeSeriesSource
import ..Utils: from_dict, to_dict
using Parameters

export ReportReconstructCrossConfiguration, ReportReconstructCrossMast, ReportReconstructCrossSettings

"""
    ReportReconstructCrossMast

Configuration for a single mast in cross-mast analysis.

# Fields
- `name::String`: Unique name for the mast
- `input::TimeSeriesSource`: Input data source (data file and sensors configuration)
"""
@with_kw struct ReportReconstructCrossMast
    name::String
    before_reconstruction::TimeSeriesSource
    after_reconstruction::TimeSeriesSource
end

"""
    ReportReconstructCrossSettings

Settings for cross-mast analysis output and report generation.

# Fields
- `output_dir::String`: Directory where analysis results will be saved (default: "./report-masts/cross-mast")
- `include_plots::Bool`: Whether to generate plots (default: true)
- `language::String`: Report language (default: "zh", Chinese)
"""
@with_kw struct ReportReconstructCrossSettings
    output_dir::String = "./report-masts/cross-mast"
    include_plots::Bool = true
    language::String = "zh"  # Chinese by default
end

"""
    ReportReconstructCrossConfiguration

Main configuration struct for report reconstruct-cross command.

# Fields
- `masts::Vector{ReportReconstructCrossMast}`: List of masts to analyze
- `analyze::ReportReconstructCrossSettings`: Analysis output settings
"""
@with_kw struct ReportReconstructCrossConfiguration
    masts::Vector{ReportReconstructCrossMast}
    analyze::ReportReconstructCrossSettings
end

# from_dict implementations
function from_dict(::Type{ReportReconstructCrossMast}, dict::Dict{String, Any})::ReportReconstructCrossMast
    name = dict["name"]
    before_reconstruction = from_dict(TimeSeriesSource, dict["before_reconstruction"])
    after_reconstruction = from_dict(TimeSeriesSource, dict["after_reconstruction"])
    return ReportReconstructCrossMast(name, before_reconstruction, after_reconstruction)
end

function from_dict(::Type{ReportReconstructCrossSettings}, dict::Dict{String, Any})::ReportReconstructCrossSettings
    output_dir = get(dict, "output_dir", "./report-masts/cross-mast")
    include_plots = get(dict, "include_plots", true)
    language = get(dict, "language", "zh")

    return ReportReconstructCrossSettings(
        output_dir, include_plots, language
    )
end

function from_dict(::Type{ReportReconstructCrossConfiguration}, dict::Dict{String, Any})::ReportReconstructCrossConfiguration
    masts = [from_dict(ReportReconstructCrossMast, Dict{String, Any}(m)) for m in dict["masts"]]
    analyze = from_dict(ReportReconstructCrossSettings, Dict{String, Any}(dict["analyze"]))
    return ReportReconstructCrossConfiguration(masts, analyze)
end

# to_dict implementations
function to_dict(mast::ReportReconstructCrossMast)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => mast.name,
        "before_reconstruction" => to_dict(mast.before_reconstruction),
        "after_reconstruction" => to_dict(mast.after_reconstruction)
    )
end

function to_dict(settings::ReportReconstructCrossSettings)::Dict{String, Any}
    return Dict{String, Any}(
        "output_dir" => settings.output_dir,
        "include_plots" => settings.include_plots,
        "language" => settings.language
    )
end

function to_dict(config::ReportReconstructCrossConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "masts" => [to_dict(mast) for mast in config.masts],
        "analyze" => to_dict(config.analyze)
    )
end

end # module 