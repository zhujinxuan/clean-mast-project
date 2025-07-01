module WtTimeSeriesConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource

export WtTimeSeriesMast, WtTimeSeriesConfiguration

struct WtTimeSeriesMast
    name::String
    input::TimeSeriesSource
    output_dir::String
    target_heights::Vector{Float64}
end

struct WtTimeSeriesConfiguration
    masts::Vector{WtTimeSeriesMast}
end

# Serialization methods
function to_dict(t::WtTimeSeriesMast)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => t.name,
        "input" => to_dict(t.input),
        "output_dir" => t.output_dir,
        "target_heights" => t.target_heights
    )
end

function to_dict(t::WtTimeSeriesConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "masts" => [to_dict(m) for m in t.masts]
    )
end

# Deserialization methods
function from_dict(::Type{WtTimeSeriesConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(WtTimeSeriesMast, m) for m in dict["masts"]]
    return WtTimeSeriesConfiguration(masts)
end

function from_dict(::Type{WtTimeSeriesMast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    output_dir = dict["output_dir"]
    target_heights = Vector{Float64}(dict["target_heights"])
    return WtTimeSeriesMast(name, input, output_dir, target_heights)
end

end # module 