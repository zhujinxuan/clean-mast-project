module ReportFrozenPeriodConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource
using Parameters

export FrozenThresholdSet, FrozenDetectionSettings, ReportFrozenPeriodMast,
       ReportFrozenPeriodOutput, ReportFrozenPeriodConfiguration

"""
    FrozenThresholdSet

One set of thresholds for frozen period detection.
Allows computing frozen periods for different sensor types (e.g., heated vs non-heated).

# Fields
- `name::String`: Threshold set name (e.g., "加热型", "非加热型")
- `temperature_threshold::Float64`: Maximum temperature for frozen condition (°C)
- `windspeed_change_threshold::Float64`: Maximum wind speed change within window (m/s)
- `winddirection_change_threshold::Float64`: Maximum wind direction change within window (degrees)
- `rh_threshold::Union{Float64, Nothing}`: Maximum relative humidity for frozen condition (%) - optional, only for 加热型
- `min_duration_seconds::Union{Int, Nothing}`: Minimum duration for frozen period (seconds) - optional
"""
@with_kw struct FrozenThresholdSet
    name::String
    temperature_threshold::Float64
    windspeed_change_threshold::Float64
    winddirection_change_threshold::Float64
    rh_threshold::Union{Float64, Nothing} = nothing
    min_duration_seconds::Union{Int, Nothing} = nothing
end

"""
    FrozenDetectionSettings

Detection settings containing multiple threshold configurations.
Supports computing frozen periods for both heated and non-heated sensors.

# Fields
- `thresholds::Vector{FrozenThresholdSet}`: Vector of threshold configurations
"""
@with_kw struct FrozenDetectionSettings
    thresholds::Vector{FrozenThresholdSet}
end

"""
    ReportFrozenPeriodMast

Configuration for analyzing one mast's frozen periods.
Uses raw data (before cleaning) as input.

# Fields
- `name::String`: Mast name (e.g., "010415")
- `input::TimeSeriesSource`: Raw data source from raw/ directory
"""
@with_kw struct ReportFrozenPeriodMast
    name::String
    input::TimeSeriesSource
end

"""
    ReportFrozenPeriodOutput

Output configuration for frozen period report.

# Fields
- `report_dir::String`: Directory to save the report (relative to report-masts/), default "./frozen-period"
- `report_filename::String`: Name of the main report file, default "frozen-period-report.typ"
"""
@with_kw struct ReportFrozenPeriodOutput
    report_dir::String = "./frozen-period"
    report_filename::String = "frozen-period-report.typ"
end

"""
    ReportFrozenPeriodConfiguration

Complete configuration for frozen period detection and reporting.

# Fields
- `masts::Vector{ReportFrozenPeriodMast}`: Masts to analyze
- `frozen_detection::FrozenDetectionSettings`: Detection settings with multiple threshold sets
- `output::ReportFrozenPeriodOutput`: Output configuration
"""
@with_kw struct ReportFrozenPeriodConfiguration
    masts::Vector{ReportFrozenPeriodMast}
    frozen_detection::FrozenDetectionSettings
    output::ReportFrozenPeriodOutput = ReportFrozenPeriodOutput()
end

# Serialization methods
function to_dict(threshold::FrozenThresholdSet)::Dict{String, Any}
    d = Dict{String, Any}(
        "name" => threshold.name,
        "temperature_threshold" => threshold.temperature_threshold,
        "windspeed_change_threshold" => threshold.windspeed_change_threshold,
        "winddirection_change_threshold" => threshold.winddirection_change_threshold
    )
    if !isnothing(threshold.rh_threshold)
        d["rh_threshold"] = threshold.rh_threshold
    end
    if !isnothing(threshold.min_duration_seconds)
        d["min_duration_seconds"] = threshold.min_duration_seconds
    end
    return d
end

function from_dict(::Type{FrozenThresholdSet}, dict::Dict{String, Any})::FrozenThresholdSet
    return FrozenThresholdSet(
        name = dict["name"],
        temperature_threshold = dict["temperature_threshold"],
        windspeed_change_threshold = dict["windspeed_change_threshold"],
        winddirection_change_threshold = dict["winddirection_change_threshold"],
        rh_threshold = get(dict, "rh_threshold", nothing),
        min_duration_seconds = get(dict, "min_duration_seconds", nothing)
    )
end

function to_dict(settings::FrozenDetectionSettings)::Dict{String, Any}
    return Dict{String, Any}(
        "thresholds" => [to_dict(t) for t in settings.thresholds]
    )
end

function from_dict(::Type{FrozenDetectionSettings}, dict::Dict{String, Any})::FrozenDetectionSettings
    return FrozenDetectionSettings(
        thresholds = [from_dict(FrozenThresholdSet, t) for t in dict["thresholds"]]
    )
end

function to_dict(mast::ReportFrozenPeriodMast)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => mast.name,
        "input" => to_dict(mast.input)
    )
end

function from_dict(::Type{ReportFrozenPeriodMast}, dict::Dict{String, Any})::ReportFrozenPeriodMast
    return ReportFrozenPeriodMast(
        name = dict["name"],
        input = from_dict(TimeSeriesSource, dict["input"])
    )
end

function to_dict(output::ReportFrozenPeriodOutput)::Dict{String, Any}
    return Dict{String, Any}(
        "report_dir" => output.report_dir,
        "report_filename" => output.report_filename
    )
end

function from_dict(::Type{ReportFrozenPeriodOutput}, dict::Dict{String, Any})::ReportFrozenPeriodOutput
    return ReportFrozenPeriodOutput(
        report_dir = dict["report_dir"],
        report_filename = dict["report_filename"]
    )
end

function to_dict(config::ReportFrozenPeriodConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "masts" => [to_dict(mast) for mast in config.masts],
        "frozen_detection" => to_dict(config.frozen_detection),
        "output" => to_dict(config.output)
    )
end

function from_dict(::Type{ReportFrozenPeriodConfiguration}, dict::Dict{String, Any})::ReportFrozenPeriodConfiguration
    return ReportFrozenPeriodConfiguration(
        masts = [from_dict(ReportFrozenPeriodMast, mast_dict) for mast_dict in dict["masts"]],
        frozen_detection = from_dict(FrozenDetectionSettings, dict["frozen_detection"]),
        output = from_dict(ReportFrozenPeriodOutput, dict["output"])
    )
end

end # module
