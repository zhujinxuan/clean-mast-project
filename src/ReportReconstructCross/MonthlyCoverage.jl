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

export generate_monthly_coverage_tables, calculate_monthly_coverage_with_before

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
    calculate_monthly_coverage_with_before(
        before_data::TimeSeriesData,
        after_data::TimeSeriesData,
        sensors::Vector{SensorColumn},
        representative_interval::Int
    )

Calculate monthly coverage statistics comparing before and after reconstruction.
Returns a vector of NamedTuples with month, coverage data, and before/after overall completeness.
"""
function calculate_monthly_coverage_with_before(
    before_data::TimeSeriesData,
    after_data::TimeSeriesData,
    sensors::Vector{SensorColumn},
    representative_interval::Int
)::Vector{NamedTuple}

    # Get all timestamps
    before_timestamps = sort(unique(filter(!ismissing, before_data.df.timestamp)))
    after_timestamps = sort(unique(filter(!ismissing, after_data.df.timestamp)))

    all_timestamps = sort(unique(vcat(before_timestamps, after_timestamps)))
    if isempty(all_timestamps)
        return NamedTuple[]
    end

    time_start = minimum(all_timestamps)
    time_end = maximum(all_timestamps)

    current_month = Date(year(time_start), month(time_start), 1)
    end_month = Date(year(time_end), month(time_end), 1)

    monthly_stats = NamedTuple[]

    while current_month <= end_month
        month_start = DateTime(current_month)
        next_month = current_month + Month(1)
        month_end = DateTime(next_month) - Millisecond(1)

        days_in_month = Dates.daysinmonth(current_month)
        expected_points = Int(ceil((days_in_month * 24 * 60) / representative_interval))

        # Calculate coverage for each sensor
        sensor_coverages = map(sensors) do sensor
            sensor_col = sensor.columnName

            # Before data
            month_mask_before = (before_data.df.timestamp .>= month_start) .&
                               (before_data.df.timestamp .<= month_end)
            before_valid = count(!ismissing, before_data.df[month_mask_before, sensor_col])
            before_completeness = expected_points > 0 ?
                round((before_valid / expected_points) * 100, digits=2) : 0.0

            # After data
            month_mask_after = (after_data.df.timestamp .>= month_start) .&
                              (after_data.df.timestamp .<= month_end)
            after_valid = count(!ismissing, after_data.df[month_mask_after, sensor_col])
            after_completeness = expected_points > 0 ?
                round((after_valid / expected_points) * 100, digits=2) : 0.0

            (
                before_completeness = before_completeness,
                after_completeness = after_completeness
            )
        end

        # Calculate overall averages
        before_completeness_values = [cov.before_completeness for cov in sensor_coverages]
        overall_before = !isempty(before_completeness_values) ?
            round(mean(before_completeness_values), digits=2) : 0.0

        after_completeness_values = [cov.after_completeness for cov in sensor_coverages]
        overall_after = !isempty(after_completeness_values) ?
            round(mean(after_completeness_values), digits=2) : 0.0

        month_data = (
            year = year(current_month),
            month = month(current_month),
            coverages = sensor_coverages,
            overall_before = overall_before,
            overall_after = overall_after
        )

        push!(monthly_stats, month_data)
        current_month = next_month
    end

    return monthly_stats
end

"""
    generate_monthly_coverage_tables(mast_data_with_before::Dict{String, @NamedTuple{data::TimeSeriesData, before_data::TimeSeriesData}})

Generate monthly wind speed sensor coverage tables with before/after comparison for all masts in Typst format.
Shows coverage for each month with columns for each wind speed sensor plus overall before/after completeness.

# Arguments
- `mast_data_with_before::Dict{String, @NamedTuple{data::TimeSeriesData, before_data::TimeSeriesData}}`: Dictionary mapping mast names to NamedTuples with data and before_data fields

# Returns
- `String`: Typst-formatted table sections for all masts
"""
function generate_monthly_coverage_tables(mast_data_with_before::Dict{String, @NamedTuple{data::TimeSeriesData, before_data::TimeSeriesData}})::String
    if isempty(mast_data_with_before)
        return "== 测风塔风速数据月度统计表\\n\\n未找到测风塔数据。\\n"
    end

    sections = String[
        "== 测风塔风速数据月度统计表",
        "",
        "本节列出各测风塔风速传感器的月度数据统计。表格显示每个传感器的数据完整率（%）。",
        ""
    ]

    for (mast_name, data_tuple) in sort(collect(mast_data_with_before), by = first)
        push!(sections, "=== $(mast_name)")
        push!(sections, "")

        after_data = data_tuple.data
        before_data = data_tuple.before_data

        wind_sensors = get_wind_speed_sensors(after_data)

        if isempty(wind_sensors)
            push!(sections, "未找到风速传感器数据。")
            push!(sections, "")
            continue
        end

        headers = create_sensor_header(wind_sensors)
        representative_interval = detect_representative_interval(after_data)

        # Use new function that handles before/after
        monthly_stats = calculate_monthly_coverage_with_before(
            before_data, after_data, wind_sensors, representative_interval
        )

        if isempty(monthly_stats)
            push!(sections, "未找到数据。")
            push!(sections, "")
            continue
        end

        num_sensors = length(wind_sensors)
        num_columns = 2 + num_sensors + 2  # year, month, sensors, before_overall, after_overall

        push!(sections, "#table(")
        push!(sections, "  columns: $(num_columns),")

        # Header with before/after columns
        header_line = "  [年份], [月份], " *
            join(["[$(h)]" for h in headers], ", ") *
            ", [重构前数据完整率], [重构后数据完整率],"
        push!(sections, header_line)

        # Rows with per-sensor after_completeness and overall before/after
        for month_data in monthly_stats
            sensor_values = [string(cov.after_completeness) for cov in month_data.coverages]

            row_line = "  [$(month_data.year)], [$(month_data.month)], " *
                join(["[$v]" for v in sensor_values], ", ") *
                ", [$(month_data.overall_before)], [$(month_data.overall_after)],"

            push!(sections, row_line)
        end

        push!(sections, ")")
        push!(sections, "")
    end

    return join(sections, "\n")
end

end # module MonthlyCoverage
