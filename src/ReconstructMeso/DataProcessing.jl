module DataProcessing

using DataFrames
using Statistics
using Dates
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.ReconstructMeso: TrainingTimeRange
using ...Types.CleanMastConfig: TimeRange
"""
Ensure TimeSeriesData has all timestamps in range at specified interval
"""
function ensure_complete_timeseries(ts::TimeSeriesData, time_range::TrainingTimeRange, 
                                  interval::Minute=Minute(10))::TimeSeriesData
    # Generate complete timestamp sequence
    all_timestamps = time_range.min:interval:time_range.max
    
    # Create DataFrame with all timestamps
    complete_df = DataFrame(timestamp = collect(all_timestamps))
    
    # Join with existing data
    result_df = leftjoin(complete_df, ts.df, on=:timestamp)
    
    TimeSeriesData(result_df, ts.sensors)
end

"""
Prepare time series data by ensuring complete timestamps at specified interval
"""
function prepare_timeseries(ts::TimeSeriesData, time_range::TrainingTimeRange, 
                          interval::Minute)::TimeSeriesData
    # First ensure we have data for the full time range at specified interval
    complete_ts = ensure_complete_timeseries(ts, time_range, interval)
    
    # Sort by timestamp to ensure proper ordering
    sort!(complete_ts.df, :timestamp)
    
    complete_ts
end

"""
Average data over 15-day periods within time_range, marking periods with >30% missing data as missing
"""
function average_timeseries(ts::TimeSeriesData, time_range::TrainingTimeRange, period_days::Int=15)::TimeSeriesData
    # First ensure complete timeseries at appropriate interval
    interval = ts.sensors[1].sensorType == "WindSpeed" ? Minute(10) : Minute(60)
    prepared_ts = prepare_timeseries(ts, time_range, interval)
    
    # Calculate periods relative to start_time
    prepared_ts.df[!, :period] = floor.(Int, (prepared_ts.df.timestamp .- time_range.min) / Day(period_days))
    
    # Calculate averages for each sensor in each period
    sensor_cols = [s.columnName for s in ts.sensors]
    
    period_averages = combine(groupby(prepared_ts.df, :period)) do group
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
        period_start = time_range.min + Day(period_days * first(group.period))
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
Calculate training time range from mast time series and optional time range input
"""
function calculate_training_timerange(mast_ts::TimeSeriesData, time_range::TimeRange)::TrainingTimeRange
    mast_min = minimum(mast_ts.df.timestamp)
    mast_max = maximum(mast_ts.df.timestamp)
    
    if !isnothing(time_range.min) && !isnothing(time_range.max)
        return TrainingTimeRange(time_range.min, time_range.max)
    end
    
    if !isnothing(time_range.min)
        range_min = time_range.min
        range_max = min(time_range.min + Year(1), mast_max)
    elseif !isnothing(time_range.max)
        range_max = time_range.max
        range_min = max(time_range.max - Year(1), mast_min)
    else
        range_max = mast_max
        range_min = max(mast_max - Year(1), mast_min)
    end
    
    TrainingTimeRange(range_min, range_max)
end

export average_timeseries, find_nearest_height_sensor, prepare_timeseries, calculate_training_timerange

end 