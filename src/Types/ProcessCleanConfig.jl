module ProcessCleanConfig

import ..Utils: from_dict
using ..MastTimeSeries: TimeSeriesSource

export Mast, ProcessCleanConfiguration

struct Mast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
    rules::Union{String,Array}
end

struct ProcessCleanConfiguration
    masts::Vector{Mast}
end

function from_dict(::Type{ProcessCleanConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(Mast, m) for m in dict["masts"]]
    return ProcessCleanConfiguration(masts)
end

function from_dict(::Type{Mast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    output = from_dict(TimeSeriesSource, dict["output"])
    rules = dict["rules"]
    return Mast(name, input, output, rules)
end

end 