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

# Import configuration and result types
using ...Types.ReconstructCrossConfig: ReconstructCrossConfiguration, ReconstructionJob, from_dict
using ...Types.ReconstructCrossResults: ReconstructionSummary, ReconstructionJobResult, QualityMetrics, to_dict
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, save_timeseries
using ...Types.CrossMastSpeedModels: CrossMastSpeedModel
using ...Types.CrossMastDirectionModels: CrossMastDirectionModel
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: strip_nothing_values
using ...CleanMastUtils: load_dict

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
    println("🚀 Starting cross-mast reconstruction...")
    
    campaign_start = now()
    
    # 1. Load and validate configuration
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end
    
    config_dict = load_dict(config_path)
    config = from_dict(ReconstructCrossConfiguration, config_dict)
    project_dir = dirname(config_path)
    
    println("📋 Configuration loaded:")
    println("  - Masts: $(length(config.masts))")
    println("  - Priority levels: $(length(config.reconstruction_priorities))")
    println("  - Output: $(config.settings.output_dir)")
    
    # 2. Create output directory
    output_dir = joinpath(project_dir, config.settings.output_dir)
    mkpath(output_dir)
    
    if config.settings.backup_originals
        backup_dir = joinpath(output_dir, "originals")
        mkpath(backup_dir)
    end
    
    # 3. Load all mast time series data
    println("\n📊 Loading mast time series data...")
    mast_data = load_all_mast_data(config, project_dir)
    println("✅ Loaded data for $(length(mast_data)) masts")
    
    # 4. Execute reconstruction jobs in priority order
    println("\n🔧 Executing reconstruction jobs...")
    job_results = ReconstructionJobResult[]
    
    total_jobs = sum(length(level.jobs) for level in config.reconstruction_priorities)
    current_job = 0
    
    for priority_level in config.reconstruction_priorities
        println("\n🎯 Priority Level $(priority_level.priority_level): $(length(priority_level.jobs)) jobs")
        
        for job in priority_level.jobs
            current_job += 1
            println("  🔍 Job $(current_job)/$(total_jobs): $(job.target_mast) ← $(job.source_mast)")
            
            result = execute_reconstruction_job(job, mast_data, config, project_dir)
            push!(job_results, result)
            
            if result.success
                println("    ✅ Success: $(join(job.variables, ", "))")
            else
                println("    ❌ Failed: $(result.error_message)")
            end
        end
    end
    
    # 5. Generate campaign summary
    campaign_end = now()
    summary = create_reconstruction_summary(job_results, campaign_start, campaign_end, config, output_dir)
    
    # 6. Save summary results
    save_reconstruction_summary(summary, output_dir)
    
    # 7. Print completion summary
    print_completion_summary(summary)
    
    println("\n✅ Cross-mast reconstruction completed!")
    return summary
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
        println("  ✅ $(mast.name): $(nrow(ts_data.df)) records, $(length(ts_data.sensors)) sensors")
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
                reconstructed_ts, source_ts, speed_model_path, config.settings.preserve_existing
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
                reconstructed_ts, source_ts, direction_model_path, config.settings.preserve_existing
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
                              speed_model_path::String, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}

Apply wind speed reconstruction using trained CrossMastSpeedModel.
"""
function apply_speed_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                   speed_model_path::String, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}
    # Load trained model
    model_data = JLD2.load(speed_model_path)
    speed_model = model_data["model"]::CrossMastSpeedModel

    # Apply reconstruction using existing function
    reconstructed_speed_ts = reconstruct(speed_model, source_ts)

    # Merge reconstructed data with target data (only fill missing values if preserve_existing)
    merged_ts = merge_reconstruction_data(target_ts, reconstructed_speed_ts, preserve_existing)

    # Calculate quality metrics
    metrics = calculate_speed_quality_metrics(target_ts, merged_ts, speed_model)

    return merged_ts, metrics
end

"""
    apply_direction_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                  direction_model_path::String, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}

Apply wind direction reconstruction using trained CrossMastDirectionModel.
"""
function apply_direction_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                       direction_model_path::String, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}
    # Load trained model
    model_data = JLD2.load(direction_model_path)
    direction_model = model_data["model"]::CrossMastDirectionModel

    # Apply reconstruction using existing function
    reconstructed_direction_ts = reconstruct(direction_model, source_ts)

    # Merge reconstructed data with target data (only fill missing values if preserve_existing)
    merged_ts = merge_reconstruction_data(target_ts, reconstructed_direction_ts, preserve_existing)

    # Calculate quality metrics
    metrics = calculate_direction_quality_metrics(target_ts, merged_ts, direction_model)

    return merged_ts, metrics
end

"""
    merge_reconstruction_data(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData,
                             preserve_existing::Bool)::TimeSeriesData

