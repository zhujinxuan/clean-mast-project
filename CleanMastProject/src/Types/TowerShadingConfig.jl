module TowerShadingConfig

import ..Utils: from_dict
using ..MastTimeSeries: TimeSeriesSource

export TowerShadingMast, TowerShadingConfiguration

struct TowerShadingMast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
end

struct TowerShadingConfiguration
    masts::Vector{TowerShadingMast}
end

# Deserialization methods
function from_dict(::Type{TowerShadingConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(TowerShadingMast, m) for m in dict["masts"]]
    return TowerShadingConfiguration(masts)
end

function from_dict(::Type{TowerShadingMast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    output = from_dict(TimeSeriesSource, dict["output"])
    return TowerShadingMast(name, input, output)
end

end # module 