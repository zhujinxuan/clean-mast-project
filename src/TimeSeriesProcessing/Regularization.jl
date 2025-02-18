module Regularization
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using DataFrames
using Dates

"""
    ensure_regular_intervals(ts::TimeSeriesData, time_range::TimeRange, 
                           interval::Period)::TimeSeriesData

Ensure TimeSeriesData has all timestamps in range at specified interval.
Missing values will be created for timestamps that don't exist in the original data.

# Arguments
- `ts::TimeSeriesData`: Input time series data
- `time_range::TimeRange`: Time range to ensure coverage for
- `interval::Period`: Time interval between points (e.g., Minute(10))

# Returns
- `TimeSeriesData`: Time series with regular intervals and missing values where needed
"""
function ensure_regular_intervals(ts::TimeSeriesData, time_range::TimeRange, 
                                interval::Period)::TimeSeriesData
    # Create complete timestamp sequence
    complete_timestamps = collect(time_range.min:interval:time_range.max)
    
    # Create new DataFrame with complete timestamps
    new_df = DataFrame(timestamp = complete_timestamps)
    
    # Add sensor columns with missing values
    for sensor in ts.sensors
        new_df[!, sensor.columnName] = Vector{Union{Missing, Float64}}(missing, length(complete_timestamps))
    end
    
    # Fill in existing values where timestamps match
    matching_timestamps = map(t -> t ∈ ts.df.timestamp, complete_timestamps)
    if any(matching_timestamps)
        matching_indices = indexin(complete_timestamps[matching_timestamps], ts.df.timestamp)
        sensor_columns = [s.columnName for s in ts.sensors]
        new_df[matching_timestamps, sensor_columns] = ts.df[matching_indices, sensor_columns]
    end
    
    TimeSeriesData(new_df, ts.sensors)
end

"""
    find_gaps(ts::TimeSeriesData, interval::Period)::Vector{Tuple{DateTime,DateTime}}

Find gaps in time series data that are larger than the specified interval.

# Arguments
- `ts::TimeSeriesData`: Input time series data
- `interval::Period`: Expected time interval between points

# Returns
- `Vector{Tuple{DateTime,DateTime}}`: Vector of (gap_start, gap_end) tuples
"""
function find_gaps(ts::TimeSeriesData, interval::Period)::Vector{Tuple{DateTime,DateTime}}
    gaps = Tuple{DateTime,DateTime}[]
    timestamps = sort(unique(ts.df.timestamp))
    gaps = collect(zip(timestamps[1:end-1], timestamps[2:end]))
    filter(gap -> gap[2] - gap[1] > interval, gaps)
end

"""
    validate_intervals(ts::TimeSeriesData, expected_interval::Period)::Bool

Check if time series has regular intervals matching the expected interval.

# Arguments
- `ts::TimeSeriesData`: Input time series data
- `expected_interval::Period`: Expected time interval between points

# Returns
- `Bool`: true if all intervals match expected_interval, false otherwise
"""
function validate_intervals(ts::TimeSeriesData, expected_interval::Period)::Bool
    timestamps = sort(unique(ts.df.timestamp))
    if length(timestamps) < 2
        return true
    end
    
    for i in 1:(length(timestamps)-1)
        if timestamps[i+1] - timestamps[i] != expected_interval
            return false
        end
    end
    
    true
end

export ensure_regular_intervals, find_gaps, validate_intervals 
end