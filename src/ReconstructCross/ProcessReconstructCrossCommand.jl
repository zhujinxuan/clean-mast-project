"""
    ProcessReconstructCrossCommand.jl

Execute cross-mast reconstruction using trained models.
This command loads models, applies reconstruction, and generates quality metrics.
"""
module ProcessReconstructCrossCommand

using TOML
using JLD2
using Dates
using DataFrames
using Statistics
using Base.Threads: @threads
using Logging

# Import configuration and result types
using ...Types.ReconstructCrossConfig: ReconstructCrossConfiguration, ReconstructionJob, from_dict
using ...Types.ReconstructCrossResults: ReconstructionSummary, ReconstructionJobResult, QualityMetrics, to_dict
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, save_timeseries
using ...Types.CrossMastSpeedModels: CrossMastSpeedModel
using ...Types.CrossMastDirectionModels: CrossMastDirectionModel
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: strip_nothing_values
using ...CleanMastUtils: load_dict

# Import logging infrastructure
using ...CleanMastLogging: create_cleanmast_logger
using ...CleanMastLogging.CleanMastLogger.LogRotation: archive_all_worker_logs

# Import reconstruction functions
using ...TrainReconstructCross.CrossMastSpeedCorrelation: reconstruct
using ...TrainReconstructCross.CrossMastDirectionAnalysis: reconstruct

export execute

