module TrainMesoResultsTypes

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource

export TrainMesoEntity, TrainMesoSpeedMetrics, TrainMesoPairResult, TrainMesoResults

"""
    TrainMesoEntity

Entity wrapper holding a name and its input TimeSeriesSource.
Used for both mast and meso entries in train-meso-results.
"""
struct TrainMesoEntity
    name::String
    input::TimeSeriesSource
end

"""
    TrainMesoSpeedMetrics

Metrics for a trained meso model method for a mast×meso pair.
For now we only emit windspeed "1-sector"; fields can extend later.
"""
struct TrainMesoSpeedMetrics
    method::String          # e.g. "1-sector"
    correlation::Float64
end

"""
    TrainMesoPairResult

One mast×meso pair with entities and an array of model metrics entries.
"""
struct TrainMesoPairResult
    mast::TrainMesoEntity
    meso::TrainMesoEntity
    models::Vector{TrainMesoSpeedMetrics}
end

"""
    TrainMesoResults

Top-level container with all mast×meso pairs.
"""
struct TrainMesoResults
    pairs::Vector{TrainMesoPairResult}
end

# ---------------- Serialization ----------------

function to_dict(e::TrainMesoEntity)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => e.name,
        "input" => to_dict(e.input)
    )
end

function from_dict(::Type{TrainMesoEntity}, dict::Dict{String, Any})::TrainMesoEntity
    return TrainMesoEntity(
        dict["name"],
        from_dict(TimeSeriesSource, dict["input"])
    )
end

function to_dict(m::TrainMesoSpeedMetrics)::Dict{String, Any}
    return Dict{String, Any}(
        "method" => m.method,
        "correlation" => m.correlation,
    )
end

function from_dict(::Type{TrainMesoSpeedMetrics}, dict::Dict{String, Any})::TrainMesoSpeedMetrics
    return TrainMesoSpeedMetrics(
        dict["method"],
        Float64(dict["correlation"]),
    )
end

function to_dict(p::TrainMesoPairResult)::Dict{String, Any}
    return Dict{String, Any}(
        "mast" => to_dict(p.mast),
        "meso" => to_dict(p.meso),
        "models" => [to_dict(m) for m in p.models],
    )
end

function from_dict(::Type{TrainMesoPairResult}, dict::Dict{String, Any})::TrainMesoPairResult
    mast = from_dict(TrainMesoEntity, dict["mast"])
    meso = from_dict(TrainMesoEntity, dict["meso"])
    models = haskey(dict, "models") ? [from_dict(TrainMesoSpeedMetrics, m) for m in dict["models"]] : TrainMesoSpeedMetrics[]
    return TrainMesoPairResult(mast, meso, models)
end

function to_dict(r::TrainMesoResults)::Dict{String, Any}
    return Dict{String, Any}(
        "pairs" => [to_dict(p) for p in r.pairs]
    )
end

function from_dict(::Type{TrainMesoResults}, dict::Dict{String, Any})::TrainMesoResults
    pairs = haskey(dict, "pairs") ? [from_dict(TrainMesoPairResult, p) for p in dict["pairs"]] : TrainMesoPairResult[]
    return TrainMesoResults(pairs)
end

end # module

