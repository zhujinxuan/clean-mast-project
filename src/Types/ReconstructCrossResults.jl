"""
    ReconstructCrossResults.jl

Result types for cross-mast reconstruction operations.
These types store the results and quality metrics from reconstruction jobs.
"""
module ReconstructCrossResults

using Parameters
using Dates
using ..SensorColumns: SensorColumn
using ..ReconstructCrossConfig: ReconstructionJob
import ..Utils: from_dict, to_dict

export ReconstructionJobResult, ReconstructionSummary, QualityMetrics

"""
    QualityMetrics

Quality assessment metrics for a single sensor reconstruction.

# Fields
- `sensor::SensorColumn`: The sensor that was reconstructed
- `filled_points::Int`: Number of missing values filled
- `total_missing::Int`: Total missing values before reconstruction
- `fill_percentage::Float64`: Percentage of missing data filled
- `model_correlation::Float64`: Correlation used for this reconstruction
- `model_rmse::Union{Float64, Nothing}`: RMSE for speed models (nothing for direction)
- `reconstruction_start::DateTime`: First reconstructed timestamp
- `reconstruction_end::DateTime`: Last reconstructed timestamp
"""
@with_kw struct QualityMetrics
    sensor::SensorColumn
    filled_points::Int
    total_missing::Int
    fill_percentage::Float64
    model_correlation::Float64
    model_rmse::Union{Float64, Nothing}
    reconstruction_start::DateTime
    reconstruction_end::DateTime
end

"""
    ReconstructionJobResult

Results from executing a single reconstruction job.

# Fields
- `job::ReconstructionJob`: Original job specification
- `execution_start::DateTime`: When reconstruction started
- `execution_end::DateTime`: When reconstruction completed
- `success::Bool`: Whether reconstruction completed successfully
- `error_message::Union{String, Nothing}`: Error details if failed
- `windspeed_metrics::Vector{QualityMetrics}`: Quality metrics for each reconstructed speed sensor
- `winddirection_metrics::Vector{QualityMetrics}`: Quality metrics for each reconstructed direction sensor
- `output_file::Union{String, Nothing}`: Path to reconstructed time series file
- `quality_report::Union{String, Nothing}`: Path to quality assessment report
"""
@with_kw struct ReconstructionJobResult
    job::ReconstructionJob
    execution_start::DateTime
    execution_end::DateTime
    success::Bool
    error_message::Union{String, Nothing} = nothing
    windspeed_metrics::Vector{QualityMetrics}
    winddirection_metrics::Vector{QualityMetrics}
    output_file::Union{String, Nothing} = nothing
    quality_report::Union{String, Nothing} = nothing
end

"""
    ReconstructionSummary

Overall summary of entire reconstruction campaign.

# Fields
- `campaign_start::DateTime`: When reconstruction campaign started
- `campaign_end::DateTime`: When reconstruction campaign completed
- `total_jobs::Int`: Total number of reconstruction jobs
- `successful_jobs::Int`: Number of jobs that completed successfully
- `failed_jobs::Int`: Number of jobs that failed
- `total_filled_points::Int`: Total missing values filled across all masts
- `total_missing_points::Int`: Total missing values across all masts
- `overall_fill_percentage::Float64`: Overall percentage of missing data filled
- `average_correlation::Float64`: Average correlation of applied models
- `best_correlation::Float64`: Best correlation achieved
- `worst_correlation::Float64`: Worst correlation applied
- `job_results::Vector{ReconstructionJobResult}`: Results from all jobs
- `summary_report::Union{String, Nothing}`: Path to campaign summary report
"""
@with_kw struct ReconstructionSummary
    campaign_start::DateTime
    campaign_end::DateTime
    total_jobs::Int
    successful_jobs::Int
    failed_jobs::Int
    total_filled_points::Int
    total_missing_points::Int
    overall_fill_percentage::Float64
    average_correlation::Float64
    best_correlation::Float64
    worst_correlation::Float64
    job_results::Vector{ReconstructionJobResult}
    summary_report::Union{String, Nothing} = nothing
end

# Serialization methods following project patterns

