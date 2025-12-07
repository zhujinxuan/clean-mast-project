module ReconstructMesoConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource, TimeRange
using ..TrainMesoConfig: TrainMesoSource
using Dates

export ReconstructMesoModelSpec, ReconstructMesoModels, ReconstructMesoMast, ReconstructMesoConfiguration

struct ReconstructMesoModelSpec
    method::String
    meso_name::String
    model_file::String
end

struct ReconstructMesoModels
    windspeed::ReconstructMesoModelSpec
    winddirection::ReconstructMesoModelSpec
end

struct ReconstructMesoMast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
    time_range::TimeRange
    models::ReconstructMesoModels
end


struct ReconstructMesoConfiguration
    masts::Vector{ReconstructMesoMast}
    mesos::Vector{TrainMesoSource}
end

function to_dict(config::ReconstructMesoConfiguration)
    return Dict(
        "masts" => [to_dict(m) for m in config.masts],
        "mesos" => [to_dict(m) for m in config.mesos]
    )
end
function to_dict(config::ReconstructMesoMast)
    return Dict(
        "name" => config.name,
        "input" => to_dict(config.input),
        "output" => to_dict(config.output),
        "time_range" => to_dict(config.time_range),
        "models" => to_dict(config.models)
    )
end
function to_dict(config::ReconstructMesoModels)
    return Dict(
        "windspeed" => to_dict(config.windspeed),
        "winddirection" => to_dict(config.winddirection)
    )
end
function to_dict(config::ReconstructMesoModelSpec)
    return Dict(
        "method" => config.method,
        "meso_name" => config.meso_name,
        "model_file" => config.model_file
    )
end

# Deserialization methods
function from_dict(::Type{ReconstructMesoConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(ReconstructMesoMast, m) for m in dict["masts"]]
    mesos = [from_dict(TrainMesoSource, m) for m in dict["mesos"]]
    
    return ReconstructMesoConfiguration(masts, mesos)
end

function from_dict(::Type{ReconstructMesoMast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    output = from_dict(TimeSeriesSource, dict["output"])
    time_range = from_dict(TimeRange, dict["time_range"])
    models = from_dict(ReconstructMesoModels, dict["models"])
    return ReconstructMesoMast(name, input, output, time_range, models)
end


function from_dict(::Type{ReconstructMesoModels}, dict::Dict{String, Any})
    windspeed = from_dict(ReconstructMesoModelSpec, dict["windspeed"])
    winddirection = from_dict(ReconstructMesoModelSpec, dict["winddirection"])
    return ReconstructMesoModels(windspeed, winddirection)
end

function from_dict(::Type{ReconstructMesoModelSpec}, dict::Dict{String, Any})
    method = dict["method"]
    meso_name = dict["meso_name"]
    model_file = dict["model_file"]
    return ReconstructMesoModelSpec(method, meso_name, model_file)
end

end # module 