"""
    execute(config_path::String)::ReconstructionSummary

Execute cross-mast reconstruction using trained models.

# Arguments
- `config_path::String`: Path to reconstruct-cross.toml configuration file

# Workflow
1. Load configuration and validate inputs
2. Load original time series data for all masts
3. Execute reconstruction jobs in priority order
4. Apply trained models to fill missing data points only
5. Save reconstructed time series files
6. Generate quality assessment reports
7. Create campaign summary

# Returns
- ReconstructionSummary with complete results
"""
function execute(config_path::String)::ReconstructionSummary
    # Setup logging
    config_dir = dirname(config_path)
    config_basename = splitext(basename(config_path))[1]

    # Create main logger for sequential operations
    main_logger = create_cleanmast_logger(
        job_name="reconstruct-cross",
        worker_id=1,
        config_dir=config_dir,
        config_basename=config_basename
    )
    global_logger(main_logger)

    @info "Starting cross-mast reconstruction" config_file=config_path

    campaign_start = now()

    # 1. Load and validate configuration
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end

    config_dict = load_dict(config_path)
    config = from_dict(ReconstructCrossConfiguration, config_dict)
    project_dir = dirname(config_path)

    @info "Configuration loaded" masts=length(config.masts) priority_levels=length(config.reconstruction_priorities) output_dir=config.settings.output_dir

    # 2. Create output directory
    output_dir = joinpath(project_dir, config.settings.output_dir)
    mkpath(output_dir)

    # 3. Load all mast time series data
    @info "Loading mast time series data"
    mast_data = load_all_mast_data(config, project_dir)
    @info "Loaded mast data" mast_count=length(mast_data)
    
    # 4. Execute reconstruction jobs in priority order using parallel batches
    @info "Executing reconstruction jobs"

    # Archive old worker logs and create worker loggers for parallel execution
    @info "Archiving old worker logs before parallel execution"
    archive_all_worker_logs(config_dir, config_basename, Threads.nthreads())

    @info "Pre-creating loggers for all worker threads" num_threads=Threads.nthreads()
    worker_loggers = Dict{Int, Any}()
    for worker_id in 1:Threads.nthreads()
        worker_loggers[worker_id] = create_cleanmast_logger(
            job_name="reconstruct-cross",
            worker_id=worker_id,
            config_dir=config_dir,
            config_basename=config_basename
        )
    end

    job_results = ReconstructionJobResult[]
    reconstructed_masts = Set{String}()

    total_jobs = sum(length(level.jobs) for level in config.reconstruction_priorities)
    completed_jobs = 0

    for priority_level in config.reconstruction_priorities
        @info "Processing priority level" level=priority_level.priority_level jobs=length(priority_level.jobs)

        # Group jobs into batches with unique target masts for parallel execution
        job_batches = create_job_batches(priority_level.jobs)
        @info "Created batches for parallel execution" num_batches=length(job_batches)

        for (batch_idx, batch) in enumerate(job_batches)
            @info "Processing batch" batch=batch_idx total_batches=length(job_batches) batch_size=length(batch)

            # Execute batch in parallel using @threads
            batch_results = Vector{ReconstructionJobResult}(undef, length(batch))
            @threads for i in eachindex(batch)
                worker_id = Threads.threadid()
                worker_logger = worker_loggers[worker_id]

                with_logger(worker_logger) do
                    job = batch[i]
                    @info "Job started" job_index="$(completed_jobs + i)/$(total_jobs)" target=job.target_mast source=job.source_mast

                    result = execute_reconstruction_job(job, mast_data, config, project_dir)
                    batch_results[i] = result

                    if result.success
                        @info "Job completed successfully" target=job.target_mast source=job.source_mast variables=join(job.variables, ", ")
                    else
                        @error "Job failed" target=job.target_mast source=job.source_mast error=result.error_message
                    end
                end
            end

            # Collect results from batch and update mast_data for cumulative reconstruction
            append!(job_results, batch_results)

            for (i, job) in enumerate(batch)
                push!(reconstructed_masts, job.target_mast)

                result = batch_results[i]
                if result.success
                    # Reload the saved file to get cumulative reconstruction for next batch
                    target_mast_config = findfirst(m -> m.name == job.target_mast, config.masts)
                    if target_mast_config !== nothing
                        output_source = config.masts[target_mast_config].output
                        try
                            updated_ts = load_timeseries(output_source, project_dir)
                            mast_data[job.target_mast] = updated_ts
                            @debug "Updated mast_data for cumulative reconstruction" target=job.target_mast
                        catch e
                            @warn "Failed to reload reconstructed data, using previous version" target=job.target_mast error=e
                        end
                    end
                end
            end

            completed_jobs += length(batch)
        end
    end

    # 4.5. Ensure all masts have output files (copy input to output for masts without reconstruction)
    @info "Ensuring all masts have output files"
    copy_unreconstructed_masts(config, mast_data, reconstructed_masts, project_dir)
    
    # 5. Generate campaign summary
    campaign_end = now()
    summary = create_reconstruction_summary(job_results, campaign_start, campaign_end, config, output_dir)

    # 6. Save summary results
    save_reconstruction_summary(summary, output_dir)

    # 7. Log completion summary
    @info "Reconstruction campaign completed" duration=(campaign_end - campaign_start) total_jobs=summary.total_jobs successful_jobs=summary.successful_jobs failed_jobs=summary.failed_jobs fill_percentage=round(summary.overall_fill_percentage, digits=1) average_correlation=round(summary.average_correlation, digits=3)

    for result in summary.job_results
        if result.success
            total_metrics = length(result.windspeed_metrics) + length(result.winddirection_metrics)
            total_filled = sum(m.filled_points for m in vcat(result.windspeed_metrics, result.winddirection_metrics))
            @info "Reconstruction summary" target=result.job.target_mast source=result.job.source_mast points_filled=total_filled sensors=total_metrics
        end
    end

    @info "Cross-mast reconstruction completed successfully"
    return summary
end

"""
    create_job_batches(jobs::Vector{ReconstructionJob})::Vector{Vector{ReconstructionJob}}

Reorganize reconstruction jobs into batches where each batch contains jobs with unique target masts.
This enables parallel execution within each batch while preventing file conflicts.

# Algorithm
- Iteratively select jobs with unique target masts for each batch
- Continue until all jobs are assigned to batches
- Jobs for the same target mast are distributed across different batches

# Returns
Vector of job batches, where each batch has unique target masts and can be executed in parallel.

# Example
Input: [M04←M05, M04←M02, M02←M04, M02←M01]
Output: [[M04←M05, M02←M04], [M04←M02, M02←M01]]
"""
function create_job_batches(jobs::Vector{ReconstructionJob})::Vector{Vector{ReconstructionJob}}
    batches = Vector{Vector{ReconstructionJob}}()
    remaining_jobs = copy(jobs)

    while !isempty(remaining_jobs)
        batch = Vector{ReconstructionJob}()
        used_targets = Set{String}()

        jobs_to_remove = Int[]
        for (i, job) in enumerate(remaining_jobs)
            if !(job.target_mast in used_targets)
                push!(batch, job)
                push!(used_targets, job.target_mast)
                push!(jobs_to_remove, i)
            end
        end

        deleteat!(remaining_jobs, jobs_to_remove)
        push!(batches, batch)
    end

    return batches
