module Analysis

using DataFrames
using Statistics
using Dates
using GLM
using ...Types.RepresentativeYear
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.ReconstructMeso: TrainingTimeRange

"""
Find target wind speed sensor closest to specified height in mast data
"""
function find_target_mast_sensor(ts::TimeSeriesData, target_height::Float64)::Union{SensorColumn, Nothing}
    ws_sensors = filter(s -> 
        s.sensorType == "WindSpeed" && 
        s.statType == "avg",
        ts.sensors
    )
    
    isempty(ws_sensors) && return nothing
    
    # Find sensor closest to target height
    closest = argmin(map(s -> abs(s.height - target_height), ws_sensors))
    ws_sensors[closest]
end
export find_target_mast_sensor

"""
Find target wind speed sensor closest to specified height in meso data
"""
function find_target_meso_sensor(ts::TimeSeriesData, target_height::Float64)::Union{SensorColumn, Nothing}
    # Filter for wind speed sensors with avg statType
    ws_sensors = filter(s -> 
        s.sensorType == "WindSpeed" && 
        s.statType == "avg",
        ts.sensors
    )
    
    isempty(ws_sensors) && return nothing
    
    # Find sensor closest to target height
    closest = argmin(map(s -> abs(s.height - target_height), ws_sensors))
    ws_sensors[closest]
end
export find_target_meso_sensor

"""
Calculate mean wind speed for a specific sensor
"""
function calculate_mean_speed(ts::TimeSeriesData, sensor::SensorColumn)::Float64
    mean(skipmissing(ts.df[!, sensor.columnName]))
end

"""
Determine if calibration is needed based on mean speed difference
"""
function is_calibration_needed(
    full_period_mean::Float64,
    training_period_mean::Float64;
    threshold::Float64=0.02
)::Bool
    abs(full_period_mean - training_period_mean) / full_period_mean > threshold
end

"""
Find direction sector for a given angle
"""
function find_direction_sector(angle::Float64)::Int
    # Normalize angle to 0-360
    norm_angle = mod(angle, 360.0)
    # Find sector (each sector is 22.5 degrees)
    sector = floor(Int, (norm_angle + 11.25) / 22.5) + 1
    # Handle edge case
    sector > 16 ? 1 : sector
end
export find_direction_sector

"""
Average time series to hourly resolution
"""
function average_to_hourly(ts::TimeSeriesData)::TimeSeriesData
    hourly_df = combine(
        groupby(ts.df, dt -> floor(dt.timestamp, Hour)),
        [
            sensor.columnName => 
                sensor.sensorType == "WindDirection" ? 
                    x -> circular_mean(collect(skipmissing(x))) :
                    mean∘skipmissing
            for sensor in ts.sensors
        ]...
    )
    rename!(hourly_df, :timestamp_floor => :timestamp)
    TimeSeriesData(hourly_df, ts.sensors)
end
export average_to_hourly

"""
Calculate circular mean for wind directions
"""
function circular_mean(angles::Vector{Float64})::Float64
    rad = deg2rad.(angles)
    mean_sin = mean(sin.(rad))
    mean_cos = mean(cos.(rad))
    mod(rad2deg(atan(mean_sin, mean_cos)), 360.0)
end
export circular_mean

"""
Find the latest representative year
"""
function find_representative_year(
    meso_ts::TimeSeriesData,
    full_period_mean::Float64;
    threshold::Float64=0.02
)::DateTime
    # Group by year and calculate mean speeds
    yearly_means = combine(
        groupby(meso_ts.df, dt -> floor(dt.timestamp, Year)),
        [sensor.columnName => mean∘skipmissing for sensor in meso_ts.sensors if sensor.sensorType == "WindSpeed" && sensor.statType == "avg"]...
    )
    rename!(yearly_means, :timestamp_floor => :year_start)
    
    # Find latest year within threshold
    for year_start in sort(yearly_means.year_start, rev=true)
        year_means = yearly_means[yearly_means.year_start .== year_start, :]
        if all(abs.(values(year_means[2:end]) .- full_period_mean) ./ full_period_mean .<= threshold)
            return year_start
        end
    end
    
    error("No representative year found within threshold")
end
export find_representative_year

