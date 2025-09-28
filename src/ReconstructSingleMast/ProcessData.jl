module ProcessData

using YAML
using DataFrames
using Dates
using ProgressMeter

using CleanMastProject.Types.ReconstructSingleMast: ReconstructedSuccess, ReconstructedFailure, ReconstructionResults, find_reconstruction_targets
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange
using CleanMastProject.TimeSeriesProcessing.Regularization: ensure_regular_intervals, validate_intervals
using CleanMastProject.TimeSeriesProcessing.IntervalDetection: detect_representative_interval

using ..WindSpeedTraining
using ..DirectionTraining

"""
Reconstruct missing wind measurements in mast data with progress tracking
"""
function reconstruct_measurements(
    data::TimeSeriesData,
    progress_bar::Union{Progress, Nothing} = nothing,
    total_timestamps::Int = 0,
    representative_interval::Minute = Minute(10)
)::Tuple{Vector{ReconstructedSuccess}, Vector{ReconstructedFailure}}
    
    # Get all reconstruction targets
    speed_targets = find_reconstruction_targets(data, "WindSpeed", "avg", 50.0)
    direction_targets = find_reconstruction_targets(data, "WindDirection", "avg", 50.0)
    
    # Calculate total reconstruction tasks (individual columns to reconstruct)
    total_speed_tasks = sum(length(t.columns) for t in speed_targets; init=0)
    total_direction_tasks = sum(length(t.columns) for t in direction_targets; init=0)
    total_tasks = total_speed_tasks + total_direction_tasks
    
    # Track current progress and timing
    current_task = 0
    slow_tasks = 0
    
    # Process wind speed reconstruction with progress tracking
    speed_successes = ReconstructedSuccess[]
    speed_failures = ReconstructedFailure[]
    
    if !isempty(speed_targets)
        for target in speed_targets
            for col in target.columns
                current_task += 1
                start_time = time()
                
                if !isnothing(progress_bar)
                    ProgressMeter.update!(progress_bar, current_task; showvalues = [
                        (:status, "Reconstructing wind speeds"),
                        (:column, string(col)),
                        (:timestamps, "$total_timestamps timestamps ($(representative_interval.value)-min intervals)"),
                        (:progress, "$current_task / $total_tasks tasks"),
                        (:slow_tasks, "$slow_tasks tasks took >5s")
                    ])
                end
                
                # Process this specific target with timing
                result = WindSpeedTraining.reconstruct_single_target(data, col, target.timestamp)
                
                # Track slow operations
                elapsed = time() - start_time
                if elapsed > 5.0  # Tasks taking more than 5 seconds
                    slow_tasks += 1
                end
                
                if result isa ReconstructedSuccess
                    push!(speed_successes, result)
                else
                    push!(speed_failures, result)
                end
            end
        end
    end
    
    # Process wind direction reconstruction with progress tracking
    direction_successes = ReconstructedSuccess[]
    direction_failures = ReconstructedFailure[]
    
    if !isempty(direction_targets)
        for target in direction_targets
            for col in target.columns
                current_task += 1
                start_time = time()
                
                if !isnothing(progress_bar)
                    ProgressMeter.update!(progress_bar, current_task; showvalues = [
                        (:status, "Reconstructing wind directions"),
                        (:column, string(col)),
                        (:timestamps, "$total_timestamps timestamps ($(representative_interval.value)-min intervals)"),
                        (:progress, "$current_task / $total_tasks tasks"),
                        (:slow_tasks, "$slow_tasks tasks took >5s")
                    ])
                end
                
                # Process this specific target with timing
                result = DirectionTraining.reconstruct_single_target(data, col, target.timestamp)
                
                # Track slow operations
                elapsed = time() - start_time
                if elapsed > 5.0  # Tasks taking more than 5 seconds
                    slow_tasks += 1
                end
                
                if result isa ReconstructedSuccess
                    push!(direction_successes, result)
                else
                    push!(direction_failures, result)
                end
            end
        end
    end
    
    return vcat(speed_successes, direction_successes),
           vcat(speed_failures, direction_failures)
end

