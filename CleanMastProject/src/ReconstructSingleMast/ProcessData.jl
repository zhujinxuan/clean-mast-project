module ProcessData

using DataFrames
using Dates
using Statistics

using CleanMastProject.Types.ReconstructSingleMast: ReconstructedSuccess, ReconstructedFailure, ReconstructionResults
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange
using CleanMastProject.TimeSeriesProcessing.Regularization: ensure_regular_intervals, validate_intervals
using CleanMastProject.TimeSeriesProcessing.IntervalDetection: detect_representative_interval

using ..GroupByHour: process_by_hour
using ..WindSpeedReconstructHourly: reconstruct_hourly_speeds
using ..WindDirectionReconstructHourly: reconstruct_hourly_directions

"""
    apply_success_reconstruction!(df::DataFrame, successes::Vector{ReconstructedSuccess})::Nothing

Apply reconstructed values to a DataFrame in-place.

Groups reconstruction results by column and updates the DataFrame with reconstructed values
at the corresponding timestamps.

# Arguments
- `df::DataFrame`: DataFrame to update (modified in-place)
- `successes::Vector{ReconstructedSuccess}`: Successful reconstruction results to apply

# Returns
- `Nothing`: DataFrame is modified in-place
"""
function apply_success_reconstruction!(
    df::DataFrame,
    successes::Vector{ReconstructedSuccess}
)::Nothing

    # Early exit if no successes
    isempty(successes) && return nothing

    # Group reconstructed values by column
    by_column = Dict{Symbol, Vector{Tuple{DateTime, Float64}}}()
    for success in successes
        push!(get!(by_column, success.columnName, Tuple{DateTime, Float64}[]),
              (success.timestamp, success.value))
    end

    # Update df column by column
    for (col, time_values) in by_column
        times = first.(time_values)
        values = last.(time_values)
        df[in.(df.timestamp, Ref(times)), col] .= values
    end

    return nothing
end

"""
    process_data!(data::TimeSeriesData)::ReconstructionResults

Apply reconstruction to data.df and return reconstruction results.

This function:
1. Regularizes the time series to consistent intervals
2. Groups data by hour
3. Reconstructs missing wind speeds and directions hourly
4. Applies all reconstructed values back to the original data

# Arguments
- `data::TimeSeriesData`: Time series data (modified in-place)

# Returns
- `ReconstructionResults`: Summary of successful and failed reconstructions
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
        data = ensure_regular_intervals(data, time_range, representative_interval)

        regularized_rows = nrow(data.df)
        println("  ✓ Regularized from $original_rows to $regularized_rows timestamps")
        println("  ✓ All timestamps now at $(representative_interval.value)-minute intervals")
    else
        println("  ✓ Time series already has regular $(representative_interval.value)-minute intervals")
    end

    # Step 2: Filter to only 'avg' statType for reconstruction
    avg_sensors = filter(s -> s.statType == "avg", data.sensors)
    avg_sensor_cols = [s.columnName for s in avg_sensors]
    avg_df = select(data.df, vcat([:timestamp], avg_sensor_cols))
    avg_data = TimeSeriesData(avg_df, avg_sensors)

    # Step 3: Process reconstructions by hour
    println("\n📊 Processing reconstructions by hour...")
    start_time = time()

    # Reconstruct wind speeds
    println("  • Reconstructing wind speeds...")
    speed_results = process_by_hour(avg_data, hour_data -> reconstruct_hourly_speeds(hour_data, representative_interval))

    # Reconstruct wind directions
    println("  • Reconstructing wind directions...")
    direction_results = process_by_hour(avg_data, hour_data -> reconstruct_hourly_directions(hour_data, representative_interval))

    # Combine results
    all_results = vcat(speed_results, direction_results)

    # Step 3: Partition into successes and failures
    successes = ReconstructedSuccess[r for r in all_results if r isa ReconstructedSuccess]
    failures = ReconstructedFailure[r for r in all_results if r isa ReconstructedFailure]

    # Step 4: Filter invalid results
    original_success_count = length(successes)
    successes = ReconstructedSuccess[s for s in successes if !ismissing(s.value) && !isnan(s.value)]
    filtered_out = original_success_count - length(successes)

    # Step 5: Apply reconstructed values to DataFrame
    apply_success_reconstruction!(data.df, successes)

    total_time = time() - start_time

    # Step 7: Show summary
    total_reconstructed = length(successes)
    total_failures = length(failures)
    total_attempts = total_reconstructed + total_failures
    success_rate = total_attempts > 0 ? round(total_reconstructed / total_attempts * 100, digits=1) : 0.0

    println("\n✓ Reconstruction completed:")
    println("  • Total attempts: $total_attempts")
    println("  • Successful: $total_reconstructed")
    println("  • Failed: $total_failures")
    if filtered_out > 0
        println("  • Filtered out: $filtered_out invalid results")
    end
    println("  • Success rate: $(success_rate)%")
    println("  • Total time: $(round(total_time, digits=1))s")

    # Show breakdown by sensor type
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
end

export process_data!

end # module