"""
Calculate directional calibrations for a specific sensor
"""
function calculate_directional_calibrations(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    training_range::TrainingTimeRange,
    ref_year_start::DateTime,
    target_sensor::SensorColumn
)::Vector{DirectionalCalibration}
    # Average both to hourly
    hourly_mast = average_to_hourly(mast_ts)
    hourly_meso = average_to_hourly(meso_ts)
    
    map(DIRECTION_SECTORS) do sector
        # Filter data for this sector
        sector_data = filter_direction_sector(hourly_mast, hourly_meso, sector.center)
        
        # Calculate slope for this sector using target sensor
        slope = calculate_sector_slope(sector_data, target_sensor)
        
        # Calculate meso speed difference
        meso_diff = calculate_sector_meso_diff(
            hourly_meso, 
            training_range,
            ref_year_start,
            sector.center
        )
        
        DirectionalCalibration(sector.center, slope, meso_diff)
    end
end

"""
Apply calibration to time series
"""
function apply_calibration(
    ts::TimeSeriesData,
    calibration::CalibrationResults
)::TimeSeriesData
    if !calibration.is_calibration_needed
        return ts
    end
    
    result_df = copy(ts.df)
    
    # Apply calibration for each row
    for row in eachrow(result_df)
        # Find direction sector
        direction = get_primary_direction(row, ts.sensors)
        sector = find_direction_sector(direction)
        cal = calibration.directional_calibrations[sector]
        
        # Apply calibration only to target sensor
        if !ismissing(row[calibration.target_sensor.columnName])
            row[calibration.target_sensor.columnName] *= (1.0 + cal.meso_speed_diff * cal.slope)
        end
    end
    
    TimeSeriesData(result_df, ts.sensors)
end

"""
Filter data for a specific direction sector
"""
function filter_direction_sector(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    center::Float64
)::DataFrame
    # Get primary direction column from mast
    dir_sensor = first(filter(s -> s.sensorType == "WindDirection", mast_ts.sensors))
    
    # Filter data within ±11.25° of center
    lower = mod(center - 11.25, 360.0)
    upper = mod(center + 11.25, 360.0)
    
    # Join mast and meso data
    df = innerjoin(mast_ts.df, meso_ts.df, on=:timestamp)
    
    if lower > upper  # Handles case around 0/360
        filter(row -> 
            !ismissing(row[dir_sensor.columnName]) && 
            (row[dir_sensor.columnName] >= lower || row[dir_sensor.columnName] < upper),
            df)
    else
        filter(row -> 
            !ismissing(row[dir_sensor.columnName]) && 
            lower <= row[dir_sensor.columnName] < upper,
            df)
    end
end

"""
Calculate slope for a direction sector using linear regression
"""
function calculate_sector_slope(sector_data::DataFrame, target_sensor::SensorColumn)::Float64
    if nrow(sector_data) < 2
        return 1.0  # Default to no adjustment if insufficient data
    end
    
    # Get meso wind speed column (assumes it's the last ws_ column)
    meso_ws = last(names(sector_data, r"^ws_.*m$"))
    
    # Perform linear regression using target sensor
    # Use @eval to create the formula dynamically
    formula = @eval @formula($(Symbol(target_sensor.columnName)) ~ $(Symbol(meso_ws)))
    model = lm(formula, sector_data)
    coef(model)[2]  # Return slope
end

"""
Calculate mean speed difference between training range and reference year for a sector
"""
function calculate_sector_meso_diff(
    meso_ts::TimeSeriesData,
    training_range::TrainingTimeRange,
    ref_year_start::DateTime,
    center::Float64
)::Float64
    # Get wind speed sensor
    ws_sensor = first(filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", meso_ts.sensors))
    
    # Filter data for direction sector
    sector_data = filter_direction_sector(meso_ts, meso_ts, center)
    
    # Calculate means for training range and reference year
    training_mean = mean(skipmissing(
        sector_data[training_range.min .<= sector_data.timestamp .<= training_range.max, ws_sensor.columnName]
    ))
    
    ref_year_end = ref_year_start + Year(1) - Second(1)
    ref_year_mean = mean(skipmissing(
        sector_data[ref_year_start .<= sector_data.timestamp .<= ref_year_end, ws_sensor.columnName]
    ))
    
    # Return relative difference
    (ref_year_mean - training_mean) / training_mean
end

"""
Get primary wind direction from a row of data
"""
function get_primary_direction(row::DataFrameRow, sensors::Vector{SensorColumn})::Float64
    # Find highest wind direction sensor
    dir_sensors = filter(s -> s.sensorType == "WindDirection", sensors)
    primary_sensor = last(sort(dir_sensors, by=s -> s.height))
    
    # Return direction, defaulting to 0 if missing
    ismissing(row[primary_sensor.columnName]) ? 0.0 : row[primary_sensor.columnName]
end

export calculate_mean_speed, is_calibration_needed, find_representative_year,
       calculate_directional_calibrations, apply_calibration

end 