end

"""
    load_all_mast_data(config::ReconstructCrossConfiguration, project_dir::String)::Dict{String, TimeSeriesData}

Load time series data for all masts in the configuration.
"""
function load_all_mast_data(config::ReconstructCrossConfiguration, project_dir::String)::Dict{String, TimeSeriesData}
    mast_data = Dict{String, TimeSeriesData}()

    for mast in config.masts
        ts_data = load_timeseries(mast.input, project_dir)
        mast_data[mast.name] = ts_data
        @info "Loaded mast data" mast=mast.name records=nrow(ts_data.df) sensors=length(ts_data.sensors)
    end

    return mast_data
end

"""
    execute_reconstruction_job(job::ReconstructionJob, mast_data::Dict{String, TimeSeriesData}, 
                              config::ReconstructCrossConfiguration, project_dir::String)::ReconstructionJobResult

Execute a single reconstruction job using trained models.
"""
function execute_reconstruction_job(job::ReconstructionJob, mast_data::Dict{String, TimeSeriesData},
                                   config::ReconstructCrossConfiguration, project_dir::String)::ReconstructionJobResult
    execution_start = now()

    # Get target and source time series
    if !haskey(mast_data, job.target_mast)
        error("Target mast data not found: $(job.target_mast)")
    end
    if !haskey(mast_data, job.source_mast)
        error("Source mast data not found: $(job.source_mast)")
    end

    target_ts = mast_data[job.target_mast]
    source_ts = mast_data[job.source_mast]

    # Initialize metrics vectors
    windspeed_metrics = QualityMetrics[]
    winddirection_metrics = QualityMetrics[]

    # Start with target time series (TimeSeriesData is immutable)
    reconstructed_ts = target_ts

    # Apply speed reconstruction if requested
    if "windspeed" in job.variables
        speed_model_path = joinpath(project_dir, job.model_dir, "windspeed.jld2")
        if isfile(speed_model_path)
            reconstructed_ts, speed_metrics = apply_speed_reconstruction(
                reconstructed_ts, source_ts, speed_model_path
            )
            append!(windspeed_metrics, speed_metrics)
        else
            @warn "Speed model file not found: $speed_model_path"
        end
    end

    # Apply direction reconstruction if requested
    if "winddirection" in job.variables
        direction_model_path = joinpath(project_dir, job.model_dir, "winddirection.jld2")
        if isfile(direction_model_path)
            reconstructed_ts, direction_metrics = apply_direction_reconstruction(
                reconstructed_ts, source_ts, direction_model_path
            )
            append!(winddirection_metrics, direction_metrics)
        else
            @warn "Direction model file not found: $direction_model_path"
        end
    end

    # Save reconstructed time series
    output_file = save_reconstructed_timeseries(reconstructed_ts, job, config, project_dir)

    execution_end = now()

    return ReconstructionJobResult(
        job = job,
        execution_start = execution_start,
        execution_end = execution_end,
        success = true,
        error_message = nothing,
        windspeed_metrics = windspeed_metrics,
        winddirection_metrics = winddirection_metrics,
        output_file = output_file,
        quality_report = nothing  # TODO: Implement quality reports in future
    )
end

"""
    apply_speed_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                              speed_model_path::String)::Tuple{TimeSeriesData, Vector{QualityMetrics}}

Apply wind speed reconstruction using trained CrossMastSpeedModel.
"""
function apply_speed_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                   speed_model_path::String)::Tuple{TimeSeriesData, Vector{QualityMetrics}}
    # Load trained model
    model_data = JLD2.load(speed_model_path)
    speed_model = model_data["model"]::CrossMastSpeedModel

    # Apply reconstruction using existing function
    reconstructed_speed_ts = reconstruct(speed_model, source_ts)

    # Merge reconstructed data with target data (only fills missing values, preserves existing data)
    merged_ts = merge_reconstruction_data(target_ts, reconstructed_speed_ts)

    # Calculate quality metrics
    metrics = calculate_speed_quality_metrics(target_ts, merged_ts, speed_model)

    return merged_ts, metrics
