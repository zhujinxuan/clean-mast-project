"""
    ReconstructCrossConfig.jl

Configuration types for the reconstruct-cross commands.
These types define the structure for cross-mast reconstruction jobs and settings.
"""
module ReconstructCrossConfig

using Parameters
using Dates
using ..MastTimeSeries: TimeSeriesSource
import ..Utils: from_dict, to_dict

export ReconstructCrossConfiguration, ReconstructCrossSettings, ReconstructionJob, ReconstructionPriority, ReconstructCrossMast

"""
    ReconstructionJob

Single reconstruction operation: target mast ← source mast using trained model.

# Fields
- `target_mast::String`: Name of the mast to be reconstructed
- `source_mast::String`: Name of the mast providing reference data
- `model_dir::String`: Path to model files directory (contains windspeed.jld2, winddirection.jld2)
- `priority::Int`: Reconstruction priority (1 = highest priority, 2 = secondary, etc.)
- `speed_correlation::Float64`: Best high-elevation correlation for this pair
- `direction_std::Float64`: Best high-elevation std deviation for this pair
- `data_coverage_days::Float64`: Days of overlapping data available during training
- `variables::Vector{String}`: Variables to reconstruct (["windspeed", "winddirection"] or subset)
"""
@with_kw struct ReconstructionJob
    target_mast::String
    source_mast::String
    model_dir::String
    priority::Int
    speed_correlation::Float64
    direction_std::Float64
    data_coverage_days::Float64
    variables::Vector{String}
end

"""
    ReconstructionPriority

Priority grouping for reconstruction order. Masts with better correlations reconstruct first.

# Fields
- `priority_level::Int`: Priority level (1 = best correlations, 2 = good, 3 = acceptable)
- `min_correlation::Float64`: Minimum correlation for this priority level
- `max_direction_std::Float64`: Maximum direction std for this priority level
- `jobs::Vector{ReconstructionJob}`: All jobs at this priority level
"""
@with_kw struct ReconstructionPriority
    priority_level::Int
    min_correlation::Float64
    max_direction_std::Float64
    jobs::Vector{ReconstructionJob}
end

"""
    ReconstructCrossSettings

Configuration settings for reconstruction execution.

# Fields
- `output_dir::String`: Directory for reconstruction outputs
- `preserve_existing::Bool`: Only fill missing data, don't override existing values
- `min_confidence::Float64`: Minimum correlation to attempt reconstruction
- `max_direction_uncertainty::Float64`: Maximum direction std deviation (degrees)
- `generate_reports::Bool`: Generate reconstruction quality reports
- `backup_originals::Bool`: Create backup of original files before reconstruction
"""
@with_kw struct ReconstructCrossSettings
    output_dir::String = "./reconstruct-cross"
    preserve_existing::Bool = true
    min_confidence::Float64 = 0.7
    max_direction_uncertainty::Float64 = 12.5
    generate_reports::Bool = true
    backup_originals::Bool = true
end

"""
    ReconstructCrossMast

Input specification for a mast that may be reconstructed.

# Fields
- `name::String`: Unique name for the mast
- `input::TimeSeriesSource`: Original data source (data file and sensors configuration)
- `output::Union{TimeSeriesSource, Nothing}`: Where to save reconstructed data (optional)
"""
@with_kw struct ReconstructCrossMast
    name::String
    input::TimeSeriesSource
    output::Union{TimeSeriesSource, Nothing} = nothing
end

"""
    ReconstructCrossConfiguration

Complete configuration for cross-mast reconstruction command.

# Fields
- `masts::Vector{ReconstructCrossMast}`: Input data sources for each mast
- `reconstruction_priorities::Vector{ReconstructionPriority}`: Reconstruction job queue (ordered by priority)
- `settings::ReconstructCrossSettings`: Execution settings
- `training_metadata::Dict{String, Any}`: Metadata from training results
"""
@with_kw struct ReconstructCrossConfiguration
    masts::Vector{ReconstructCrossMast}
    reconstruction_priorities::Vector{ReconstructionPriority}
    settings::ReconstructCrossSettings
    training_metadata::Dict{String, Any}
end

# Serialization methods following project patterns

