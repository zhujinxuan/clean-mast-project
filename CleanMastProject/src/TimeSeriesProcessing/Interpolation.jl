module Interpolation
using Dates
using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.Sector: degree_diff

"""
    interpolate_timeseries(ts::TimeSeriesData, target_timestamps::Vector{DateTime})::TimeSeriesData

Interpolate time series data to match target timestamps using linear interpolation for numeric values
and circular interpolation for wind directions.

# Arguments
- `ts::TimeSeriesData`: Input time series data
- `target_timestamps::Vector{DateTime}`: Target timestamps for interpolation

# Returns
- `TimeSeriesData`: Interpolated time series with values at target timestamps
"""
function interpolate_timeseries(ts::TimeSeriesData, target_timestamps::Vector{DateTime})::TimeSeriesData
    # Create target DataFrame with timestamps
    result_df = DataFrame(timestamp = target_timestamps)
    sort!(result_df, :timestamp)
    
    # Interpolate each sensor column
    for sensor in ts.sensors
        col = sensor.columnName
        values = ts.df[!, col]
        timestamps = ts.df.timestamp
        
        # Initialize result column with missing values
        result_df[!, col] = Vector{Union{Missing, Float64}}(missing, length(target_timestamps))
        
        # Find valid data points in source
        valid_mask = .!ismissing.(values)
        if !any(valid_mask)
            continue
        end
        
        # Get valid source data
        valid_timestamps = timestamps[valid_mask]
        valid_values = values[valid_mask]
        
        # Count interpolated points
        interpolated_count = 0
        exact_match_count = 0
        outside_range_count = 0
        
        # Interpolate for each target timestamp
        for (i, target_time) in enumerate(target_timestamps)
            # Skip if target time is outside source range
            if target_time < first(valid_timestamps) || target_time > last(valid_timestamps)
                outside_range_count += 1
                continue
            end
            
            # Find surrounding valid points
            before_idx = findlast(t -> t <= target_time, valid_timestamps)
            after_idx = findfirst(t -> t > target_time, valid_timestamps)
            
            if isnothing(before_idx) || isnothing(after_idx)
                continue
            end
            
            before_time = valid_timestamps[before_idx]
            after_time = valid_timestamps[after_idx]
            before_val = valid_values[before_idx]
            after_val = valid_values[after_idx]
            
            # If exact match, use the value directly
            if target_time == before_time
                result_df[i, col] = before_val
                exact_match_count += 1
                continue
            end
            
            # Calculate interpolation fraction
            time_frac = (target_time - before_time) / (after_time - before_time)
            
            if sensor.sensorType == "WindDirection"
                # Handle circular interpolation for wind direction
                angle_diff = degree_diff(after_val, before_val)
                result_df[i, col] = mod(before_val + time_frac * angle_diff, 360)
            else
                # Linear interpolation for other values
                result_df[i, col] = before_val + time_frac * (after_val - before_val)
            end
            interpolated_count += 1
        end
    end
    
    TimeSeriesData(result_df, ts.sensors)
end

"""
    interpolate_to_interval(ts::TimeSeriesData, interval::Period)::TimeSeriesData

Interpolate time series to regular intervals within its time range.

# Arguments
- `ts::TimeSeriesData`: Input time series data
- `interval::Period`: Target time interval (e.g., Minute(10))

# Returns
- `TimeSeriesData`: Interpolated time series with regular intervals
"""
function interpolate_to_interval(ts::TimeSeriesData, interval::Period)::TimeSeriesData
    # Get data bounds
    valid_times = filter(!ismissing, ts.df.timestamp)
    if isempty(valid_times)
        return ts
    end
    
    start_time = minimum(valid_times)
    end_time = maximum(valid_times)
    
    # Create target timestamps
    target_timestamps = collect(start_time:interval:end_time)
    
    # Perform interpolation
    interpolate_timeseries(ts, target_timestamps)
end

export interpolate_timeseries, interpolate_to_interval 
end