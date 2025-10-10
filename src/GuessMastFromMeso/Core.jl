module Core

using Dates
using DataFrames
using Statistics
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange, SensorColumn, TimeSeriesSource
using ...Types.GuessMastFromMesoConfig: GuessMastFromMesoConfiguration, GuessMastTarget
using ...RepresentativeYear.Utils: find_heighest_meso_sensor, calculate_mean_speed,
                                    filter_training_range

export guess_mast_from_meso

"""
    find_highest_direction_sensor(meso_ts::TimeSeriesData)::Union{SensorColumn, Nothing}

Find the highest available wind direction sensor in meso data.
"""
function find_highest_direction_sensor(meso_ts::TimeSeriesData)::Union{SensorColumn, Nothing}
    wd_sensors = filter(sensor -> sensor.statType == "avg" && sensor.sensorType == "WindDirection", meso_ts.sensors)
    if isempty(wd_sensors)
        return nothing
    end
    foldl(wd_sensors, init=first(wd_sensors)) do max_sensor, sensor
        if (sensor.height > max_sensor.height)
            sensor
        else
            max_sensor
        end
    end
end

"""
    find_direction_sensors_by_height(meso_ts::TimeSeriesData)::Vector{SensorColumn}

Find all wind direction sensors sorted by height (ascending).
"""
function find_direction_sensors_by_height(meso_ts::TimeSeriesData)::Vector{SensorColumn}
    wd_sensors = filter(sensor -> sensor.statType == "avg" && sensor.sensorType == "WindDirection", meso_ts.sensors)
    sort(wd_sensors, by = s -> s.height)
end

"""
    calculate_direction_veer(df::DataFrame, wd_low::SensorColumn, wd_high::SensorColumn)::Float64

Calculate mean directional veer (degrees) between two wind direction sensors.
Uses circular statistics to handle 0°/360° boundary correctly.
"""
function calculate_direction_veer(df::DataFrame, wd_low::SensorColumn, wd_high::SensorColumn)::Float64
    valid_pairs = filter(eachrow(df)) do row
        !ismissing(row[wd_low.columnName]) && !ismissing(row[wd_high.columnName])
    end

    if isempty(valid_pairs)
        return 0.0
    end

    veer_values = map(valid_pairs) do row
        diff = row[wd_high.columnName] - row[wd_low.columnName]
        mod(diff + 180, 360) - 180
    end

    return Statistics.mean(veer_values)
end

"""
    interpolate_wind_direction(
        base_sensor::SensorColumn,
        target_height::Float64,
        veer_per_meter::Float64,
        df::DataFrame
    )::Tuple{SensorColumn, Vector{Union{Missing, Float64}}}

Interpolate wind direction to target height using constant veer rate.
"""
function interpolate_wind_direction(
    base_sensor::SensorColumn,
    target_height::Float64,
    veer_per_meter::Float64,
    df::DataFrame
)::Tuple{SensorColumn, Vector{Union{Missing, Float64}}}
    col_name = Symbol("WindDirection_$(Int(round(target_height)))m_avg")

    height_diff = target_height - base_sensor.height
    interpolated_values = map(df[!, base_sensor.columnName]) do value
        if ismissing(value)
            return missing
        end
        veer_adjustment = veer_per_meter * height_diff
        adjusted = value + veer_adjustment
        mod(adjusted, 360)
    end

    new_sensor = SensorColumn(
        col_name,
        "WindDirection",
        base_sensor.sensorDirection,
        target_height,
        "avg",
        base_sensor.unit
    )

    return (new_sensor, interpolated_values)
end

"""
    create_scaled_sensor(base_sensor::SensorColumn, target_height::Float64, scale_factor::Float64, df::DataFrame)::Tuple{SensorColumn, Vector{Union{Missing, Float64}}}

Create a new wind speed sensor at target height with scaled values.
"""
function create_scaled_sensor(base_sensor::SensorColumn, target_height::Float64, scale_factor::Float64, df::DataFrame)::Tuple{SensorColumn, Vector{Union{Missing, Float64}}}
    col_name = Symbol("WindSpeed_$(Int(round(target_height)))m_avg")

    scaled_values = map(df[!, base_sensor.columnName]) do value
        ismissing(value) ? missing : value * scale_factor
    end

    new_sensor = SensorColumn(
        col_name,
        "WindSpeed",
        base_sensor.sensorDirection,
        target_height,
        "avg",
        base_sensor.unit
    )

    return (new_sensor, scaled_values)
