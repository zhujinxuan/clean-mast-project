"""
    TrainReconstructCrossConfiguration.jl

Configuration types for the train-reconstruct-cross command.
This command analyzes all mast-to-mast relationships and trains cross-mast reconstruction models.
"""
module TrainReconstructCrossConfig

using ..MastTimeSeries: TimeSeriesSource
import ..Utils: from_dict, to_dict
using Parameters

export TrainReconstructCrossConfiguration, TrainCrossMast, TrainCrossSettings

"""
    TrainCrossMast

Configuration for a single mast in cross-mast training.

# Fields
- `name::String`: Unique name for the mast
- `input::TimeSeriesSource`: Input data source (data file and sensors configuration)
"""
@with_kw struct TrainCrossMast
    name::String
    input::TimeSeriesSource
end

"""
    TrainCrossSettings

Settings for cross-mast training output and model training parameters.

# Fields
- `output_dir::String`: Directory where training results will be saved
- `min_overlap_days::Float64`: Minimum overlap days for model training (default: 90.0)
- `min_data_points::Int`: Minimum concurrent data points for training (default: 100)
- `exclude_nan_results::Bool`: Filter out NaN/Inf results (default: true)
"""
@with_kw struct TrainCrossSettings
    output_dir::String
    # Training parameters
    min_overlap_days::Float64 = 90.0        # Minimum overlap days for model training
    min_data_points::Int = 100
    exclude_nan_results::Bool = true
end

"""
    TrainReconstructCrossConfiguration

Main configuration struct for train-reconstruct-cross command.

# Fields
- `masts::Vector{TrainCrossMast}`: List of masts to train
- `train::TrainCrossSettings`: Training output settings
"""
@with_kw struct TrainReconstructCrossConfiguration
    masts::Vector{TrainCrossMast}
    train::TrainCrossSettings
end

# from_dict implementations
function from_dict(::Type{TrainCrossMast}, dict::Dict{String, Any})::TrainCrossMast
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    return TrainCrossMast(name, input)
end

function from_dict(::Type{TrainCrossSettings}, dict::Dict{String, Any})::TrainCrossSettings
    output_dir = dict["output_dir"]
    min_overlap_days = get(dict, "min_overlap_days", 90.0)
    min_data_points = get(dict, "min_data_points", 100)
    exclude_nan_results = get(dict, "exclude_nan_results", true)

    return TrainCrossSettings(
        output_dir, min_overlap_days, min_data_points, exclude_nan_results
    )
end

function from_dict(::Type{TrainReconstructCrossConfiguration}, dict::Dict{String, Any})::TrainReconstructCrossConfiguration
    masts = [from_dict(TrainCrossMast, Dict{String, Any}(m)) for m in dict["masts"]]
    train = from_dict(TrainCrossSettings, Dict{String, Any}(dict["train"]))
    return TrainReconstructCrossConfiguration(masts, train)
end

# to_dict implementations
function to_dict(mast::TrainCrossMast)::Dict{String, Any}
    return Dict{String, Any}(
        "name" => mast.name,
        "input" => to_dict(mast.input)
    )
end

function to_dict(settings::TrainCrossSettings)::Dict{String, Any}
    return Dict{String, Any}(
        "output_dir" => settings.output_dir,
        "min_overlap_days" => settings.min_overlap_days,
        "min_data_points" => settings.min_data_points,
        "exclude_nan_results" => settings.exclude_nan_results
    )
end

function to_dict(config::TrainReconstructCrossConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "masts" => [to_dict(m) for m in config.masts],
        "train" => to_dict(config.train)
    )
end

end # module 