end

"""
    apply_direction_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                  direction_model_path::String)::Tuple{TimeSeriesData, Vector{QualityMetrics}}

Apply wind direction reconstruction using trained CrossMastDirectionModel.
"""
function apply_direction_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                       direction_model_path::String)::Tuple{TimeSeriesData, Vector{QualityMetrics}}
    # Load trained model
    model_data = JLD2.load(direction_model_path)
    direction_model = model_data["model"]::CrossMastDirectionModel

    # Apply reconstruction using existing function
    reconstructed_direction_ts = reconstruct(direction_model, source_ts)

    # Merge reconstructed data with target data (only fills missing values, preserves existing data)
    merged_ts = merge_reconstruction_data(target_ts, reconstructed_direction_ts)

    # Calculate quality metrics
    metrics = calculate_direction_quality_metrics(target_ts, merged_ts, direction_model)

    return merged_ts, metrics
end

"""
    append_new_timestamps(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData)::DataFrame

Extend target DataFrame with new timestamps from reconstructed data.
Appends rows for timestamps that exist in reconstructed but not in target, with all sensor values as missing.
Returns sorted DataFrame by timestamp.
"""
function append_new_timestamps(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData)::DataFrame
    # Start with target data
    result_df = copy(target_ts.df)

    # Find timestamps in reconstructed that don't exist in target
    existing_timestamps = Set(target_ts.df.timestamp)
    reconstructed_timestamps = reconstructed_ts.df.timestamp
    new_timestamps = filter(t -> !(t in existing_timestamps), reconstructed_timestamps)

    if isempty(new_timestamps)
        return result_df  # No new timestamps to add
    end

    # Create rows for new timestamps with ALL columns from target (including non-sensor columns like Battery_V)
    new_rows = DataFrame(:timestamp => new_timestamps)

    # Add ALL columns from target_df to match schema
    for col_name in propertynames(result_df)
        if col_name == :timestamp
            continue  # Already added
        end

        # Get column type from target_df to preserve type consistency
        col_type = eltype(result_df[!, col_name])
        new_rows[!, col_name] = missings(col_type, length(new_timestamps))
    end

    # Append new rows and sort by timestamp
    result_df = vcat(result_df, new_rows)
    sort!(result_df, :timestamp)

    return result_df
end

"""
    merge_reconstruction_data(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData)::TimeSeriesData

Merge reconstructed data with original target data.
Only fills missing values in target data, preserving all existing data.
Extends time range to include all timestamps from reconstruction.
"""
function merge_reconstruction_data(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData)::TimeSeriesData
    # Append new timestamps from reconstruction, then sort
    result_df = append_new_timestamps(target_ts, reconstructed_ts)

    # Build index from reconstructed timestamps to row index for alignment
    rc_index = Dict{DateTime, Int}()
    for (i, t) in enumerate(reconstructed_ts.df.timestamp)
        rc_index[t] = i
    end

    # Merge each reconstructed sensor
    for sensor in reconstructed_ts.sensors
        col_name = sensor.columnName

        # Validate sensor exists in target; otherwise, this indicates a mismatch between model and target data
        if !hasproperty(result_df, col_name)
            error("merge_reconstruction_data: Target data is missing expected sensor column '$(col_name)'. Ensure the model's target sensors exist in the target mast data.")
        end

        # Fill only missing values where reconstructed has data at the same timestamp
        for i in 1:nrow(result_df)
            ismissing(result_df[i, col_name]) || continue
            t = result_df.timestamp[i]
            haskey(rc_index, t) || continue
            v = reconstructed_ts.df[rc_index[t], col_name]
            ismissing(v) && continue
            result_df[i, col_name] = v
        end
    end

    return TimeSeriesData(result_df, target_ts.sensors)
end

