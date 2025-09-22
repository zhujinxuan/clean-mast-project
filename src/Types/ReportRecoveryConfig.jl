module ReportRecoveryConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource, TimeRange
using Parameters

export ReportRecoveryMast, ReportRecoveryConfiguration, ReportRecoveryOutput

"""
    ReportRecoveryMast

Configuration for a single mast in the recovery report.
Contains data sources for all reconstruction stages.

# Fields
- `name::String`: Mast name (e.g., "nrg-17005")
- `tower_shading::TimeSeriesSource`: Data after tower shading processing
- `reconstruct_single::TimeSeriesSource`: Data after single-mast reconstruction
- `reconstruct_cross::Union{TimeSeriesSource, Nothing}`: Data after cross-mast reconstruction (optional)
- `reconstruct_meso::TimeSeriesSource`: Data after mesoscale reconstruction
- `time_range::TimeRange`: Time range for analysis (from reconstruct-meso configuration)
"""
@with_kw struct ReportRecoveryMast
    name::String
    tower_shading::TimeSeriesSource
    reconstruct_single::TimeSeriesSource
    reconstruct_cross::Union{TimeSeriesSource, Nothing}
    reconstruct_meso::TimeSeriesSource
    time_range::TimeRange
end

"""
    ReportRecoveryOutput

Output configuration for recovery report.

# Fields
- `report_dir::String`: Directory to save the report
- `report_filename::String`: Name of the main report file
"""
@with_kw struct ReportRecoveryOutput
    report_dir::String = "./report-masts/recovery"
    report_filename::String = "recovery-report.typ"
end

"""
    ReportRecoveryConfiguration

Complete configuration for data recovery status report.

# Fields
- `masts::Vector{ReportRecoveryMast}`: Masts to analyze
- `output::ReportRecoveryOutput`: Output configuration
"""
@with_kw struct ReportRecoveryConfiguration
    masts::Vector{ReportRecoveryMast}
    output::ReportRecoveryOutput = ReportRecoveryOutput()
end

# Serialization methods
function to_dict(mast::ReportRecoveryMast)::Dict{String, Any}
    result = Dict{String, Any}(
        "name" => mast.name,
        "tower_shading" => to_dict(mast.tower_shading),
        "reconstruct_single" => to_dict(mast.reconstruct_single),
        "reconstruct_meso" => to_dict(mast.reconstruct_meso),
        "time_range" => to_dict(mast.time_range)
    )

    # Only include reconstruct_cross if it exists
    if !isnothing(mast.reconstruct_cross)
        result["reconstruct_cross"] = to_dict(mast.reconstruct_cross)
    end

    return result
end

function from_dict(::Type{ReportRecoveryMast}, dict::Dict{String, Any})::ReportRecoveryMast
    # Handle optional reconstruct_cross field
    reconstruct_cross = haskey(dict, "reconstruct_cross") ?
                       from_dict(TimeSeriesSource, dict["reconstruct_cross"]) :
                       nothing

    return ReportRecoveryMast(
        name = dict["name"],
        tower_shading = from_dict(TimeSeriesSource, dict["tower_shading"]),
        reconstruct_single = from_dict(TimeSeriesSource, dict["reconstruct_single"]),
        reconstruct_cross = reconstruct_cross,
        reconstruct_meso = from_dict(TimeSeriesSource, dict["reconstruct_meso"]),
        time_range = from_dict(TimeRange, dict["time_range"])
    )
end

function to_dict(output::ReportRecoveryOutput)::Dict{String, Any}
    return Dict{String, Any}(
        "report_dir" => output.report_dir,
        "report_filename" => output.report_filename
    )
end

function from_dict(::Type{ReportRecoveryOutput}, dict::Dict{String, Any})::ReportRecoveryOutput
    return ReportRecoveryOutput(
        report_dir = dict["report_dir"],
        report_filename = dict["report_filename"]
    )
end

function to_dict(config::ReportRecoveryConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "masts" => [to_dict(mast) for mast in config.masts],
        "output" => to_dict(config.output)
    )
end

function from_dict(::Type{ReportRecoveryConfiguration}, dict::Dict{String, Any})::ReportRecoveryConfiguration
    return ReportRecoveryConfiguration(
        masts = [from_dict(ReportRecoveryMast, mast_dict) for mast_dict in dict["masts"]],
        output = from_dict(ReportRecoveryOutput, dict["output"])
    )
end

end # module
