module ReportReconstructMesoConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource

export ReportReconstructMesoAnalysisSettings, ReportReconstructMesoMast, ReportReconstructMesoMeso, ReportReconstructMesoConfiguration

struct ReportReconstructMesoAnalysisSettings
    output_dir::String
end

struct ReportReconstructMesoMast
    name::String
    input::TimeSeriesSource
    wind_speed_report_heights::Vector{Float64}
end

struct ReportReconstructMesoMeso
    name::String
    input::TimeSeriesSource
    wind_speed_report_heights::Vector{Float64}
end

struct ReportReconstructMesoConfiguration
    masts::Vector{ReportReconstructMesoMast}
    mesos::Vector{ReportReconstructMesoMeso}
    analyze::ReportReconstructMesoAnalysisSettings
end

function to_dict(settings::ReportReconstructMesoAnalysisSettings)
    return Dict(
        "output_dir" => settings.output_dir
    )
end

function from_dict(::Type{ReportReconstructMesoAnalysisSettings}, dict::Dict{String, Any})
    output_dir = get(dict, "output_dir", "report-masts/reconstruct-meso")
    return ReportReconstructMesoAnalysisSettings(output_dir)
end

function to_dict(mast::ReportReconstructMesoMast)
    return Dict(
        "name" => mast.name,
        "input" => to_dict(mast.input),
        "wind_speed_report_heights" => mast.wind_speed_report_heights
    )
end

function from_dict(::Type{ReportReconstructMesoMast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    wind_speed_report_heights = Vector{Float64}(dict["wind_speed_report_heights"])
    return ReportReconstructMesoMast(name, input, wind_speed_report_heights)
end

function to_dict(meso::ReportReconstructMesoMeso)
    return Dict(
        "name" => meso.name,
        "input" => to_dict(meso.input),
        "wind_speed_report_heights" => meso.wind_speed_report_heights
    )
end

function from_dict(::Type{ReportReconstructMesoMeso}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    wind_speed_report_heights = Vector{Float64}(dict["wind_speed_report_heights"])
    return ReportReconstructMesoMeso(name, input, wind_speed_report_heights)
end

function to_dict(config::ReportReconstructMesoConfiguration)
    return Dict(
        "masts" => [to_dict(m) for m in config.masts],
        "mesos" => [to_dict(m) for m in config.mesos],
        "analyze" => to_dict(config.analyze)
    )
end

function from_dict(::Type{ReportReconstructMesoConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(ReportReconstructMesoMast, m) for m in dict["masts"]]
    mesos = [from_dict(ReportReconstructMesoMeso, m) for m in dict["mesos"]]
    analyze = from_dict(ReportReconstructMesoAnalysisSettings, dict["analyze"])
    return ReportReconstructMesoConfiguration(masts, mesos, analyze)
end

end # module
