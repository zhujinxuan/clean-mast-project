module GuessMastFromMesoConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource, TimeRange

export GuessMastTarget, GuessMastMeso, GuessMastOutput, GuessMastFromMesoConfiguration

struct GuessMastTarget
    height::Float64
    mean_speed::Float64
end

struct GuessMastMeso
    name::String
    input::TimeSeriesSource
    time_range::TimeRange
end

struct GuessMastOutput
    name::String
    sensors::String
    data::String
end

struct GuessMastFromMesoConfiguration
    meso::GuessMastMeso
    output::GuessMastOutput
    targets::Vector{GuessMastTarget}
end

function to_dict(target::GuessMastTarget)::Dict{String, Any}
    return Dict{String, Any}(
        "height" => target.height,
        "mean_speed" => target.mean_speed
    )
end

function to_dict(meso::GuessMastMeso)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => meso.name,
        "input" => to_dict(meso.input),
        "time_range" => to_dict(meso.time_range)
    )
end

function to_dict(output::GuessMastOutput)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => output.name,
        "sensors" => output.sensors,
        "data" => output.data
    )
end

function to_dict(config::GuessMastFromMesoConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "meso" => to_dict(config.meso),
        "output" => to_dict(config.output),
        "targets" => [to_dict(t) for t in config.targets]
    )
end

function from_dict(::Type{GuessMastTarget}, dict::Dict{String, Any})::GuessMastTarget
    return GuessMastTarget(
        dict["height"],
        dict["mean_speed"]
    )
end

function from_dict(::Type{GuessMastMeso}, dict::Dict{String, Any})::GuessMastMeso
    return GuessMastMeso(
        dict["name"],
        from_dict(TimeSeriesSource, dict["input"]),
        from_dict(TimeRange, dict["time_range"])
    )
end

function from_dict(::Type{GuessMastOutput}, dict::Dict{String, Any})::GuessMastOutput
    return GuessMastOutput(
        dict["name"],
        dict["sensors"],
        dict["data"]
    )
end

function from_dict(::Type{GuessMastFromMesoConfiguration}, dict::Dict{String, Any})::GuessMastFromMesoConfiguration
    return GuessMastFromMesoConfiguration(
        from_dict(GuessMastMeso, dict["meso"]),
        from_dict(GuessMastOutput, dict["output"]),
        [from_dict(GuessMastTarget, t) for t in dict["targets"]]
    )
end

end
