module ReconstructMeso
using DataFrames
using ..Utils
using ..MastTimeSeries
using Dates

struct WindSpeedTrainResult
    mastSensor::SensorColumn
    mesoSensor::SensorColumn
    slope::Float64
    intercept::Float64
end

struct WindDirectionTrainResult
    mastSensor::SensorColumn
    mesoSensor::SensorColumn
    diff::Float64
end

# Type alias for training results
const WindSpeedTrainResults = Dict{Symbol, WindSpeedTrainResult}
const WindDirectionTrainResults = Dict{Symbol, WindDirectionTrainResult}

function from_dict(::Type{WindSpeedTrainResult}, dict::Dict{String, Any})::WindSpeedTrainResult
    WindSpeedTrainResult(
        from_dict(SensorColumn, dict["mastSensor"]),
        from_dict(SensorColumn, dict["mesoSensor"]),
        dict["slope"],
        dict["intercept"]
    )
end

function to_dict(wstr::WindSpeedTrainResult)::Dict{String, Any}
    Dict{String, Any}(
        "mastSensor" => to_dict(wstr.mastSensor),
        "mesoSensor" => to_dict(wstr.mesoSensor),
        "slope" => wstr.slope,
        "intercept" => wstr.intercept
    )
end

function from_dict(::Type{WindDirectionTrainResult}, dict::Dict{String, Any})::WindDirectionTrainResult
    WindDirectionTrainResult(
        from_dict(SensorColumn, dict["mastSensor"]),
        from_dict(SensorColumn, dict["mesoSensor"]),
        dict["diff"]
    )
end

function to_dict(wdtr::WindDirectionTrainResult)::Dict{String, Any}
    Dict{String, Any}(
        "mastSensor" => to_dict(wdtr.mastSensor),
        "mesoSensor" => to_dict(wdtr.mesoSensor),
        "diff" => wdtr.diff
    )
end

export WindSpeedTrainResult, WindDirectionTrainResult, WindSpeedTrainResults, WindDirectionTrainResults

end 