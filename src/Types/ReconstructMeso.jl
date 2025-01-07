module ReconstructMeso
using DataFrames
using ..Utils
using ..MastTimeSeries
using Dates

struct WindSpeedSectorModel
    sector_start::Float64  # Start angle of the sector (inclusive)
    sector_end::Float64    # End angle of the sector (exclusive)
    slope::Float64         # k in mast_speed = k * meso_speed + b
    intercept::Float64     # b in mast_speed = k * meso_speed + b
end

struct WindSpeedTrainResult
    mastSensor::SensorColumn
    mesoSensor::SensorColumn
    sector_models::Vector{WindSpeedSectorModel}  # Models for each direction sector
end

struct WindDirectionTrainResult
    mastSensor::SensorColumn
    mesoSensor::SensorColumn
    diff::Float64  # mast_direction = meso_direction + diff
end

struct TrainingTimeRange
    min::DateTime
    max::DateTime
    
    function TrainingTimeRange(min::DateTime, max::DateTime)
        min <= max || throw(ArgumentError("min must be <= max"))
        new(min, max)
    end
end

# Type alias for training results
const WindSpeedTrainResults = Dict{Symbol, WindSpeedTrainResult}
const WindDirectionTrainResults = Dict{Symbol, WindDirectionTrainResult}

function from_dict(::Type{WindSpeedSectorModel}, dict::Dict{String, Any})::WindSpeedSectorModel
    WindSpeedSectorModel(
        dict["sector_start"],
        dict["sector_end"],
        dict["slope"],
        dict["intercept"]
    )
end

function to_dict(model::WindSpeedSectorModel)::Dict{String, Any}
    Dict{String, Any}(
        "sector_start" => model.sector_start,
        "sector_end" => model.sector_end,
        "slope" => model.slope,
        "intercept" => model.intercept
    )
end

function from_dict(::Type{WindSpeedTrainResult}, dict::Dict{String, Any})::WindSpeedTrainResult
    WindSpeedTrainResult(
        from_dict(SensorColumn, dict["mastSensor"]),
        from_dict(SensorColumn, dict["mesoSensor"]),
        [from_dict(WindSpeedSectorModel, m) for m in dict["sector_models"]]
    )
end

function to_dict(wstr::WindSpeedTrainResult)::Dict{String, Any}
    Dict{String, Any}(
        "mastSensor" => to_dict(wstr.mastSensor),
        "mesoSensor" => to_dict(wstr.mesoSensor),
        "sector_models" => [to_dict(m) for m in wstr.sector_models]
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

export WindSpeedSectorModel, WindSpeedTrainResult, WindDirectionTrainResult, 
       WindSpeedTrainResults, WindDirectionTrainResults, TrainingTimeRange

end 