Merge reconstructed data with original target data.
"""
function merge_reconstruction_data(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData,
                                  preserve_existing::Bool)::TimeSeriesData
    # Start with target data
    result_df = copy(target_ts.df)

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

        # Timestamp-aligned merge
        if preserve_existing
            # Fill only missing values where reconstructed has data at the same timestamp
            for i in 1:nrow(result_df)
                ismissing(result_df[i, col_name]) || continue
                t = result_df.timestamp[i]
                haskey(rc_index, t) || continue
                v = reconstructed_ts.df[rc_index[t], col_name]
                ismissing(v) && continue
                result_df[i, col_name] = v
            end
        else
            # Replace values where reconstructed has data at the same timestamp
            for i in 1:nrow(result_df)
                t = result_df.timestamp[i]
                haskey(rc_index, t) || continue
                v = reconstructed_ts.df[rc_index[t], col_name]
                ismissing(v) && continue
                result_df[i, col_name] = v
            end
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

    for pair in model.pairs
        sensor = pair.target_sensor
        col_name = sensor.columnName

        # Skip if sensor not in data
        if !hasproperty(original_ts.df, col_name) || !hasproperty(reconstructed_ts.df, col_name)
            continue
        end

        original_data = original_ts.df[!, col_name]
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

    for pair in model.pairs
        sensor = pair.target_sensor
        col_name = sensor.columnName

        # Skip if sensor not in data
        if !hasproperty(original_ts.df, col_name) || !hasproperty(reconstructed_ts.df, col_name)
            continue
        end

        original_data = original_ts.df[!, col_name]
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

    if target_mast_config === nothing || config.masts[target_mast_config].output === nothing
        # Generate default output path
        output_source = TimeSeriesSource(
            joinpath(config.settings.output_dir, "$(job.target_mast)_reconstructed.csv"),
            joinpath(config.settings.output_dir, "$(job.target_mast)_reconstructed.sensors.yaml")
        )
    else
        output_source = config.masts[target_mast_config].output
    end

    # Create backup if requested
    if config.settings.backup_originals
        backup_original_files(job, config, project_dir)
    end

    # Save reconstructed data
    save_timeseries(output_source, project_dir, reconstructed_ts)

    return joinpath(project_dir, output_source.data)
end

"""
    backup_original_files(job::ReconstructionJob, config::ReconstructCrossConfiguration, project_dir::String)

Create backup of original files before reconstruction.
"""
function backup_original_files(job::ReconstructionJob, config::ReconstructCrossConfiguration, project_dir::String)
    target_mast_config = findfirst(m -> m.name == job.target_mast, config.masts)
    if target_mast_config === nothing
        return
    end

    mast = config.masts[target_mast_config]
    backup_dir = joinpath(project_dir, config.settings.output_dir, "originals")
    mkpath(backup_dir)

    # Copy original files to backup directory
    original_data_path = joinpath(project_dir, mast.input.data)
    original_sensors_path = joinpath(project_dir, mast.input.sensors)

    if isfile(original_data_path)
        backup_data_path = joinpath(backup_dir, "$(job.target_mast).csv")
        cp(original_data_path, backup_data_path, force=true)
    end

    if isfile(original_sensors_path)
        backup_sensors_path = joinpath(backup_dir, "$(job.target_mast).sensors.yaml")
        cp(original_sensors_path, backup_sensors_path, force=true)
    end
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

    println("💾 Saved reconstruction summary: $summary_path")
end

"""
    print_completion_summary(summary::ReconstructionSummary)

Print a summary of the reconstruction campaign results.
"""
function print_completion_summary(summary::ReconstructionSummary)
    println("\n📊 Reconstruction Campaign Summary:")
    println("  Duration: $(summary.campaign_end - summary.campaign_start)")
    println("  Total jobs: $(summary.total_jobs)")
    println("  Successful: $(summary.successful_jobs)")
    println("  Failed: $(summary.failed_jobs)")
    println("  Overall fill rate: $(round(summary.overall_fill_percentage, digits=1))%")
    println("  Average correlation: $(round(summary.average_correlation, digits=3))")

    if summary.successful_jobs > 0
        println("\n✅ Successful Reconstructions:")
        for result in summary.job_results
            if result.success
                total_metrics = length(result.windspeed_metrics) + length(result.winddirection_metrics)
                total_filled = sum(m.filled_points for m in vcat(result.windspeed_metrics, result.winddirection_metrics))
                println("    $(result.job.target_mast) ← $(result.job.source_mast): $total_filled points filled across $total_metrics sensors")
            end
        end
    end
end

end # module
