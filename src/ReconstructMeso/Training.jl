module Training

using DataFrames
using Statistics
using GLM
using Dates
using ...Types.ReconstructMeso
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
using ...Types.Sector: degree_diff
using ..DataProcessing: prepare_training_data

# Constants for direction sectors (22.5 degrees each)
const SECTOR_SIZE = 22.5
const NUM_SECTORS = 16
const SECTORS = [(i * SECTOR_SIZE, (i + 1) * SECTOR_SIZE) for i in 0:(NUM_SECTORS-1)]

"""
Get the sector index for a given direction
"""
function get_direction_sector(direction::Float64)::Int
    mod(floor(Int, direction / SECTOR_SIZE), NUM_SECTORS) + 1
end

"""
Train wind speed correlation between mast and meso data using sector-based approach
"""
function train_wind_speed(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, 
                         min_height::Float64=50.0)::WindSpeedTrainResults
    # Filter mast sensors above minimum height
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindSpeed" && 
                             s.statType == "avg", mast_ts.sensors)
    
    # Create pairs of (mast_sensor, meso_sensor)
    sensor_pairs = filter(pair -> !isnothing(pair[2]),
        map(mast_sensor -> (
            mast_sensor,
            find_nearest_height_sensor(mast_sensor.height, meso_ts.sensors, "WindSpeed", "avg")
        ), mast_sensors)
    )
    
    # Process each valid sensor pair and create results dictionary
    Dict(
        pair[1].columnName => result
        for pair in sensor_pairs
        for result in [process_windspeed_sensor_pair(pair[1], pair[2], mast_ts, meso_ts)]
        if !isnothing(result)
    )
end

function process_windspeed_sensor_pair(mast_sensor::SensorColumn, meso_sensor::SensorColumn,
                           mast_ts::TimeSeriesData, meso_ts::TimeSeriesData
                           )::Union{WindSpeedTrainResult, Nothing}
    # Get meso direction sensor for sector determination
    meso_dir_sensor = find_highest_direction_sensor(meso_ts.sensors)
    isnothing(meso_dir_sensor) && return nothing
    
    # Get paired values with direction
    paired_data = DataFrame(
        mast_speed = mast_ts.df[!, mast_sensor.columnName],
        meso_speed = meso_ts.df[!, meso_sensor.columnName],
        meso_dir = meso_ts.df[!, meso_dir_sensor.columnName]
    )
    
    # Filter out missing values
    paired_data = filter(row -> !any(ismissing, row), paired_data)
    nrow(paired_data) < 10 && return nothing
    
    # Train models for each sector
    sector_models = map(SECTORS) do (sector_start, sector_end)
        # Filter data for this sector
        sector_data = filter(row -> 
            sector_start <= row.meso_dir < sector_end, paired_data)
        
        if nrow(sector_data) >= 5  # Minimum points for regression
            # Fit linear model using GLM
            model = lm(@formula(mast_speed ~ meso_speed), sector_data)
            coefs = coef(model)
            WindSpeedSectorModel(sector_start, sector_end, coefs[2], coefs[1])
        else
            # Use overall correlation if not enough data in sector
            model = lm(@formula(mast_speed ~ meso_speed), paired_data)
            coefs = coef(model)
            WindSpeedSectorModel(sector_start, sector_end, coefs[2], coefs[1])
        end
    end
    
    WindSpeedTrainResult(mast_sensor, meso_sensor, meso_dir_sensor, sector_models)
end

"""
Find highest wind direction sensor
"""
function find_highest_direction_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}
    dir_sensors = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", sensors)
    isempty(dir_sensors) && return nothing
    
    reduce((s1, s2) -> s1.height > s2.height ? s1 : s2, dir_sensors)
end

"""
Train wind direction offset between mast and meso data
"""
function train_wind_direction(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, 
                            min_height::Float64=50.0)::WindDirectionTrainResults
    # Filter mast sensors above minimum height
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindDirection" && 
                             s.statType == "avg", mast_ts.sensors)
    
    # Create pairs of (mast_sensor, meso_sensor)
    sensor_pairs = filter(pair -> !isnothing(pair[2]),
        map(mast_sensor -> (
            mast_sensor,
            find_nearest_height_sensor(mast_sensor.height, meso_ts.sensors, "WindDirection", "avg")
        ), mast_sensors)
    )
    
    # Process each valid sensor pair and create results dictionary
    Dict(
        pair[1].columnName => result
        for pair in sensor_pairs
        for result in [process_winddirection_sensor_pair(pair[1], pair[2], mast_ts, meso_ts)]
        if !isnothing(result)
    )
end

function process_winddirection_sensor_pair(mast_sensor::SensorColumn, meso_sensor::SensorColumn,
                                         mast_ts::TimeSeriesData, meso_ts::TimeSeriesData
                                         )::Union{WindDirectionTrainResult, Nothing}
    # Get paired values
    paired_values = collect(zip(
        mast_ts.df[!, mast_sensor.columnName],
        meso_ts.df[!, meso_sensor.columnName]
    ))
    
    # Filter out missing values
    valid_pairs = filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), paired_values)
    length(valid_pairs) < 10 && return nothing
    
    # Unzip the filtered pairs
    mast_filtered, meso_filtered = map(i -> Float64[p[i] for p in valid_pairs], (1, 2))
    
    # Calculate direction differences considering circular nature
    diffs = degree_diff.(mast_filtered, meso_filtered)
    mean_diff = mean(diffs)
    
    WindDirectionTrainResult(mast_sensor, meso_sensor, mean_diff)
end

export train_wind_speed, train_wind_direction

end 