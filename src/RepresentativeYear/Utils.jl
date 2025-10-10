module Utils

using DataFrames
using Statistics
using Dates
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, TimeRange

export calculate_mean_speed, calculate_climatology_mean, find_climatology_timerange,
       is_calibration_needed, find_representative_year,
       filter_training_range, find_target_mast_sensor, find_target_meso_sensor,
       find_heighest_meso_sensor

"""
    calculate_mean_speed(ts::TimeSeriesData, sensor::SensorColumn)::Float64

Calculate mean wind speed for a specific sensor.
"""
function calculate_mean_speed(ts::TimeSeriesData, sensor::SensorColumn)::Float64
    mean(skipmissing(ts.df[!, sensor.columnName]))
end

"""
    find_climatology_timerange(min_timestamp::DateTime, max_timestamp::DateTime)::TimeRange

Find the climatology time range using only complete years.

# Logic
1. If min_timestamp - Day(1) has same year as min_timestamp, start from next year Jan 1
2. If max_timestamp + Day(1) has same year as max_timestamp, end at previous year Dec 31
3. If difference > 30 years, adjust start year to make difference ≤ 30 years
"""
function find_climatology_timerange(min_timestamp::DateTime, max_timestamp::DateTime)::TimeRange
    min_year = year(min_timestamp)
    max_year = year(max_timestamp)

    start_year = if year(min_timestamp - Day(1)) == min_year
        min_year + 1
    else
        min_year
    end

    end_year = if year(max_timestamp + Day(1)) == max_year
        max_year - 1
    else
        max_year
    end

    if end_year < start_year
        error("No complete years found in dataset. Time range: $min_timestamp to $max_timestamp")
    end

    year_diff = end_year - start_year + 1
    if year_diff > 30
        start_year = end_year - 29
    end

    climatology_start = DateTime(start_year, 1, 1, 0, 0, 0)
    climatology_end = DateTime(end_year, 12, 31, 23, 59, 59)

    return TimeRange(climatology_start, climatology_end)
end

"""
    calculate_climatology_mean(ts::TimeSeriesData, sensor::SensorColumn)::Float64

Calculate climatology mean using only complete years (Jan 1 - Dec 31).
Partial years at the beginning or end of the dataset are excluded to avoid seasonal bias.
Uses at most 30 years of data if dataset is longer.
"""
function calculate_climatology_mean(ts::TimeSeriesData, sensor::SensorColumn)::Float64
    df = ts.df
    min_timestamp = minimum(df.timestamp)
    max_timestamp = maximum(df.timestamp)

    climatology_range = find_climatology_timerange(min_timestamp, max_timestamp)

    complete_years_df = filter(row ->
        climatology_range.min <= row.timestamp <= climatology_range.max,
        df
    )

    return mean(skipmissing(complete_years_df[!, sensor.columnName]))
end

"""
    is_calibration_needed(
        full_period_mean::Float64,
        training_period_mean::Float64;
        threshold::Float64=0.02
    )::Bool

Determine if calibration is needed based on mean speed difference.
Returns true if the absolute difference exceeds the threshold (default 2%).
"""
function is_calibration_needed(
    full_period_mean::Float64,
    training_period_mean::Float64;
    threshold::Float64=0.02
)::Bool
    abs(full_period_mean - training_period_mean) / full_period_mean > threshold
end

"""
    find_representative_year(
        meso_ts::TimeSeriesData,
        full_period_mean::Float64,
        meso_sensor::SensorColumn;
        threshold::Float64=0.02
    )::DateTime

Find the latest representative year, the return value is the year start date.

A representative year is defined as the latest complete year (Jan 1 - Dec 31)
where the annual mean wind speed differs from the climatology mean by less than
the threshold (default 2%).
"""
function find_representative_year(
    meso_ts::TimeSeriesData,
    full_period_mean::Float64,
    meso_sensor::SensorColumn;
    threshold::Float64=0.02
)::DateTime
    df = copy(meso_ts.df)
    df.year_start = floor.(df.timestamp, Year)

    yearly_means = combine(
        groupby(df, :year_start),
        meso_sensor.columnName => mean∘skipmissing => :mean_speed
    )

    for year_start in sort(yearly_means.year_start, rev=true)
        year_mean = yearly_means[yearly_means.year_start .== year_start, :mean_speed][1]
        if abs(year_mean - full_period_mean) / full_period_mean <= threshold
            return year_start
        end
    end

    error("No representative year found within threshold")
end

"""
    filter_training_range(ts::TimeSeriesData, training_range::TimeRange)::TimeSeriesData

Filter time series data to only include timestamps within the specified time range.
"""
function filter_training_range(ts::TimeSeriesData, training_range::TimeRange)::TimeSeriesData
    df = ts.df[training_range.min .<= ts.df.timestamp .<= training_range.max, :]
    TimeSeriesData(df, ts.sensors)
end

"""
    find_target_mast_sensor(ts::TimeSeriesData, target_height::Float64)::Union{SensorColumn, Nothing}

Find target wind speed sensor closest to specified height in mast data.
"""
function find_target_mast_sensor(ts::TimeSeriesData, target_height::Float64)::Union{SensorColumn, Nothing}
    ws_sensors = filter(s ->
        s.sensorType == "WindSpeed" &&
        s.statType == "avg",
        ts.sensors
    )

    isempty(ws_sensors) && return nothing

    closest = argmin(map(s -> abs(s.height - target_height), ws_sensors))
    ws_sensors[closest]
end

"""
    find_target_meso_sensor(ts::TimeSeriesData, target_height::Float64)::Union{SensorColumn, Nothing}

Find target wind speed sensor closest to specified height in meso data.
"""
function find_target_meso_sensor(ts::TimeSeriesData, target_height::Float64)::Union{SensorColumn, Nothing}
    ws_sensors = filter(s ->
        s.sensorType == "WindSpeed" &&
        s.statType == "avg",
        ts.sensors
    )

    isempty(ws_sensors) && return nothing

    closest = argmin(map(s -> abs(s.height - target_height), ws_sensors))
    ws_sensors[closest]
end

"""
    find_heighest_meso_sensor(meso_ts::TimeSeriesData)::Union{SensorColumn, Nothing}

Find the highest available wind speed sensor in meso data.
"""
function find_heighest_meso_sensor(meso_ts::TimeSeriesData)::Union{SensorColumn, Nothing}
    avg_wind_speed_sensors = filter(sensor -> sensor.statType == "avg" && sensor.sensorType == "WindSpeed", meso_ts.sensors)
    if isempty(avg_wind_speed_sensors)
        return nothing
    end
    foldl(avg_wind_speed_sensors, init=first(avg_wind_speed_sensors)) do max_sensor, sensor
        if (sensor.height > max_sensor.height)
            sensor
        else
            max_sensor
        end
    end
end

end