function to_dict(metrics::QualityMetrics)::Dict{String, Any}
    return Dict{String, Any}(
        "sensor" => to_dict(metrics.sensor),
        "filled_points" => metrics.filled_points,
        "total_missing" => metrics.total_missing,
        "fill_percentage" => metrics.fill_percentage,
        "model_correlation" => metrics.model_correlation,
        "model_rmse" => metrics.model_rmse,
        "reconstruction_start" => string(metrics.reconstruction_start),
        "reconstruction_end" => string(metrics.reconstruction_end)
    )
end

function from_dict(::Type{QualityMetrics}, dict::Dict{String, Any})::QualityMetrics
    return QualityMetrics(
        sensor = from_dict(SensorColumn, dict["sensor"]),
        filled_points = dict["filled_points"],
        total_missing = dict["total_missing"],
        fill_percentage = dict["fill_percentage"],
        model_correlation = dict["model_correlation"],
        model_rmse = dict["model_rmse"],
        reconstruction_start = DateTime(dict["reconstruction_start"]),
        reconstruction_end = DateTime(dict["reconstruction_end"])
    )
end

function to_dict(result::ReconstructionJobResult)::Dict{String, Any}
    return Dict{String, Any}(
        "job" => to_dict(result.job),
        "execution_start" => string(result.execution_start),
        "execution_end" => string(result.execution_end),
        "success" => result.success,
        "error_message" => result.error_message,
        "windspeed_metrics" => [to_dict(m) for m in result.windspeed_metrics],
        "winddirection_metrics" => [to_dict(m) for m in result.winddirection_metrics],
        "output_file" => result.output_file,
        "quality_report" => result.quality_report
    )
end

function from_dict(::Type{ReconstructionJobResult}, dict::Dict{String, Any})::ReconstructionJobResult
    return ReconstructionJobResult(
        job = from_dict(ReconstructionJob, dict["job"]),
        execution_start = DateTime(dict["execution_start"]),
        execution_end = DateTime(dict["execution_end"]),
        success = dict["success"],
        error_message = dict["error_message"],
        windspeed_metrics = [from_dict(QualityMetrics, m) for m in dict["windspeed_metrics"]],
        winddirection_metrics = [from_dict(QualityMetrics, m) for m in dict["winddirection_metrics"]],
        output_file = dict["output_file"],
        quality_report = dict["quality_report"]
    )
end

function to_dict(summary::ReconstructionSummary)::Dict{String, Any}
    return Dict{String, Any}(
        "campaign_start" => string(summary.campaign_start),
        "campaign_end" => string(summary.campaign_end),
        "total_jobs" => summary.total_jobs,
        "successful_jobs" => summary.successful_jobs,
        "failed_jobs" => summary.failed_jobs,
        "total_filled_points" => summary.total_filled_points,
        "total_missing_points" => summary.total_missing_points,
        "overall_fill_percentage" => summary.overall_fill_percentage,
        "average_correlation" => summary.average_correlation,
        "best_correlation" => summary.best_correlation,
        "worst_correlation" => summary.worst_correlation,
        "job_results" => [to_dict(r) for r in summary.job_results],
        "summary_report" => summary.summary_report
    )
end

function from_dict(::Type{ReconstructionSummary}, dict::Dict{String, Any})::ReconstructionSummary
    return ReconstructionSummary(
        campaign_start = DateTime(dict["campaign_start"]),
        campaign_end = DateTime(dict["campaign_end"]),
        total_jobs = dict["total_jobs"],
        successful_jobs = dict["successful_jobs"],
        failed_jobs = dict["failed_jobs"],
        total_filled_points = dict["total_filled_points"],
        total_missing_points = dict["total_missing_points"],
        overall_fill_percentage = dict["overall_fill_percentage"],
        average_correlation = dict["average_correlation"],
        best_correlation = dict["best_correlation"],
        worst_correlation = dict["worst_correlation"],
        job_results = [from_dict(ReconstructionJobResult, r) for r in dict["job_results"]],
        summary_report = dict["summary_report"]
    )
end

end # module
