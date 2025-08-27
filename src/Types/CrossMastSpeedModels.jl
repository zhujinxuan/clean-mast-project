"""
    CrossMastSpeedModel.jl

Wind speed model types for cross-mast reconstruction.
These models handle mast-to-mast wind speed relationships using linear regression.
"""
module CrossMastSpeedModels

using ..SensorColumns: SensorColumn
using ..MastReferenceModel: AbstractSpeedReferenceModel
import ..Utils: from_dict, to_dict
using Parameters

export CrossMastSpeedPair, CrossMastSpeedModel

"""
    CrossMastSpeedPair

A single sensor pair relationship for wind speed reconstruction between two masts.

# Fields
- `target_sensor::SensorColumn`: Target mast wind speed sensor to be reconstructed
- `source_sensor::SensorColumn`: Source mast wind speed sensor used for reconstruction
- `correlation::Float64`: Pearson correlation coefficient between sensors
- `slope::Float64`: Linear regression slope (target = slope * source + intercept)
- `intercept::Float64`: Linear regression intercept
- `data_points::Int`: Number of data points used in correlation analysis
"""
@with_kw struct CrossMastSpeedPair
    target_sensor::SensorColumn
    source_sensor::SensorColumn
    correlation::Float64
    slope::Float64
    intercept::Float64
    data_points::Int
end

"""
    CrossMastSpeedModel <: AbstractSpeedReferenceModel

Complete wind speed model for cross-mast reconstruction containing all sensor pairs
between a target mast and source mast.

# Fields
- `target_mast_name::String`: Name of the target mast (to be reconstructed)
- `source_mast_name::String`: Name of the source mast (used for reconstruction)
- `pairs::Vector{CrossMastSpeedPair}`: All sensor pairs with their regression parameters
"""
@with_kw struct CrossMastSpeedModel <: AbstractSpeedReferenceModel
    target_mast_name::String
    source_mast_name::String
    pairs::Vector{CrossMastSpeedPair}
end

# from_dict implementations
function from_dict(::Type{CrossMastSpeedPair}, dict::Dict{String, Any})::CrossMastSpeedPair
    target_sensor = from_dict(SensorColumn, dict["target_sensor"])
    source_sensor = from_dict(SensorColumn, dict["source_sensor"])
    correlation = dict["correlation"]
    slope = dict["slope"]
    intercept = dict["intercept"]
    data_points = dict["data_points"]
    
    return CrossMastSpeedPair(
        target_sensor, source_sensor, correlation,
        slope, intercept, data_points
    )
end

function from_dict(::Type{CrossMastSpeedModel}, dict::Dict{String, Any})::CrossMastSpeedModel
    target_mast_name = dict["target_mast_name"]
    source_mast_name = dict["source_mast_name"]
    pairs = [from_dict(CrossMastSpeedPair, Dict{String, Any}(p)) for p in dict["pairs"]]
    
    return CrossMastSpeedModel(target_mast_name, source_mast_name, pairs)
end

# to_dict implementations
function to_dict(pair::CrossMastSpeedPair)::Dict{String, Any}
    return Dict{String, Any}(
        "target_sensor" => to_dict(pair.target_sensor),
        "source_sensor" => to_dict(pair.source_sensor),
        "correlation" => pair.correlation,
        "slope" => pair.slope,
        "intercept" => pair.intercept,
        "data_points" => pair.data_points
    )
end

function to_dict(model::CrossMastSpeedModel)::Dict{String, Any}
    return Dict{String, Any}(
        "target_mast_name" => model.target_mast_name,
        "source_mast_name" => model.source_mast_name,
        "pairs" => [to_dict(p) for p in model.pairs]
    )
end

end # module 