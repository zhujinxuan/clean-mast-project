module ReportCleanConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource
using Parameters

export ReportCleanMast, ReportCleanMastGroup, ReportCleanOutput, ReportCleanConfiguration

@with_kw struct ReportCleanMast
    name::String
    input::TimeSeriesSource
end

@with_kw struct ReportCleanMastGroup
    masts::Vector{ReportCleanMast}
end

@with_kw struct ReportCleanOutput
    report_dir::String = "./report-masts/clean"
    report_filename::String = "report.typ"
end

@with_kw struct ReportCleanConfiguration
    raw::ReportCleanMastGroup
    clean::ReportCleanMastGroup
    output::ReportCleanOutput = ReportCleanOutput()
end

# from_dict implementations using existing pattern
function from_dict(::Type{ReportCleanMast}, dict::Dict{String, Any})
    return ReportCleanMast(
        name = dict["name"],
        input = from_dict(TimeSeriesSource, dict["input"])
    )
end

function from_dict(::Type{ReportCleanMastGroup}, dict::Dict{String, Any})
    return ReportCleanMastGroup(
        masts = [from_dict(ReportCleanMast, m) for m in dict["masts"]]
    )
end

function from_dict(::Type{ReportCleanOutput}, dict::Dict{String, Any})
    return ReportCleanOutput(
        report_dir = get(dict, "report_dir", "./report-masts/clean"),
        report_filename = get(dict, "report_filename", "report.typ")
    )
end

function from_dict(::Type{ReportCleanConfiguration}, dict::Dict{String, Any})
    return ReportCleanConfiguration(
        raw = from_dict(ReportCleanMastGroup, dict["raw"]),
        clean = from_dict(ReportCleanMastGroup, dict["clean"]),
        output = haskey(dict, "output") ? from_dict(ReportCleanOutput, dict["output"]) : ReportCleanOutput()
    )
end

# to_dict implementations for saving configurations
function to_dict(mast::ReportCleanMast)
    return Dict{String, Any}(
        "name" => mast.name,
        "input" => to_dict(mast.input)
    )
end

function to_dict(group::ReportCleanMastGroup)
    return Dict{String, Any}(
        "masts" => [to_dict(mast) for mast in group.masts]
    )
end

function to_dict(output::ReportCleanOutput)
    return Dict{String, Any}(
        "report_dir" => output.report_dir,
        "report_filename" => output.report_filename
    )
end

function to_dict(config::ReportCleanConfiguration)
    return Dict{String, Any}(
        "raw" => to_dict(config.raw),
        "clean" => to_dict(config.clean),
        "output" => to_dict(config.output)
    )
end

end # module
