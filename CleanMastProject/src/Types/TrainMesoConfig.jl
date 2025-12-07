module TrainMesoConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource

export TrainMesoMast, TrainMesoSource, TrainMesoModel, TrainMesoConfiguration

struct TrainMesoMast
    name::String
    input::TimeSeriesSource
end

struct TrainMesoSource
    name::String
    input::TimeSeriesSource
end

struct TrainMesoModel
    mast_name::String
    meso_name::String
    method::String  # "16-sector", "1-sector", "constant-direction-offset"
    output::String  # path to .jld2 file
end

struct TrainMesoConfiguration
    masts::Vector{TrainMesoMast}
    mesos::Vector{TrainMesoSource}
    models::Vector{TrainMesoModel}
end

function to_dict(config::TrainMesoConfiguration)::Dict{String, Any}
    Dict{String, Any}(
        "masts" => [to_dict(m) for m in config.masts],
        "mesos" => [to_dict(m) for m in config.mesos],
        "models" => [to_dict(m) for m in config.models]
    )
end
function to_dict(config::TrainMesoMast)::Dict{String, Any}
    Dict{String, Any}(
        "name" => config.name,
        "input" => to_dict(config.input)
    )
end
function to_dict(config::TrainMesoSource)::Dict{String, Any}    
    Dict{String, Any}(
        "name" => config.name,
        "input" => to_dict(config.input)
    )
end
function to_dict(config::TrainMesoModel)::Dict{String, Any}
    Dict{String, Any}(
        "mast_name" => config.mast_name,
        "meso_name" => config.meso_name,
        "method" => config.method,
        "output" => config.output
    )
end

# Deserialization methods
function from_dict(::Type{TrainMesoConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(TrainMesoMast, m) for m in dict["masts"]]
    
    mesos = [from_dict(TrainMesoSource, m) for m in dict["mesos"]]
    
    models = [from_dict(TrainMesoModel, m) for m in dict["models"]]
    return TrainMesoConfiguration(masts, mesos, models)
end

function from_dict(::Type{TrainMesoMast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    return TrainMesoMast(name, input)
end

function from_dict(::Type{TrainMesoSource}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    return TrainMesoSource(name, input)
end

function from_dict(::Type{TrainMesoModel}, dict::Dict{String, Any})
    mast_name = dict["mast_name"]
    meso_name = dict["meso_name"]
    method = dict["method"]
    output = dict["output"]
    return TrainMesoModel(mast_name, meso_name, method, output)
end

end # module 