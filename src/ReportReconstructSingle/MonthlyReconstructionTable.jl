"""
Monthly Reconstruction Coverage Table Generation Module

This module generates monthly wind speed sensor reconstruction coverage tables showing:
- Monthly data completeness for each wind speed sensor after reconstruction
- Comparison between before and after reconstruction coverage
- Proper handling of multiple sensors at the same height
"""

module MonthlyReconstructionTable

using DataFrames
using Dates
using Statistics
using StatsBase: mode
using ....Types.ReportReconstructSingleConfiguration: ProcessedMastReconstructConfig
using ....Types.SensorColumns: SensorColumn
using ....Types.MastTimeSeries: TimeSeriesData

export generate_monthly_reconstruction_table

"""
    get_wind_speed_sensors(data::TimeSeriesData)

Extract unique wind speed sensors with statType = 'avg' from time series data.
Returns a sorted vector of sensors (sorted by height, then direction).
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
    calculate_monthly_reconstruction_stats(
        mast::ProcessedMastReconstructConfig,
        sensors::Vector{SensorColumn},
        representative_interval::Int
    )

Calculate monthly reconstruction statistics for each wind speed sensor.
Returns a vector of NamedTuples with month and coverage data for before and after reconstruction.
"""
function calculate_monthly_reconstruction_stats(
    mast::ProcessedMastReconstructConfig,
    sensors::Vector{SensorColumn},
    representative_interval::Int
)::Vector{NamedTuple}

    before_timestamps = sort(unique(filter(!ismissing, mast.beforeData.df.timestamp)))
    after_timestamps = sort(unique(filter(!ismissing, mast.afterData.df.timestamp)))

    all_timestamps = sort(unique(vcat(before_timestamps, after_timestamps)))
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

        sensor_coverages = map(sensors) do sensor
            sensor_col = sensor.columnName

            month_mask_before = (mast.beforeData.df.timestamp .>= month_start) .&
                               (mast.beforeData.df.timestamp .<= month_end)
            month_mask_after = (mast.afterData.df.timestamp .>= month_start) .&
                              (mast.afterData.df.timestamp .<= month_end)

            before_valid = count(!ismissing, mast.beforeData.df[month_mask_before, sensor_col])
            after_valid = count(!ismissing, mast.afterData.df[month_mask_after, sensor_col])

            before_completeness = expected_points > 0 ?
                round((before_valid / expected_points) * 100, digits=2) : 0.0
            after_completeness = expected_points > 0 ?
                round((after_valid / expected_points) * 100, digits=2) : 0.0

            (
                before_completeness = before_completeness,
                after_completeness = after_completeness
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
    generate_monthly_reconstruction_table(masts::Vector{ProcessedMastReconstructConfig})

Generate monthly wind speed sensor reconstruction coverage table in Typst format.
Shows coverage for each month with columns for each wind speed sensor.
Last two columns show overall before and after reconstruction completeness rates.
"""
function generate_monthly_reconstruction_table(masts::Vector{ProcessedMastReconstructConfig})::String
    if isempty(masts)
        return "== 测风塔实测风速重构月度统计表\n\n未找到测风塔数据。\n"
    end

    sections = String[
        "== 测风塔实测风速重构月度统计表",
        "",
        "本节列出各测风塔风速传感器的月度重构数据统计。表格显示每个传感器重构后的数据完整率，以及最后两列分别显示重构前和重构后的整体数据完整率。",
        ""
    ]

    for mast in masts
        push!(sections, "=== $(mast.name)")
        push!(sections, "")

        wind_sensors = get_wind_speed_sensors(mast.afterData)

        if isempty(wind_sensors)
            push!(sections, "未找到风速传感器数据。")
            push!(sections, "")
            continue
        end

        headers = create_sensor_header(wind_sensors)
        representative_interval = detect_representative_interval(mast.afterData)
        monthly_stats = calculate_monthly_reconstruction_stats(mast, wind_sensors, representative_interval)

        num_sensors = length(wind_sensors)
        num_columns = 2 + num_sensors + 2

        push!(sections, "#table(")
        push!(sections, "  columns: $(num_columns),")

        header_line = "  [年份], [月份], " *
            join(["[$(h)]" for h in headers], ", ") *
            ", [重构前数据完整率], [重构后数据完整率],"
        push!(sections, header_line)

        for month_data in monthly_stats
            sensor_values = [string(cov.after_completeness) for cov in month_data.coverages]

            before_completeness = [cov.before_completeness for cov in month_data.coverages]
            after_completeness = [cov.after_completeness for cov in month_data.coverages]

            overall_before = !isempty(before_completeness) ?
                round(mean(before_completeness), digits=2) : 0.0
            overall_after = !isempty(after_completeness) ?
                round(mean(after_completeness), digits=2) : 0.0

            row_line = "  [$(month_data.year)], [$(month_data.month)], " *
                join(["[$v]" for v in sensor_values], ", ") *
                ", [$overall_before], [$overall_after],"

            push!(sections, row_line)
        end

        push!(sections, ")")
        push!(sections, "")
    end

    return join(sections, "\n")
end

end # module MonthlyReconstructionTable
