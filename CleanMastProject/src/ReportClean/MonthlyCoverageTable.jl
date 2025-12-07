"""
Monthly Coverage Table Generation Module

This module generates monthly wind speed sensor coverage tables showing:
- Monthly data coverage for each wind speed sensor
- Comparison between raw and clean data coverage
- Proper handling of multiple sensors at the same height
"""

module MonthlyCoverageTable

using DataFrames
using Dates
using Statistics
using ....Types.ReportCleanData: MastReportData, DetectedInterval
using ....Types.SensorColumns: SensorColumn

export generate_monthly_coverage_table

"""
    get_wind_speed_sensors(mast::MastReportData)

Extract unique wind speed sensors with statType = 'avg' from mast data.
Returns a sorted vector of sensors (sorted by height, then direction).
"""
function get_wind_speed_sensors(mast::MastReportData)::Vector{SensorColumn}
    wind_speed_sensors = filter(
        sensor -> sensor.sensorType == "WindSpeed" && sensor.statType == "avg",
        mast.raw_data.sensors
    )

    unique_sensors = Dict{Tuple{Float64, String}, SensorColumn}()
    for sensor in wind_speed_sensors
        key = (sensor.height, sensor.sensorDirection)
        if !haskey(unique_sensors, key)
            unique_sensors[key] = sensor
        end
    end

    sensors = collect(values(unique_sensors))
    sort!(sensors, by = s -> (s.height, s.sensorDirection))

    return sensors
end

"""
    create_sensor_header(sensors::Vector{SensorColumn})

Create column headers for wind speed sensors.
If multiple sensors exist at the same height, use {height}m:{direction} format.
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
            direction_str = sensor.sensorDirection == "N/A" ? "" : ":$(sensor.sensorDirection)"
            push!(headers, "$(height_str)m$(direction_str)")
        else
            push!(headers, "$(height_str)m")
        end
    end

    return headers
end

"""
    calculate_monthly_stats(
        mast::MastReportData,
        sensors::Vector{SensorColumn},
        representative_interval::DetectedInterval
    )

Calculate monthly coverage statistics for each wind speed sensor.
Returns a vector of NamedTuples with month and three metrics:
- missing_ratio: 缺测数据比例 (missing data ratio from raw)
- unreasonable_ratio: 不合理数据比例 (unreasonable data ratio = raw_valid - clean_valid)
- valid_completeness: 有效数据完整率 (valid data completeness rate from clean)
"""
function calculate_monthly_stats(
    mast::MastReportData,
    sensors::Vector{SensorColumn},
    representative_interval::DetectedInterval
)::Vector{NamedTuple}

    raw_timestamps = sort(unique(filter(!ismissing, mast.raw_data.df.timestamp)))
    time_start = minimum(raw_timestamps)
    time_end = maximum(raw_timestamps)

    current_month = Date(year(time_start), month(time_start), 1)
    end_month = Date(year(time_end), month(time_end), 1)

    monthly_stats = NamedTuple[]

    while current_month <= end_month
        month_start = DateTime(current_month)
        next_month = current_month + Month(1)
        month_end = DateTime(next_month) - Millisecond(1)

        days_in_month = Dates.daysinmonth(current_month)
        interval_minutes = representative_interval.interval.value
        expected_points = Int(ceil((days_in_month * 24 * 60) / interval_minutes))

        sensor_coverages = map(sensors) do sensor
            sensor_col = sensor.columnName

            month_mask_raw = (mast.raw_data.df.timestamp .>= month_start) .&
                            (mast.raw_data.df.timestamp .<= month_end)
            month_mask_clean = (mast.clean_data.df.timestamp .>= month_start) .&
                              (mast.clean_data.df.timestamp .<= month_end)

            raw_valid = count(!ismissing, mast.raw_data.df[month_mask_raw, sensor_col])
            clean_valid = count(!ismissing, mast.clean_data.df[month_mask_clean, sensor_col])

            missing_ratio = expected_points > 0 ?
                round(((expected_points - raw_valid) / expected_points) * 100, digits=2) : 0.0

            unreasonable_ratio = expected_points > 0 ?
                round(((raw_valid - clean_valid) / expected_points) * 100, digits=2) : 0.0

            valid_completeness = expected_points > 0 ?
                round((clean_valid / expected_points) * 100, digits=2) : 0.0

            (
                missing_ratio = missing_ratio,
                unreasonable_ratio = unreasonable_ratio,
                valid_completeness = valid_completeness
            )
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
    generate_monthly_coverage_table(mast_data::Vector{MastReportData})

Generate monthly wind speed sensor coverage table in Typst format.
Shows coverage for each month with columns for each wind speed sensor.
Last three columns show:
- 缺测数据比例 (missing data ratio)
- 不合理数据比例 (unreasonable data ratio)
- 有效数据完整率(%) (valid data completeness rate)
"""
function generate_monthly_coverage_table(mast_data::Vector{MastReportData})::String
    if isempty(mast_data)
        return "== 测风塔实测风速初步统计表\n\n未找到测风塔数据。\n"
    end

    sections = String[
        "== 测风塔实测风速初步统计表",
        "",
        "本节列出各测风塔风速传感器的月度数据统计。表格显示每个传感器的有效数据完整率，以及最后三列分别显示缺测数据比例、不合理数据比例和有效数据完整率。",
        ""
    ]

    for mast in mast_data
        push!(sections, "=== $(mast.name)")
        push!(sections, "")

        wind_sensors = get_wind_speed_sensors(mast)

        if isempty(wind_sensors)
            push!(sections, "未找到风速传感器数据。")
            push!(sections, "")
            continue
        end

        headers = create_sensor_header(wind_sensors)
        monthly_stats = calculate_monthly_stats(mast, wind_sensors, mast.detected_interval)

        num_sensors = length(wind_sensors)
        num_columns = 2 + num_sensors + 3

        push!(sections, "#table(")
        push!(sections, "  columns: $(num_columns),")

        header_line = "  [年份], [月份], " *
            join(["[$(h)]" for h in headers], ", ") *
            ", [缺测数据比例], [不合理数据比例], [有效数据完整率 (%)],\n"
        push!(sections, header_line)

        for month_data in monthly_stats
            sensor_values = [string(cov.valid_completeness) for cov in month_data.coverages]

            missing_ratios = [cov.missing_ratio for cov in month_data.coverages]
            unreasonable_ratios = [cov.unreasonable_ratio for cov in month_data.coverages]
            valid_completeness = [cov.valid_completeness for cov in month_data.coverages]

            overall_missing = !isempty(missing_ratios) ?
                round(mean(missing_ratios), digits=2) : 0.0
            overall_unreasonable = !isempty(unreasonable_ratios) ?
                round(mean(unreasonable_ratios), digits=2) : 0.0
            overall_valid = !isempty(valid_completeness) ?
                round(mean(valid_completeness), digits=2) : 0.0

            row_line = "  [$(month_data.year)], [$(month_data.month)], " *
                join(["[$v]" for v in sensor_values], ", ") *
                ", [$(overall_missing)%], [$(overall_unreasonable)%], [$(overall_valid)],"

            push!(sections, row_line)
        end

        push!(sections, ")")
        push!(sections, "")
    end

    return join(sections, "\n")
end

end # module MonthlyCoverageTable