"""
    calculate_speed_quality_metrics(original_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData,
                                   model::CrossMastSpeedModel)::Vector{QualityMetrics}

Calculate quality metrics for speed reconstruction.
"""
function calculate_speed_quality_metrics(original_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData,
                                        model::CrossMastSpeedModel)::Vector{QualityMetrics}
    metrics = QualityMetrics[]

    # Extend original_ts to match reconstructed_ts time range
    # This ensures both DataFrames have the same timestamps for quality comparison
    extended_original_df = append_new_timestamps(original_ts, reconstructed_ts)

    for pair in model.pairs
        sensor = pair.target_sensor
        col_name = sensor.columnName

        # Skip if sensor not in data
        if !hasproperty(extended_original_df, col_name) || !hasproperty(reconstructed_ts.df, col_name)
            continue
        end

        # Use extended original data (same length as reconstructed)
        original_data = extended_original_df[!, col_name]
        reconstructed_data = reconstructed_ts.df[!, col_name]

        # Calculate metrics
        total_missing = count(ismissing, original_data)
        filled_points = count(!ismissing(reconstructed_data[ismissing.(original_data)]))
        fill_percentage = total_missing > 0 ? (filled_points / total_missing) * 100.0 : 0.0

        # Find reconstruction time range
        filled_indices = findall(!ismissing(reconstructed_data) .& ismissing.(original_data))
        reconstruction_start = isempty(filled_indices) ? now() : reconstructed_ts.df.timestamp[first(filled_indices)]
        reconstruction_end = isempty(filled_indices) ? now() : reconstructed_ts.df.timestamp[last(filled_indices)]

        push!(metrics, QualityMetrics(
            sensor = sensor,
            filled_points = filled_points,
            total_missing = total_missing,
            fill_percentage = fill_percentage,
            model_correlation = pair.correlation,
            model_rmse = nothing,  # Could calculate RMSE if needed
            reconstruction_start = reconstruction_start,
            reconstruction_end = reconstruction_end
        ))
    end

    return metrics
end

"""
    calculate_direction_quality_metrics(original_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData,
                                       model::CrossMastDirectionModel)::Vector{QualityMetrics}

Calculate quality metrics for direction reconstruction.
"""
function calculate_direction_quality_metrics(original_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData,
                                            model::CrossMastDirectionModel)::Vector{QualityMetrics}
    metrics = QualityMetrics[]

    # Extend original_ts to match reconstructed_ts time range
    # This ensures both DataFrames have the same timestamps for quality comparison
    extended_original_df = append_new_timestamps(original_ts, reconstructed_ts)

    for pair in model.pairs
        sensor = pair.target_sensor
        col_name = sensor.columnName

        # Skip if sensor not in data
        if !hasproperty(extended_original_df, col_name) || !hasproperty(reconstructed_ts.df, col_name)
            continue
        end

        # Use extended original data (same length as reconstructed)
        original_data = extended_original_df[!, col_name]
        reconstructed_data = reconstructed_ts.df[!, col_name]

        # Calculate metrics
        total_missing = count(ismissing, original_data)
        filled_points = count(!ismissing(reconstructed_data[ismissing.(original_data)]))
        fill_percentage = total_missing > 0 ? (filled_points / total_missing) * 100.0 : 0.0

        # Find reconstruction time range
        filled_indices = findall(!ismissing(reconstructed_data) .& ismissing.(original_data))
        reconstruction_start = isempty(filled_indices) ? now() : reconstructed_ts.df.timestamp[first(filled_indices)]
        reconstruction_end = isempty(filled_indices) ? now() : reconstructed_ts.df.timestamp[last(filled_indices)]

        # Use inverse of std_deviation as a correlation-like metric (lower std = better quality)
        quality_score = 1.0 / (1.0 + pair.std_deviation / 10.0)  # Normalize to 0-1 range

        push!(metrics, QualityMetrics(
            sensor = sensor,
            filled_points = filled_points,
            total_missing = total_missing,
            fill_percentage = fill_percentage,
            model_correlation = quality_score,  # Use quality score for direction
            model_rmse = nothing,
            reconstruction_start = reconstruction_start,
            reconstruction_end = reconstruction_end
        ))
    end

    return metrics
end

