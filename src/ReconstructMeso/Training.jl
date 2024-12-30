module Training

using DataFrames
using Statistics
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.ReconstructMeso: WindSpeedTrainResult, WindDirectionTrainResult,
                               WindSpeedTrainResults, WindDirectionTrainResults
using ..DataProcessing: find_nearest_height_sensor, average_timeseries

"""
Train wind speed correlation between mast and meso data using 15-day averages
"""
function train_wind_speed(avg_mast_ts::TimeSeriesData, avg_meso_ts::TimeSeriesData, 
                         min_height::Float64=50.0)::WindSpeedTrainResults
    # Filter mast sensors above minimum height
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindSpeed" && 
                             s.statType == "avg", avg_mast_ts.sensors)
    
    results = Dict{Symbol, WindSpeedTrainResult}()
    
    for mast_sensor in mast_sensors
        meso_sensor = find_nearest_height_sensor(mast_sensor.height, avg_meso_ts.sensors, 
                                               "WindSpeed", "avg")
        isnothing(meso_sensor) && continue
        
        # Get paired values using zip and filter
        mast_values = avg_mast_ts.df[!, mast_sensor.columnName]
        meso_values = avg_meso_ts.df[!, meso_sensor.columnName]
        
        paired_values = filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), 
                             zip(mast_values, meso_values))
        
        length(paired_values) < 10 && continue
        
        # Unzip the filtered pairs into x and y vectors
        y, x = collect(zip(paired_values...))
        
        # Simple linear regression
        slope = cov(x, y) / var(x)
        intercept = mean(y) - slope * mean(x)
        
        results[mast_sensor.columnName] = WindSpeedTrainResult(
            mast_sensor, meso_sensor, slope, intercept
        )
    end
    
    return results
end

"""
Train wind direction offset between mast and meso data using 15-day averages
"""
function train_wind_direction(avg_mast_ts::TimeSeriesData, avg_meso_ts::TimeSeriesData, 
                            min_height::Float64=50.0)::WindDirectionTrainResults
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindDirection" && 
                             s.statType == "avg", avg_mast_ts.sensors)
    
    results = Dict{Symbol, WindDirectionTrainResult}()
    
    for mast_sensor in mast_sensors
        meso_sensor = find_nearest_height_sensor(mast_sensor.height, avg_meso_ts.sensors, 
                                               "WindDirection", "avg")
        isnothing(meso_sensor) && continue
        
        # Get paired values using zip and filter
        mast_values = avg_mast_ts.df[!, mast_sensor.columnName]
        meso_values = avg_meso_ts.df[!, meso_sensor.columnName]
        
        paired_values = filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), 
                             zip(mast_values, meso_values))
        
        length(paired_values) < 10 && continue
        
        # Unzip the filtered pairs
        mast_filtered, meso_filtered = collect(zip(paired_values...))
        
        diffs = @. mod((mast_filtered - meso_filtered + 180), 360) - 180
        mean_diff = mean(diffs)
        
        results[mast_sensor.columnName] = WindDirectionTrainResult(
            mast_sensor, meso_sensor, mean_diff
        )
    end
    
    return results
end

export train_wind_speed, train_wind_direction

end 