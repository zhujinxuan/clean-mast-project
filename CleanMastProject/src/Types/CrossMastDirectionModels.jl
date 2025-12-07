"""
    CrossMastDirectionModels.jl

Wind direction model types for cross-mast reconstruction.
These models handle mast-to-mast wind direction relationships using offset corrections.
"""
module CrossMastDirectionModels

using ..SensorColumns: SensorColumn
using ..MastReferenceModel: AbstractDirectionReferenceModel
import ..Utils: from_dict, to_dict
using Parameters

export CrossMastDirectionPair, CrossMastDirectionModel

"""
    CrossMastDirectionPair

A single sensor pair relationship for wind direction reconstruction between two masts.

# Fields
- `target_sensor::SensorColumn`: Target mast wind direction sensor to be reconstructed
- `source_sensor::SensorColumn`: Source mast wind direction sensor used for reconstruction
- `offset::Float64`: Mean direction offset between sensors (degrees)
- `std_deviation::Float64`: Standard deviation of direction differences (degrees)
- `data_points::Int`: Number of data points used in direction analysis
"""
@with_kw struct CrossMastDirectionPair
    target_sensor::SensorColumn
    source_sensor::SensorColumn
    offset::Float64
    std_deviation::Float64
    data_points::Int
end

"""
    CrossMastDirectionModel <: AbstractDirectionReferenceModel

Complete wind direction model for cross-mast reconstruction containing all sensor pairs
between a target mast and source mast.

# Fields
- `target_mast_name::String`: Name of the target mast (to be reconstructed)
- `source_mast_name::String`: Name of the source mast (used for reconstruction)
- `pairs::Vector{CrossMastDirectionPair}`: All sensor pairs with their offset parameters
"""
@with_kw struct CrossMastDirectionModel <: AbstractDirectionReferenceModel
    target_mast_name::String
    source_mast_name::String
    pairs::Vector{CrossMastDirectionPair}
end

# from_dict implementations
function from_dict(::Type{CrossMastDirectionPair}, dict::Dict{String, Any})::CrossMastDirectionPair
    target_sensor = from_dict(SensorColumn, dict["target_sensor"])
    source_sensor = from_dict(SensorColumn, dict["source_sensor"])
    offset = dict["offset"]
    std_deviation = dict["std_deviation"]
    data_points = dict["data_points"]
    
    return CrossMastDirectionPair(target_sensor, source_sensor, offset, std_deviation, data_points)
end

function from_dict(::Type{CrossMastDirectionModel}, dict::Dict{String, Any})::CrossMastDirectionModel
    target_mast_name = dict["target_mast_name"]
    source_mast_name = dict["source_mast_name"]
    pairs = [from_dict(CrossMastDirectionPair, Dict{String, Any}(p)) for p in dict["pairs"]]
    
    return CrossMastDirectionModel(target_mast_name, source_mast_name, pairs)
end

# to_dict implementations
function to_dict(pair::CrossMastDirectionPair)::Dict{String, Any}
    return Dict{String, Any}(
        "target_sensor" => to_dict(pair.target_sensor),
        "source_sensor" => to_dict(pair.source_sensor),
        "offset" => pair.offset,
        "std_deviation" => pair.std_deviation,
        "data_points" => pair.data_points
    )
end

function to_dict(model::CrossMastDirectionModel)::Dict{String, Any}
    return Dict{String, Any}(
        "target_mast_name" => model.target_mast_name,
        "source_mast_name" => model.source_mast_name,
        "pairs" => [to_dict(p) for p in model.pairs]
    )
end

end # module 