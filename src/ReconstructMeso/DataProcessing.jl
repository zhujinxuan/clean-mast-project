module DataProcessing

using DataFrames
using Statistics
using Dates
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
using ...Types.ReconstructMeso: TrainingTimeRange
using ...Types.CleanMastConfig: TimeRange
using ...Types.Sector: degree_diff

"""
Ensure TimeSeriesData has all timestamps in range at specified interval
"""
function ensure_complete_timeseries(ts::TimeSeriesData, time_range::TrainingTimeRange, 
                                  interval::Period)::TimeSeriesData
    start_time = time_range.min
    end_time = time_range.max
    
    # Create complete timestamp sequence
    complete_timestamps = collect(start_time:interval:end_time)
    
    # Create new DataFrame with complete timestamps and initialize with Union{Missing, Float64}
    new_df = DataFrame(timestamp = complete_timestamps)
    
    # Add sensor columns with missing values, ensuring proper type
    for sensor in ts.sensors
        new_df[!, sensor.columnName] = Vector{Union{Missing, Float64}}(missing, length(complete_timestamps))
    end
    
    # Fill in existing values
    matching_timestamps = map(t -> t ∈ ts.df.timestamp, complete_timestamps)
    matching_indices = indexin(complete_timestamps[matching_timestamps], ts.df.timestamp)
    sensor_columns = [s.columnName for s in ts.sensors]
    
    new_df[matching_timestamps, sensor_columns] = ts.df[matching_indices, sensor_columns]
    
    TimeSeriesData(new_df, ts.sensors)
end

"""
Interpolate meso data to specified interval using vector calculation, by default interval is 10 minutes
"""
function interpolate_meso_data(ts::TimeSeriesData, time_range::TrainingTimeRange; interval::Period=Minute(10))::TimeSeriesData
    # Create target timestamps at specified intervals
    target_df = DataFrame(timestamp = collect(time_range.min:interval:time_range.max))
    
    # Join with existing data, creating missing values for timestamps in between
    result_df = leftjoin(target_df, ts.df, on = :timestamp)
    sort!(result_df, :timestamp)
    
    # Interpolate each sensor column
    for sensor in ts.sensors
        col = sensor.columnName
        values = result_df[!, col]
        timestamps = result_df.timestamp
        
        # Find valid data points
        valid_mask = .!ismissing.(values)
        if !any(valid_mask)
            continue
        end
        
        # For each missing value, interpolate from surrounding valid points
        missing_mask = ismissing.(values)
        for i in findall(missing_mask)
            # Find surrounding valid points
            before_idx = findlast(j -> j < i && valid_mask[j], 1:length(values))
            after_idx = findfirst(j -> j > i && valid_mask[j], 1:length(values))
            
            if isnothing(before_idx) || isnothing(after_idx)
                continue
            end
            
            before_time = timestamps[before_idx]
            after_time = timestamps[after_idx]
            before_val = values[before_idx]
            after_val = values[after_idx]
            
            # Calculate interpolation fraction
            time_frac = (timestamps[i] - before_time) / (after_time - before_time)
            
            if sensor.sensorType == "WindDirection"
                # Handle circular interpolation for wind direction
                angle_diff = degree_diff(after_val, before_val)
                result_df[i, col] = mod(before_val + time_frac * angle_diff, 360)
            else
                # Linear interpolation for other values
                result_df[i, col] = before_val + time_frac * (after_val - before_val)
            end
        end
    end
    
    TimeSeriesData(result_df, ts.sensors)
end

"""
Prepare mast and meso data for training by ensuring complete timestamps and proper interpolation
"""
function prepare_training_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData)::Tuple{TimeSeriesData, TimeSeriesData}
    # Calculate the mast data range
    mast_min = minimum(filter(!ismissing, mast_ts.df.timestamp))
    mast_max = maximum(filter(!ismissing, mast_ts.df.timestamp))
    time_range = TrainingTimeRange(mast_min, mast_max)
    
    # Interpolate meso data to 10-minute intervals for the mast data range
    interpolated_meso = interpolate_meso_data(meso_ts, time_range)
    
    # Ensure mast data has complete timestamps within its range
    complete_mast = ensure_complete_timeseries(mast_ts, time_range, Minute(10))
    
    return complete_mast, interpolated_meso
end

"""
Calculate training time range from mast time series and optional time range input
"""
function calculate_training_timerange(ts::TimeSeriesData, time_range::Union{TimeRange,Nothing}) :: TrainingTimeRange
    if isnothing(time_range)
        time_range = TimeRange(nothing, nothing)
    end
    
    # Get data bounds
    data_max = maximum(ts.df.timestamp)
    
    # Calculate default range (1 year before max date)
    default_min = floor(something(time_range.max, data_max) - Year(1), Month(1))
    
    # Determine actual min and max
    actual_min = something(time_range.min, default_min)
    actual_max = something(time_range.max, actual_min + Year(1))
    # If actual_max is at the start of day, then reduce by 1 second to avoid partial day
    if is_start_of_day(actual_max)
        actual_max -= Second(1)
    end
    
    TrainingTimeRange(actual_min, actual_max)
end

"""
Check if a given DateTime is at the start of a day
"""
function is_start_of_day(dt::DateTime)::Bool
    return hour(dt) == 0 && minute(dt) == 0 && second(dt) == 0
end

export prepare_training_data, calculate_training_timerange

end 