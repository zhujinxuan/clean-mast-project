module ReconstructSingleConfig

import ..Utils: from_dict
using ..MastTimeSeries: TimeSeriesSource

export ReconstructSingleMast, ReconstructSingleConfiguration

struct ReconstructSingleMast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
end

struct ReconstructSingleConfiguration
    masts::Vector{ReconstructSingleMast}
end

# Deserialization methods
function from_dict(::Type{ReconstructSingleConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(ReconstructSingleMast, m) for m in dict["masts"]]
    return ReconstructSingleConfiguration(masts)
end

function from_dict(::Type{ReconstructSingleMast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    output = from_dict(TimeSeriesSource, dict["output"])
    return ReconstructSingleMast(name, input, output)
end

end # module 