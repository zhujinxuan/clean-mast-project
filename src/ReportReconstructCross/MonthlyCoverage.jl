"""
Monthly Data Coverage Table Generation for Cross-Mast Report

This module generates monthly wind speed sensor data coverage tables showing:
- Monthly data completeness for each wind speed sensor
- Coverage statistics for each mast in the cross-mast analysis
"""

module MonthlyCoverage

using DataFrames
using Dates
using Statistics
using StatsBase: mode
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn

export generate_monthly_coverage_tables

"""
    get_wind_speed_sensors(data::TimeSeriesData)

Extract unique wind speed sensors with statType = 'avg' from time series data.
Returns a sorted vector of sensors (sorted by height descending, then direction).
"""
function get_wind_speed_sensors(data::TimeSeriesData)::Vector{SensorColumn}
    wind_speed_sensors = filter(
        sensor -> sensor.sensorType == "WindSpeed" && sensor.statType == "avg",
        data.sensors
    )

    unique_sensors = Dict{Tuple{Float64, String}, SensorColumn}()
    for sensor in wind_speed_sensors
        key = (sensor.height, sensor.sensorDirection)
        if !haskey(unique_sensors, key)
            unique_sensors[key] = sensor
        end
    end

    sensors = collect(values(unique_sensors))
    sort!(sensors, by = s -> (s.height, s.sensorDirection), rev=true)

    return sensors
end

"""
    create_sensor_header(sensors::Vector{SensorColumn})

Create column headers for wind speed sensors.
If multiple sensors exist at the same height, use {height}m_{direction} format.
Otherwise, use {height}m format.
"""
function create_sensor_header(sensors::Vector{SensorColumn})::Vector{String}
    height_counts = Dict{Float64, Int}()
    for sensor in sensors
        height_counts[sensor.height] = get(height_counts, sensor.height, 0) + 1
    end

    headers = String[]
    for sensor in sensors
        height_str = sensor.height == floor(sensor.height) ?
            string(Int(sensor.height)) : string(sensor.height)

        if height_counts[sensor.height] > 1
            direction_str = sensor.sensorDirection == "N/A" ? "" : "_$(sensor.sensorDirection)"
            push!(headers, "$(height_str)m$(direction_str)")
        else
            push!(headers, "$(height_str)m")
        end
    end

    return headers
end

"""
    detect_representative_interval(data::TimeSeriesData)

Detect the representative time interval from the data.
Returns interval in minutes.
"""
function detect_representative_interval(data::TimeSeriesData)::Int
    timestamps = sort(unique(filter(!ismissing, data.df.timestamp)))
    if length(timestamps) < 2
        return 10  # Default to 10 minutes
    end

    diffs = diff(timestamps)
    common_diff = mode([Dates.value(d) ÷ 60000 for d in diffs])  # Convert to minutes

    return Int(common_diff)
end

"""
    calculate_monthly_coverage(
        data::TimeSeriesData,
        sensors::Vector{SensorColumn},
        representative_interval::Int
    )

Calculate monthly coverage statistics for each wind speed sensor.
Returns a vector of NamedTuples with month and coverage data.
"""
function calculate_monthly_coverage(
    data::TimeSeriesData,
    sensors::Vector{SensorColumn},
    representative_interval::Int
)::Vector{NamedTuple}

    timestamps = sort(unique(filter(!ismissing, data.df.timestamp)))
    if isempty(timestamps)
        return NamedTuple[]
    end

    time_start = minimum(timestamps)
    time_end = maximum(timestamps)

    current_month = Date(year(time_start), month(time_start), 1)
    end_month = Date(year(time_end), month(time_end), 1)

    monthly_stats = NamedTuple[]

    while current_month <= end_month
        month_start = DateTime(current_month)
        next_month = current_month + Month(1)
        month_end = DateTime(next_month) - Millisecond(1)

        days_in_month = Dates.daysinmonth(current_month)
        expected_points = Int(ceil((days_in_month * 24 * 60) / representative_interval))

        sensor_coverages = map(sensors) do sensor
            sensor_col = sensor.columnName

            month_mask = (data.df.timestamp .>= month_start) .&
                        (data.df.timestamp .<= month_end)

            valid_count = count(!ismissing, data.df[month_mask, sensor_col])

            completeness = expected_points > 0 ?
                round((valid_count / expected_points) * 100, digits=2) : 0.0

            completeness
        end

        month_data = (
            year = year(current_month),
            month = month(current_month),
            coverages = sensor_coverages
        )

        push!(monthly_stats, month_data)
        current_month = next_month
    end

    return monthly_stats
end

"""
    generate_monthly_coverage_tables(mast_data::Dict{String, TimeSeriesData})

Generate monthly wind speed sensor coverage tables for all masts in Typst format.
Shows coverage for each month with columns for each wind speed sensor.

# Arguments
- `mast_data::Dict{String, TimeSeriesData}`: Dictionary mapping mast names to their time series data

# Returns
- `String`: Typst-formatted table sections for all masts
"""
function generate_monthly_coverage_tables(mast_data::Dict{String, TimeSeriesData})::String
    if isempty(mast_data)
        return "== 测风塔风速数据月度统计表\\n\\n未找到测风塔数据。\\n"
    end

    sections = String[
        "== 测风塔风速数据月度统计表",
        "",
        "本节列出各测风塔风速传感器的月度数据统计。表格显示每个传感器的数据完整率（%）。",
        ""
    ]

    for (mast_name, time_series) in sort(collect(mast_data))
        push!(sections, "=== $(mast_name)")
        push!(sections, "")

        wind_sensors = get_wind_speed_sensors(time_series)

        if isempty(wind_sensors)
            push!(sections, "未找到风速传感器数据。")
            push!(sections, "")
            continue
        end

        headers = create_sensor_header(wind_sensors)
        representative_interval = detect_representative_interval(time_series)
        monthly_stats = calculate_monthly_coverage(time_series, wind_sensors, representative_interval)

        if isempty(monthly_stats)
            push!(sections, "未找到数据。")
            push!(sections, "")
            continue
        end

        num_sensors = length(wind_sensors)
        num_columns = 2 + num_sensors  # year, month, + sensors

        push!(sections, "#table(")
        push!(sections, "  columns: $(num_columns),")

        header_line = "  [年份], [月份], " *
            join(["[$(h)]" for h in headers], ", ") * ","
        push!(sections, header_line)

        for month_data in monthly_stats
            sensor_values = [string(cov) for cov in month_data.coverages]

            row_line = "  [$(month_data.year)], [$(month_data.month)], " *
                join(["[$v]" for v in sensor_values], ", ") * ","

            push!(sections, row_line)
        end

        push!(sections, ")")
        push!(sections, "")
    end

    return join(sections, "\n")
end

end # module MonthlyCoverage
