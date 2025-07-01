module RepresentativeYearConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource, TimeRange
import ..TrainMesoConfig: TrainMesoSource
using Dates

export RepresentativeYearMesoModel, RepresentativeYearMast, RepresentativeYearConfiguration

struct RepresentativeYearMesoModel
    method::String
    meso_name::String
    model_file::String
end

struct RepresentativeYearMast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
    time_range::TimeRange
    meso_model::RepresentativeYearMesoModel
end

struct RepresentativeYearConfiguration
    masts::Vector{RepresentativeYearMast}
    mesos::Vector{TrainMesoSource}
end

function to_dict(t :: RepresentativeYearMesoModel) :: Dict{String, Any}
    return Dict(
        "method" => t.method,
        "meso_name" => t.meso_name,
        "model_file" => t.model_file
    )
end

function to_dict(t :: RepresentativeYearMast) :: Dict{String, Any}
    return Dict(
        "name" => t.name,
        "input" => to_dict(t.input),
        "output" => to_dict(t.output),
        "time_range" => to_dict(t.time_range),
        "meso_model" => to_dict(t.meso_model)
    )
end

function to_dict(t :: RepresentativeYearConfiguration) :: Dict{String, Any}
    return Dict(
        "masts" => [to_dict(m) for m in t.masts],
        "mesos" => [to_dict(m) for m in t.mesos]
    )
end

# Deserialization methods
function from_dict(::Type{RepresentativeYearConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(RepresentativeYearMast, m) for m in dict["masts"]]
    mesos = [from_dict(TrainMesoSource, m) for m in dict["mesos"]]
    
    return RepresentativeYearConfiguration(masts, mesos)
end

function from_dict(::Type{RepresentativeYearMast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    output = from_dict(TimeSeriesSource, dict["output"])
    time_range = from_dict(TimeRange, dict["time_range"])
    meso_model = from_dict(RepresentativeYearMesoModel, dict["meso_model"])
    return RepresentativeYearMast(name, input, output, time_range, meso_model)
end

function from_dict(::Type{RepresentativeYearMesoModel}, dict::Dict{String, Any})
    method = dict["method"]
    meso_name = dict["meso_name"]
    model_file = dict["model_file"]
    return RepresentativeYearMesoModel(method, meso_name, model_file)
end

end # module 