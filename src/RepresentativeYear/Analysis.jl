module Analysis

using DataFrames
using Statistics
using Dates
using GLM
using ...Types.RepresentativeYear: CalibrationResults, CalibrationEachWSSensor, DirectionalCalibration
using ...Types.Sector: DIRECTION_16_SECTORS, abs_degree_diff
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, TimeRange
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel, SpeedPair

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
    # Create a copy of the DataFrame with hour floor column
    df = copy(ts.df)
    df.hour_floor = floor.(df.timestamp, Hour)
    
    # Group by hour floor and calculate means
    hourly_df = combine(
        groupby(df, :hour_floor),
        [
            sensor.columnName => 
                sensor.sensorType == "WindDirection" ? 
                    (x -> circular_mean(collect(skipmissing(x)))) => sensor.columnName :
                    mean∘skipmissing => sensor.columnName
            for sensor in ts.sensors
        ]...
    )
    
    # Rename hour_floor back to timestamp and sort
    rename!(hourly_df, :hour_floor => :timestamp)
    sort!(hourly_df, :timestamp)
    
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
Find the latest representative year, the return value is the year start date
"""
function find_representative_year(
    meso_ts::TimeSeriesData,
    full_period_mean::Float64,
    meso_sensor::SensorColumn;
    threshold::Float64=0.02
)::DateTime
    # Create a copy of DataFrame with year start column
    df = copy(meso_ts.df)
    df.year_start = floor.(df.timestamp, Year)
    
    # Group by year and calculate mean speed for the specific sensor
    yearly_means = combine(
        groupby(df, :year_start),
        meso_sensor.columnName => mean∘skipmissing => :mean_speed
    )
    
    # Find latest year within threshold
    for year_start in sort(yearly_means.year_start, rev=true)
        year_mean = yearly_means[yearly_means.year_start .== year_start, :mean_speed][1]
        if abs(year_mean - full_period_mean) / full_period_mean <= threshold
            return year_start
        end
    end
    
    error("No representative year found within threshold")
end
export find_representative_year

function filter_training_range(ts::TimeSeriesData, training_range::TimeRange)::TimeSeriesData
    df = ts.df[training_range.min .<= ts.df.timestamp .<= training_range.max, :]
    TimeSeriesData(df, ts.sensors)
end
export filter_training_range


"""
Apply calibration to time series with validation checks
"""
function apply_calibration(
    ts::TimeSeriesData,
    calibration::CalibrationResults,
    meso_ts:: TimeSeriesData;
    min_speed::Float64 = 0.5,
    max_speed::Float64 = 25.0
)::TimeSeriesData
    result_df = copy(ts.df)
    for calibration_each_ws_sensor in calibration.calibrations
        dir_col = calibration_each_ws_sensor.meso_direction_sensor.columnName
        target_col = calibration_each_ws_sensor.target_sensor.columnName
        for (i, row) in enumerate(eachrow(result_df))
            dir = meso_ts.df[i, dir_col]
            # Skip if original value is missing
            ismissing(row[target_col]) && continue
            ismissing(dir) && continue
            
            sector = find_direction_sector(dir)
            cal = calibration_each_ws_sensor.directional_calibrations[sector]
            original_value = row[target_col]
            calibrated_value = original_value + cal.meso_speed_diff * cal.slope
            if min_speed <= calibrated_value <= max_speed
                row[target_col] = calibrated_value
            end
        end
    end
    
    TimeSeriesData(result_df, ts.sensors)
end
export apply_calibration

"""
Find wind direction sensor closest to given wind speed sensor
"""
function find_matching_direction_sensor(
    ts::TimeSeriesData, 
    ws_sensor::SensorColumn
)::SensorColumn
    dir_sensors = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", ts.sensors)
    isempty(dir_sensors) && error("No wind direction sensors found in data")
    
    # Find direction sensor with height closest to wind speed sensor
    closest = argmin(map(s -> abs(s.height - ws_sensor.height), dir_sensors))
    dir_sensors[closest]
end

"""
Filter data for a specific direction sector
"""
function filter_direction_sector(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    center::Float64,
    mast_ws_sensor::SensorColumn
)::DataFrame
    # Get direction sensor closest to wind speed sensor height
    dir_sensor = find_matching_direction_sensor(mast_ts, mast_ws_sensor)
    
    # Join mast and meso data
    df = innerjoin(mast_ts.df, meso_ts.df, on=:timestamp)
    
    # Add circular difference column
    df.dir_diff = map(row -> 
        ismissing(row[dir_sensor.columnName]) ? Inf : 
        abs_degree_diff(row[dir_sensor.columnName], center),
        eachrow(df))
    
    # Filter rows within ±11.25° of center
    filter(row -> row.dir_diff <= 11.25, df)
end

"""
Calculate slope for a direction sector using linear regression
"""
function calculate_sector_slope(
    sector_data::DataFrame, 
    mast_sensor::SensorColumn,
    meso_sensor::SensorColumn
)::Float64
    if nrow(sector_data) < 2
        return 1.0  # Default to no adjustment if insufficient data
    end
    # Create formula using both sensor column names
    formula = @eval @formula($(Symbol(mast_sensor.columnName)) ~ $(Symbol(meso_sensor.columnName)))
    model = lm(formula, sector_data)
    coef(model)[2]  # Return slope
end

"""
Calculate mean speed for a direction sector
"""
function calculate_sector_meso_mean(meso_ts::TimeSeriesData, speed_sensor::SensorColumn)::DataFrame
    df = copy(meso_ts.df)

    dir_sensor = find_matching_direction_sensor(meso_ts, speed_sensor)
    # Map each direction to its sector number and then to sector name
    df.sector = map(eachrow(df)) do row
        sector_idx = find_direction_sector(row[dir_sensor.columnName])
        DIRECTION_16_SECTORS[sector_idx].name
    end
    
    # Group by sector name and calculate mean
    sector_df = combine(groupby(df, :sector), speed_sensor.columnName => mean∘skipmissing => :mean_speed)
    sort!(sector_df, :sector)  # Sort by sector name for consistency
    sector_df
end

"""
Calculate mean speed difference between training range and reference year for a sector
"""
function calculate_sector_meso_diff(
    meso_ts::TimeSeriesData,
    training_range::TimeRange,
    ref_year_start::DateTime,
    meso_sensor::SensorColumn
)::DataFrame
    meso_training_ts = filter_training_range(meso_ts, training_range)
    meso_ref_year_ts = filter_training_range(meso_ts, TimeRange(ref_year_start, ref_year_start + Year(1) - Second(1)))
    
    meso_training_sector_df = calculate_sector_meso_mean(meso_training_ts, meso_sensor)
    meso_ref_year_sector_df = calculate_sector_meso_mean(meso_ref_year_ts, meso_sensor)
    
    # Rename columns before joining
    rename!(meso_training_sector_df, :mean_speed => :training_mean_speed)
    rename!(meso_ref_year_sector_df, :mean_speed => :ref_year_mean_speed)
    
    # Join and calculate difference
    result_df = innerjoin(meso_training_sector_df, meso_ref_year_sector_df, on=:sector)
    result_df.meso_speed_diff = result_df.ref_year_mean_speed .- result_df.training_mean_speed
    
    result_df
end

function calculate_calibration_each_ws_sensor(
    sector_meso_diff_df::DataFrame,
    pair:: SpeedPair
):: CalibrationEachWSSensor
   directional_calibrations = map(pair.sectors) do sector
    meso_speed_diff = first(filter(row -> row.sector == sector.direction_sector.name, sector_meso_diff_df).meso_speed_diff)
    DirectionalCalibration(sector.direction_sector, sector.slope, meso_speed_diff)
   end

   return CalibrationEachWSSensor(
    pair.mast_speed_sensor,
    pair.meso_direction_sensor,
    directional_calibrations
   )
end


export calculate_mean_speed, is_calibration_needed, find_representative_year,
       apply_calibration, calculate_sector_meso_diff, calculate_calibration_each_ws_sensor

end 