module DataProcessing

using DataFrames
using Statistics
using Dates
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.CleanMastConfig: TimeRange

"""
Average data over 15-day periods within time_range, marking periods with >30% missing data as missing
"""
function average_timeseries(ts::TimeSeriesData, time_range::TimeRange, period_days::Int=15)::TimeSeriesData
    # Group data by 15-day periods
    df = ts.df
    
    # Filter data within time range
    start_time = something(time_range.min, minimum(df.timestamp))
    end_time = something(time_range.max, maximum(df.timestamp))
    time_mask = start_time .<= df.timestamp .<= end_time
    period_df = df[time_mask, :]
    
    # Calculate periods relative to start_time
    period_df[!, :period] = floor.(Int, (period_df.timestamp .- start_time) / Day(period_days))
    
    # Calculate averages for each sensor in each period
    sensor_cols = [s.columnName for s in ts.sensors]
    
    period_averages = combine(groupby(period_df, :period)) do group
        # For each sensor column
        result = Dict{Symbol, Union{Float64, Missing}}()
        for col in sensor_cols
            values = group[!, col]
            # If more than 30% missing, return missing
            if mean(ismissing.(values)) > 0.3
                result[col] = missing
            else
                result[col] = mean(skipmissing(values))
            end
        end
        # Add timestamp as middle of period
        period_start = start_time + Day(period_days * first(group.period))
        result[:timestamp] = period_start + Day(period_days ÷ 2)
        result
    end
    
    TimeSeriesData(period_averages, ts.sensors)
end

"""
Find nearest height sensor of specified type in sensors list
"""
function find_nearest_height_sensor(target_height::Float64, sensors::Vector{SensorColumn}, 
                                  sensor_type::String, stat_type::String="avg")::Union{SensorColumn, Nothing}
    matching_sensors = filter(s -> s.sensorType == sensor_type && s.statType == stat_type, sensors)
    isempty(matching_sensors) && return nothing
    
    # Find sensor with closest height
    closest_sensor = reduce((s1, s2) -> 
        abs(s1.height - target_height) < abs(s2.height - target_height) ? s1 : s2, 
        matching_sensors)
    
    return closest_sensor
end

"""
Ensure TimeSeriesData has all timestamps in range at 10-minute intervals
"""
function ensure_complete_timeseries(ts::TimeSeriesData, time_range::TimeRange)::TimeSeriesData
    start_time = something(time_range.min, minimum(ts.df.timestamp))
    end_time = something(time_range.max, maximum(ts.df.timestamp))
    
    # Generate complete timestamp sequence
    all_timestamps = start_time:Minute(10):end_time
    
    # Create DataFrame with all timestamps
    complete_df = DataFrame(timestamp = all_timestamps)
    
    # Join with existing data
    result_df = leftjoin(complete_df, ts.df, on=:timestamp)
    
    TimeSeriesData(result_df, ts.sensors)
end

"""
Interpolate hourly meso data to 10-minute intervals
"""
function interpolate_meso_data(meso_ts::TimeSeriesData, time_range::TimeRange)::TimeSeriesData
    # Ensure we have complete hourly data first
    hourly_ts = ensure_complete_timeseries(meso_ts, time_range)
    
    # Generate 10-minute timestamps
    start_time = something(time_range.min, minimum(hourly_ts.df.timestamp))
    end_time = something(time_range.max, maximum(hourly_ts.df.timestamp))
    target_timestamps = start_time:Minute(10):end_time
    
    # Create result DataFrame
    result_df = DataFrame(timestamp = target_timestamps)
    
    # Interpolate each sensor
    for sensor in meso_ts.sensors
        col = sensor.columnName
        # Linear interpolation
        result_df[!, col] = linear_interpolate(
            hourly_ts.df.timestamp,
            hourly_ts.df[!, col],
            target_timestamps
        )
    end
    
    TimeSeriesData(result_df, meso_ts.sensors)
end

"""
Linear interpolation helper
"""
function linear_interpolate(x::Vector{DateTime}, y::Vector{Union{Float64, Missing}}, 
                          xi::Vector{DateTime})::Vector{Union{Float64, Missing}}
    # Convert DateTime to Float64 seconds for interpolation
    x_float = Float64.(datetime2unix.(x))
    xi_float = Float64.(datetime2unix.(xi))
    
    result = Vector{Union{Float64, Missing}}(missing, length(xi))
    
    for (i, x_i) in enumerate(xi_float)
        # Find surrounding points
        idx = searchsorted(x_float, x_i)
        if idx.start == 1 || idx.stop > length(x_float)
            continue  # Outside range - leave as missing
        end
        
        left_idx = idx.start - 1
        right_idx = idx.start
        
        # Skip if either surrounding point is missing
        if ismissing(y[left_idx]) || ismissing(y[right_idx])
            continue
        end
        
        # Linear interpolation
        t = (x_i - x_float[left_idx]) / (x_float[right_idx] - x_float[left_idx])
        result[i] = y[left_idx] + t * (y[right_idx] - y[left_idx])
    end
    
    return result
end

export average_timeseries, find_nearest_height_sensor, ensure_complete_timeseries, 
       interpolate_meso_data

end 