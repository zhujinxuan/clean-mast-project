"""
    CrossMastTrainParams.jl

Parameter types for training cross-mast reconstruction models.
These structs define configurable filtering criteria for model training.
"""
module CrossMastTrainParams

using Parameters
import ..Utils: from_dict, to_dict

export CrossMastSpeedTrainParams, CrossMastDirectionTrainParams

"""
    CrossMastSpeedTrainParams

Parameters for training CrossMastSpeedModel with configurable filtering criteria.

# Fields
- `target_name::String`: Name of target mast (required, no default)
- `source_name::String`: Name of source mast (required, no default)
- `min_data_points::Int`: Minimum concurrent data points required (default: 100)
- `min_correlation::Float64`: Minimum correlation threshold (default: 0.0, recommend: 0.7)
- `exclude_nan_results::Bool`: Filter out NaN/Inf values (default: true)

# Usage
```julia
# Analyze command (permissive filtering)
params = CrossMastSpeedTrainParams(target_name="Mast1", source_name="Mast2")

# Recommend command (strict filtering)
strict_params = CrossMastSpeedTrainParams(
    target_name="Mast1", 
    source_name="Mast2",
    min_correlation=0.7
)
```
"""
@with_kw struct CrossMastSpeedTrainParams
    # Required names (no defaults)
    target_name::String
    source_name::String
    
    # Data quality filters (with defaults)
    min_data_points::Int = 100
    min_correlation::Float64 = 0.0           # recommend: 0.7
    exclude_nan_results::Bool = true
end

"""
    CrossMastDirectionTrainParams

Parameters for training CrossMastDirectionModel with configurable filtering criteria.

# Fields
- `target_name::String`: Name of target mast (required, no default)
- `source_name::String`: Name of source mast (required, no default)
- `min_data_points::Int`: Minimum concurrent data points required (default: 100)
- `max_std_deviation::Float64`: Maximum standard deviation threshold (default: Inf, recommend: 45.0)
- `max_abs_offset::Float64`: Maximum absolute offset threshold (default: Inf, recommend: 45.0)
- `exclude_nan_results::Bool`: Filter out NaN/Inf values (default: true)

# Usage
```julia
# Analyze command (permissive filtering)
params = CrossMastDirectionTrainParams(target_name="Mast1", source_name="Mast2")

# Recommend command (strict filtering)
strict_params = CrossMastDirectionTrainParams(
    target_name="Mast1", 
    source_name="Mast2",
    max_std_deviation=45.0,
    max_abs_offset=45.0
)
```
"""
@with_kw struct CrossMastDirectionTrainParams
    # Required names (no defaults)
    target_name::String
    source_name::String
    
    # Data quality filters (with defaults)
    min_data_points::Int = 100
    max_std_deviation::Float64 = Inf         # recommend: 45.0
    max_abs_offset::Float64 = Inf            # recommend: 45.0
    exclude_nan_results::Bool = true
end

# from_dict implementations
function from_dict(::Type{CrossMastSpeedTrainParams}, dict::Dict{String, Any})::CrossMastSpeedTrainParams
    target_name = dict["target_name"]
    source_name = dict["source_name"]
    min_data_points = get(dict, "min_data_points", 100)
    min_correlation = get(dict, "min_correlation", 0.0)
    exclude_nan_results = get(dict, "exclude_nan_results", true)
    
    return CrossMastSpeedTrainParams(
        target_name, source_name, min_data_points, min_correlation, 
        exclude_nan_results
    )
end

function from_dict(::Type{CrossMastDirectionTrainParams}, dict::Dict{String, Any})::CrossMastDirectionTrainParams
    target_name = dict["target_name"]
    source_name = dict["source_name"]
    min_data_points = get(dict, "min_data_points", 100)
    max_std_deviation = get(dict, "max_std_deviation", Inf)
    max_abs_offset = get(dict, "max_abs_offset", Inf)
    exclude_nan_results = get(dict, "exclude_nan_results", true)
    
    return CrossMastDirectionTrainParams(
        target_name, source_name, min_data_points, max_std_deviation, 
        max_abs_offset, exclude_nan_results
    )
end

# to_dict implementations
function to_dict(params::CrossMastSpeedTrainParams)::Dict{String, Any}
    return Dict{String, Any}(
        "target_name" => params.target_name,
        "source_name" => params.source_name,
        "min_data_points" => params.min_data_points,
        "min_correlation" => params.min_correlation,
        "exclude_nan_results" => params.exclude_nan_results
    )
end

function to_dict(params::CrossMastDirectionTrainParams)::Dict{String, Any}
    return Dict{String, Any}(
        "target_name" => params.target_name,
        "source_name" => params.source_name,
        "min_data_points" => params.min_data_points,
        "max_std_deviation" => params.max_std_deviation,
        "max_abs_offset" => params.max_abs_offset,
        "exclude_nan_results" => params.exclude_nan_results
    )
end

end # module 