"""
    save_reconstructed_timeseries(reconstructed_ts::TimeSeriesData, job::ReconstructionJob,
                                 config::ReconstructCrossConfiguration, project_dir::String)::String

Save reconstructed time series to output file.
"""
function save_reconstructed_timeseries(reconstructed_ts::TimeSeriesData, job::ReconstructionJob,
                                      config::ReconstructCrossConfiguration, project_dir::String)::String
    # Find the mast configuration for output path
    target_mast_config = findfirst(m -> m.name == job.target_mast, config.masts)

    if target_mast_config === nothing
        error("Target mast $(job.target_mast) not found in configuration masts")
    end
    output_source = config.masts[target_mast_config].output

    # Save reconstructed data
    save_timeseries(output_source, project_dir, reconstructed_ts)

    return joinpath(project_dir, output_source.data)
end

"""
    create_reconstruction_summary(job_results::Vector{ReconstructionJobResult},
                                 campaign_start::DateTime, campaign_end::DateTime,
                                 config::ReconstructCrossConfiguration, output_dir::String)::ReconstructionSummary

Create overall summary of reconstruction campaign.
"""
function create_reconstruction_summary(job_results::Vector{ReconstructionJobResult},
                                      campaign_start::DateTime, campaign_end::DateTime,
                                      config::ReconstructCrossConfiguration, output_dir::String)::ReconstructionSummary
    successful_jobs = count(r -> r.success, job_results)
    failed_jobs = length(job_results) - successful_jobs

    # Calculate aggregate statistics
    all_metrics = vcat([vcat(r.windspeed_metrics, r.winddirection_metrics) for r in job_results]...)

    total_filled_points = isempty(all_metrics) ? 0 : sum(m.filled_points for m in all_metrics)
    total_missing_points = isempty(all_metrics) ? 0 : sum(m.total_missing for m in all_metrics)
    overall_fill_percentage = total_missing_points > 0 ? (total_filled_points / total_missing_points) * 100.0 : 0.0

    # Calculate correlation statistics
    correlations = [m.model_correlation for m in all_metrics if !isnothing(m.model_correlation)]
    average_correlation = isempty(correlations) ? 0.0 : mean(correlations)
    best_correlation = isempty(correlations) ? 0.0 : maximum(correlations)
    worst_correlation = isempty(correlations) ? 0.0 : minimum(correlations)

    return ReconstructionSummary(
        campaign_start = campaign_start,
        campaign_end = campaign_end,
        total_jobs = length(job_results),
        successful_jobs = successful_jobs,
        failed_jobs = failed_jobs,
        total_filled_points = total_filled_points,
        total_missing_points = total_missing_points,
        overall_fill_percentage = overall_fill_percentage,
        average_correlation = average_correlation,
        best_correlation = best_correlation,
        worst_correlation = worst_correlation,
        job_results = job_results,
        summary_report = nothing
    )
end

"""
    save_reconstruction_summary(summary::ReconstructionSummary, output_dir::String)

Save reconstruction summary to TOML file.
"""
function save_reconstruction_summary(summary::ReconstructionSummary, output_dir::String)
    summary_path = joinpath(output_dir, "reconstruction-summary.toml")
    summary_dict = to_dict(summary)

    open(summary_path, "w") do io
        println(io, "# Cross-Mast Reconstruction Summary")
        println(io, "# Generated on: $(now())")
        println(io)
        TOML.print(io, strip_nothing_values(summary_dict))
    end

    @info "Saved reconstruction summary" path=summary_path
end

"""
    copy_unreconstructed_masts(config::ReconstructCrossConfiguration, mast_data::Dict{String, TimeSeriesData},
                              reconstructed_masts::Set{String}, project_dir::String)

Ensure all masts have output files by copying input to output for masts without reconstruction.
This is necessary for downstream steps that expect to read from the reconstruct-cross directory.
"""
function copy_unreconstructed_masts(config::ReconstructCrossConfiguration, mast_data::Dict{String, TimeSeriesData},
                                   reconstructed_masts::Set{String}, project_dir::String)
    for mast_config in config.masts
        if !(mast_config.name in reconstructed_masts)
            @info "No reconstruction applied, copying input to output" mast=mast_config.name

            if haskey(mast_data, mast_config.name)
                ts_data = mast_data[mast_config.name]
                save_timeseries(mast_config.output, project_dir, ts_data)
                @info "Saved unreconstructed mast" mast=mast_config.name path=mast_config.output.data
            else
                @warn "Mast data not found" mast=mast_config.name
            end
        end
    end
end

end # module
