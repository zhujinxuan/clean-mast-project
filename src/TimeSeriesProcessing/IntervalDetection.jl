"""
Interval Detection Utilities for Time Series Processing

This module provides functions to detect the representative time interval
in time series data, which is crucial for accurate data coverage calculations.
"""

module IntervalDetection

# TimeSeriesData type will be available from parent module context
using Dates
using Statistics

export detect_representative_interval

"""
    detect_representative_interval(ts_data::TimeSeriesData)::Minute

Detect the most commonly occurring time interval in a time series dataset.
This function analyzes the timestamp differences and returns the mode (most frequent) interval.

# Arguments
- `ts_data::TimeSeriesData`: Input time series data containing timestamps

# Returns
- `Minute`: The representative interval as a Dates.Minute object

# Algorithm
1. Extract all valid (non-missing) timestamps
2. Calculate consecutive timestamp differences
3. Round differences to nearest minute to handle minor timing variations
4. Find the mode (most frequent) interval
5. Return the representative interval

# Examples
```julia
# For 10-minute interval data
interval = detect_representative_interval(mast_data)
# Returns: Minute(10)

# For 1-hour interval data  
interval = detect_representative_interval(hourly_data)
# Returns: Minute(60)
```

# Edge Cases
- If no valid timestamps exist, returns Minute(10) as default
- If only one timestamp exists, returns Minute(10) as default
- If multiple intervals have equal frequency, returns the smallest one
- Handles irregular data by finding the most common interval
"""
function detect_representative_interval(ts_data)
    # Extract valid timestamps and sort them
    valid_timestamps = filter(!ismissing, ts_data.df.timestamp)
    
    # Handle edge cases
    if length(valid_timestamps) < 2
        @warn "Insufficient timestamps for interval detection. Using default 10-minute interval."
        return Minute(10)
    end
    
    # Sort timestamps to ensure proper ordering
    sorted_timestamps = sort(valid_timestamps)
    
    # Calculate consecutive differences in minutes using vectorized operations
    time_diffs = map(diff -> Int(diff.value ÷ (1000 * 60)),
                     sorted_timestamps[2:end] .- sorted_timestamps[1:end-1])

    # Filter out non-positive differences
    time_diffs = filter(diff -> diff > 0, time_diffs)
    
    # Handle case where no valid differences found
    if isempty(time_diffs)
        @warn "No valid time differences found. Using default 10-minute interval."
        return Minute(10)
    end
    
    # Find the mode (most frequent interval)
    interval_counts = Dict{Int, Int}()
    for diff in time_diffs
        interval_counts[diff] = get(interval_counts, diff, 0) + 1
    end
    
    # Find the most frequent interval (mode)
    # If there's a tie, choose the smallest interval for consistency
    max_count = maximum(values(interval_counts))
    most_frequent_intervals = [interval for (interval, count) in interval_counts if count == max_count]
    representative_interval_minutes = minimum(most_frequent_intervals)
    
    return Minute(representative_interval_minutes)
end

"""
    calculate_expected_points(ts_data::TimeSeriesData, interval::Minute)::Int

Calculate the expected number of data points based on the time range and interval.

# Arguments
- `ts_data::TimeSeriesData`: Input time series data
- `interval::Minute`: The representative interval

# Returns
- `Int`: Expected number of data points
"""
function calculate_expected_points(ts_data, interval)
    valid_timestamps = filter(!ismissing, ts_data.df.timestamp)
    
    if length(valid_timestamps) < 2
        return 0
    end
    
    time_start = minimum(valid_timestamps)
    time_end = maximum(valid_timestamps)
    time_range_minutes = (time_end - time_start).value ÷ (1000 * 60)
    
    return Int(time_range_minutes ÷ interval.value) + 1
end

"""
    get_interval_statistics(ts_data::TimeSeriesData)::NamedTuple

Get detailed statistics about intervals in the time series data.
Useful for debugging and understanding data quality.

# Returns
- NamedTuple with fields: representative_interval, interval_distribution, total_points, expected_points
"""
function get_interval_statistics(ts_data)
    valid_timestamps = filter(!ismissing, ts_data.df.timestamp)
    
    if length(valid_timestamps) < 2
        return (
            representative_interval = Minute(10),
            interval_distribution = Dict{Int, Int}(),
            total_points = length(valid_timestamps),
            expected_points = 0
        )
    end
    
    sorted_timestamps = sort(valid_timestamps)
    
    # Calculate all intervals using vectorized operations
    time_diffs = map(diff -> Int(diff.value ÷ (1000 * 60)),
                     sorted_timestamps[2:end] .- sorted_timestamps[1:end-1])

    # Filter out non-positive differences
    time_diffs = filter(diff -> diff > 0, time_diffs)
    
    # Create interval distribution
    interval_counts = Dict{Int, Int}()
    for diff in time_diffs
        interval_counts[diff] = get(interval_counts, diff, 0) + 1
    end
    
    # Get representative interval
    representative_interval = detect_representative_interval(ts_data)
    expected_points = calculate_expected_points(ts_data, representative_interval)
    
    return (
        representative_interval = representative_interval,
        interval_distribution = interval_counts,
        total_points = length(valid_timestamps),
        expected_points = expected_points
    )
end

end # module IntervalDetection