function from_dict(::Type{ReconstructionJob}, dict::Dict{String, Any})::ReconstructionJob
    return ReconstructionJob(
        target_mast = dict["target_mast"],
        source_mast = dict["source_mast"],
        model_dir = dict["model_dir"],
        priority = dict["priority"],
        speed_correlation = dict["speed_correlation"],
        direction_std = dict["direction_std"],
        data_coverage_days = dict["data_coverage_days"],
        variables = dict["variables"]
    )
end

function to_dict(job::ReconstructionJob)::Dict{String, Any}
    return Dict{String, Any}(
        "target_mast" => job.target_mast,
        "source_mast" => job.source_mast,
        "model_dir" => job.model_dir,
        "priority" => job.priority,
        "speed_correlation" => job.speed_correlation,
        "direction_std" => job.direction_std,
        "data_coverage_days" => job.data_coverage_days,
        "variables" => job.variables
    )
end

function from_dict(::Type{ReconstructionPriority}, dict::Dict{String, Any})::ReconstructionPriority
    jobs = [from_dict(ReconstructionJob, job_dict) for job_dict in dict["jobs"]]
    return ReconstructionPriority(
        priority_level = dict["priority_level"],
        min_correlation = dict["min_correlation"],
        max_direction_std = dict["max_direction_std"],
        jobs = jobs
    )
end

function to_dict(priority::ReconstructionPriority)::Dict{String, Any}
    return Dict{String, Any}(
        "priority_level" => priority.priority_level,
        "min_correlation" => priority.min_correlation,
        "max_direction_std" => priority.max_direction_std,
        "jobs" => [to_dict(job) for job in priority.jobs]
    )
end

function from_dict(::Type{ReconstructCrossSettings}, dict::Dict{String, Any})::ReconstructCrossSettings
    return ReconstructCrossSettings(
        output_dir = get(dict, "output_dir", "./reconstruct-cross"),
        preserve_existing = get(dict, "preserve_existing", true),
        min_confidence = get(dict, "min_confidence", 0.7),
        max_direction_uncertainty = get(dict, "max_direction_uncertainty", 12.5),
        generate_reports = get(dict, "generate_reports", true),
        backup_originals = get(dict, "backup_originals", true)
    )
end

function to_dict(settings::ReconstructCrossSettings)::Dict{String, Any}
    return Dict{String, Any}(
        "output_dir" => settings.output_dir,
        "preserve_existing" => settings.preserve_existing,
        "min_confidence" => settings.min_confidence,
        "max_direction_uncertainty" => settings.max_direction_uncertainty,
        "generate_reports" => settings.generate_reports,
        "backup_originals" => settings.backup_originals
    )
end

function from_dict(::Type{ReconstructCrossMast}, dict::Dict{String, Any})::ReconstructCrossMast
    input = from_dict(TimeSeriesSource, dict["input"])
    output = haskey(dict, "output") && dict["output"] !== nothing ? 
             from_dict(TimeSeriesSource, dict["output"]) : nothing
    return ReconstructCrossMast(
        name = dict["name"],
        input = input,
        output = output
    )
end

function to_dict(mast::ReconstructCrossMast)::Dict{String, Any}
    result = Dict{String, Any}(
        "name" => mast.name,
        "input" => to_dict(mast.input)
    )
    if mast.output !== nothing
        result["output"] = to_dict(mast.output)
    end
    return result
end

function from_dict(::Type{ReconstructCrossConfiguration}, dict::Dict{String, Any})::ReconstructCrossConfiguration
    masts = [from_dict(ReconstructCrossMast, mast_dict) for mast_dict in dict["masts"]]
    priorities = [from_dict(ReconstructionPriority, priority_dict) for priority_dict in dict["reconstruction_priorities"]]
    settings = from_dict(ReconstructCrossSettings, dict["settings"])
    training_metadata = get(dict, "training_metadata", Dict{String, Any}())
    
    return ReconstructCrossConfiguration(
        masts = masts,
        reconstruction_priorities = priorities,
        settings = settings,
        training_metadata = training_metadata
    )
end

function to_dict(config::ReconstructCrossConfiguration)::Dict{String, Any}
    return Dict{String, Any}(
        "masts" => [to_dict(mast) for mast in config.masts],
        "reconstruction_priorities" => [to_dict(priority) for priority in config.reconstruction_priorities],
        "settings" => to_dict(config.settings),
        "training_metadata" => config.training_metadata
    )
end

end # module