"""
Apply reconstruction to data.df and return reconstruction results with progress tracking
"""
function process_data!(
    data::TimeSeriesData
)::ReconstructionResults
    
    # Step 1: Detect representative interval and regularize time series
    representative_interval = detect_representative_interval(data)
    println("🕐 Regularizing time series to $(representative_interval.value)-minute intervals...")

    # Calculate time range from existing data
    time_range = TimeRange(
        minimum(data.df.timestamp),
        maximum(data.df.timestamp)
    )

    original_rows = nrow(data.df)

    # Check if already regularized
    if !validate_intervals(data, representative_interval)
        # Regularize to representative intervals
        data_regularized = ensure_regular_intervals(data, time_range, representative_interval)

        # Replace the data with regularized version
        data = data_regularized

        regularized_rows = nrow(data.df)
        println("  ✓ Regularized from $original_rows to $regularized_rows timestamps")
        println("  ✓ All timestamps now at $(representative_interval.value)-minute intervals")
    else
        println("  ✓ Time series already has regular $(representative_interval.value)-minute intervals")
    end
    
    # Count total reconstruction tasks (individual columns to reconstruct)
    speed_targets = find_reconstruction_targets(data, "WindSpeed", "avg", 50.0)
    direction_targets = find_reconstruction_targets(data, "WindDirection", "avg", 50.0)
    
    total_speed_tasks = sum(length(t.columns) for t in speed_targets; init=0)
    total_direction_tasks = sum(length(t.columns) for t in direction_targets; init=0)
    total_tasks = total_speed_tasks + total_direction_tasks
    
    if total_tasks == 0
        println("ℹ️  No reconstruction targets found - all data is already complete!")
        return ReconstructionResults(Dict{String, Any}[], Dict{String, Any}[])
    end
    
    # Count unique timestamps for information
    all_timestamps = Set{DateTime}()
    for target in speed_targets
        push!(all_timestamps, target.timestamp)
    end
    for target in direction_targets
        push!(all_timestamps, target.timestamp)
    end
    total_timestamps = length(all_timestamps)
    
    # Create progress bar based on total reconstruction tasks
    progress_bar = Progress(total_tasks, desc="Processing reconstruction: ", 
                           barglyphs=BarGlyphs('|','█', ['▁' ,'▂' ,'▃' ,'▄' ,'▅' ,'▆', '▇'],' ','|'),
                           barlen=50,
                           showspeed=true)
    
    try        
        # Apply reconstruction with meaningful progress tracking
        start_time = time()
        successes, failures = reconstruct_measurements(data, progress_bar, total_timestamps, representative_interval)
        total_time = time() - start_time
        
        # Complete progress bar
        ProgressMeter.finish!(progress_bar)
        
        # Filter invalid results
        original_success_count = length(successes)
        successes = filter(s -> !ismissing(s.value) && !isnan(s.value), successes)
        filtered_out = original_success_count - length(successes)
        
        # Group reconstructed values by column
        by_column = Dict{Symbol, Vector{Tuple{DateTime, Float64}}}()
        for success in successes 
            push!(get!(by_column, success.columnName, Tuple{DateTime, Float64}[]), 
                  (success.timestamp, success.value))
        end

        # Update data.df column by column
        for (col, time_values) in by_column
            times = first.(time_values)
            values = last.(time_values)
            data.df[in.(data.df.timestamp, Ref(times)), col] .= values
        end
        
        # Show summary (after progress bar is finished)
        total_reconstructed = length(successes)
        total_failures = length(failures)
        total_attempts = total_reconstructed + total_failures
        success_rate = total_attempts > 0 ? round(total_reconstructed / total_attempts * 100, digits=1) : 0.0
        avg_time_per_task = total_tasks > 0 ? total_time / total_tasks : 0.0
        
        println("\n✓ Reconstruction completed:")
        println("  • Timestamps processed: $total_timestamps (10-minute intervals)")
        println("  • Total attempts: $total_attempts")
        println("  • Successful: $total_reconstructed")
        println("  • Failed: $total_failures")
        if filtered_out > 0
            println("  • Filtered out: $filtered_out invalid results")
        end
        println("  • Success rate: $(success_rate)%")
        println("  • Total time: $(round(total_time, digits=1))s")
        println("  • Average time per task: $(round(avg_time_per_task * 1000, digits=1))ms")

        # Show breakdown by sensor type if available
        speed_successes = filter(s -> any(sensor -> sensor.columnName == s.columnName && sensor.sensorType == "WindSpeed", data.sensors), successes)
        direction_successes = filter(s -> any(sensor -> sensor.columnName == s.columnName && sensor.sensorType == "WindDirection", data.sensors), successes)
        
        if !isempty(speed_successes) || !isempty(direction_successes)
            println("  • Wind speed: $(length(speed_successes)) points")
            println("  • Wind direction: $(length(direction_successes)) points")
        end

        # Prepare typed result
        result = ReconstructionResults(
            [Dict{String, Any}("timestamp" => s.timestamp, "columnName" => s.columnName, "value" => s.value) for s in successes],
            [Dict{String, Any}("timestamp" => f.timestamp, "columnName" => f.columnName, "reason" => f.reason) for f in failures]
        )

        return result
        
    catch e
        # Ensure progress bar is cleaned up on error
        ProgressMeter.finish!(progress_bar)
        rethrow(e)
    end
end

export reconstruct_measurements, process_data!

end # module 