end

"""
    guess_mast_from_meso(config::GuessMastFromMesoConfiguration, base_dir::String)::Nothing

Main function to generate synthetic mast data from mesoscale data.

# Arguments
- `config::GuessMastFromMesoConfiguration`: Configuration with meso source, output, and targets
- `base_dir::String`: Base directory for resolving relative paths

# Processing Steps
1. Load meso data from input source
2. Slice to representative year time range
3. Find highest wind speed and direction sensors
4. For each target height:
   - Calculate scaling factor based on target mean speed
   - Create new wind speed sensor with scaled values
5. Copy wind direction from highest meso sensor
6. Save output TimeSeriesData
"""
function guess_mast_from_meso(config::GuessMastFromMesoConfiguration, base_dir::String)::Nothing
    println("🔮 Generating synthetic mast data from mesoscale...")
    println("   Meso source: $(config.meso.name)")
    println("   Time range: $(config.meso.time_range.min) to $(config.meso.time_range.max)")

    meso_ts = load_timeseries(config.meso.input, base_dir)

    rep_year_ts = filter_training_range(meso_ts, config.meso.time_range)
    println("   Representative year data points: $(nrow(rep_year_ts.df))")

    highest_ws_sensor = find_heighest_meso_sensor(rep_year_ts)
    if isnothing(highest_ws_sensor)
        error("No wind speed sensor found in meso data")
    end
    println("   Using meso wind speed sensor: $(highest_ws_sensor.columnName) @ $(highest_ws_sensor.height)m")

    wd_sensors = find_direction_sensors_by_height(rep_year_ts)
    if isempty(wd_sensors)
        error("No wind direction sensor found in meso data")
    end

    veer_per_meter = 0.0
    reference_wd_sensor = last(wd_sensors)

    if length(wd_sensors) >= 2
        wd_low = first(wd_sensors)
        wd_high = last(wd_sensors)
        mean_veer = calculate_direction_veer(rep_year_ts.df, wd_low, wd_high)
        veer_per_meter = mean_veer / (wd_high.height - wd_low.height)
        println("   Found $(length(wd_sensors)) WD sensors: veer = $(round(mean_veer, digits=2))° over $(round(wd_high.height - wd_low.height, digits=1))m ($(round(veer_per_meter, digits=4))°/m)")
    else
        println("   Found 1 WD sensor @ $(reference_wd_sensor.height)m - no veer adjustment")
    end

    actual_mean = calculate_mean_speed(rep_year_ts, highest_ws_sensor)
    println("   Actual mean wind speed: $(round(actual_mean, digits=2)) m/s")

    result_df = DataFrame(timestamp = rep_year_ts.df.timestamp)
    result_sensors = Vector{SensorColumn}()

    for target in config.targets
        scale_factor = target.mean_speed / actual_mean
        println("   Creating WS @ $(target.height)m: mean=$(target.mean_speed) m/s, scale=$(round(scale_factor, digits=3))")

        ws_sensor, ws_values = create_scaled_sensor(highest_ws_sensor, target.height, scale_factor, rep_year_ts.df)
        result_df[!, ws_sensor.columnName] = ws_values
        push!(result_sensors, ws_sensor)

        wd_sensor, wd_values = interpolate_wind_direction(reference_wd_sensor, target.height, veer_per_meter, rep_year_ts.df)
        veer_adjustment = veer_per_meter * (target.height - reference_wd_sensor.height)
        println("   Creating WD @ $(target.height)m: veer adjustment = $(round(veer_adjustment, digits=2))°")
        result_df[!, wd_sensor.columnName] = wd_values
        push!(result_sensors, wd_sensor)
    end

    result_ts = TimeSeriesData(result_df, result_sensors)

    output_source = TimeSeriesSource(config.output.data, config.output.sensors)
    save_timeseries(output_source, base_dir, result_ts)

    println("✅ Synthetic mast data generated successfully")
    println("   Output: $(config.output.data)")
    println("   Sensors: $(length(result_sensors)) ($(length(config.targets)) WS + $(length(config.targets)) WD)")

    return nothing
end

using ...Types.MastTimeSeries: load_timeseries, save_timeseries

end
