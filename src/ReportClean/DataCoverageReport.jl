"""
Data Coverage Report Generation Module

This module generates the "数据覆盖率对比" (Data Coverage Comparison) section of the clean report.
It provides detailed sensor-by-sensor analysis of data coverage, loss rates, and fault durations.
"""

module DataCoverageReport

using DataFrames
using Statistics
using Dates
using ....Types.ReportCleanData: MastReportData, SensorCoverageInfo, DetectedInterval
using ....Types.SensorColumns: SensorColumn, create_sensor_short_name
using AlgebraOfGraphics, CairoMakie
using DataFrames

export generate_data_coverage_section

# Note: Using create_sensor_short_name from SensorColumns module instead of custom function

"""
    get_unique_avg_sensors(mast::MastReportData)

Extract unique sensors with only 'avg' statType from mast data.
Returns a dictionary with (sensorType, height, sensorDirection) as key.
"""
function get_unique_avg_sensors(mast::MastReportData)::Dict{Tuple{String, Float64, String}, Any}
    avg_sensors = filter(sensor -> sensor.statType == "avg", mast.raw_data.sensors)
    return Dict(
        (sensor.sensorType, sensor.height, sensor.sensorDirection) => sensor
        for sensor in avg_sensors
    )
end

"""
    calculate_sensor_coverage(mast, unique_sensors, expected_points, representative_interval)

Calculate coverage metrics for each sensor in the mast using detected interval.
Returns an array of coverage information tuples.
"""
function calculate_sensor_coverage(mast::MastReportData, unique_sensors::Dict, expected_points::Int, detected_interval::DetectedInterval)::Vector{NamedTuple}
    sorted_sensors = sort(collect(unique_sensors), by=x->x[1][2])  # Sort by height

    return map(sorted_sensors) do (_, sensor)
        sensor_col = sensor.columnName

        # Count non-missing values in raw and clean data
        raw_valid = sum(.!ismissing.(mast.raw_data.df[!, sensor_col]))
        clean_valid = sum(.!ismissing.(mast.clean_data.df[!, sensor_col]))

        # Calculate coverage rates with 4 decimal places
        raw_coverage = round(raw_valid / expected_points * 100, digits=4)
        clean_coverage = round(clean_valid / expected_points * 100, digits=4)

        # Calculate total missing time in days (final missing points after all processing)
        final_missing_points = expected_points - clean_valid
        interval_minutes = detected_interval.interval.value
        total_missing_days = round(final_missing_points * interval_minutes / (60 * 24), digits=4)  # Convert to days

        (
            name = create_sensor_short_name(sensor),
            raw_coverage = raw_coverage,
            clean_coverage = clean_coverage,
            total_missing_days = total_missing_days
        )
    end
end

"""
    calculate_time_range_and_expected_points(mast, detect_interval_fn, calculate_points_fn)

Calculate the time range and expected data points for a mast using detected representative interval.
Returns (time_start, time_end, expected_points, representative_interval).
"""
function calculate_time_range_and_expected_points(mast::MastReportData)::Tuple{DateTime, DateTime, Int, DetectedInterval}
    # Use pre-calculated values from MastReportData
    detected_interval = mast.detected_interval
    expected_points = mast.expected_points

    # Get time range from raw data TimeSeriesData
    raw_timestamps = sort(unique(filter(!ismissing, mast.raw_data.df.timestamp)))
    time_start = minimum(raw_timestamps)
    time_end = maximum(raw_timestamps)

    return time_start, time_end, expected_points, detected_interval
end

"""
    calculate_monthly_coverage(mast, unique_sensors, representative_interval)

Calculate monthly data coverage for each sensor.
Returns an array of dictionaries with month and sensor coverage percentages.
"""
function calculate_monthly_coverage(mast::MastReportData, unique_sensors::Dict, representative_interval::DetectedInterval)::Vector{Dict{String,Any}}
    monthly_coverage = Dict{String,Dict{String,Float64}}()

    # Get time range
    time_start, time_end, _, _ = calculate_time_range_and_expected_points(mast)

    # Generate monthly periods
    current_month = Date(year(time_start), month(time_start), 1)
    end_month = Date(year(time_end), month(time_end), 1)

    while current_month <= end_month
        month_name = "$(year(current_month))年$(month(current_month))月"
        monthly_coverage[month_name] = Dict{String,Float64}()

        # Calculate month boundaries
        month_start = DateTime(current_month)
        next_month = current_month + Month(1)
        month_end = DateTime(next_month) - Millisecond(1)

        # Calculate expected points for this month
        month_duration = month_end - month_start
        expected_monthly_points = Int(ceil(month_duration / representative_interval.interval))

        # Calculate coverage for each sensor in this month
        sensor_coverages = map(collect(unique_sensors)) do (_, sensor)
            sensor_col = sensor.columnName
            short_name = create_sensor_short_name(sensor)

            coverage = if hasproperty(mast.clean_data.df, sensor_col)
                # Filter timestamps for this month and count non-missing values
                month_mask = (mast.clean_data.df.timestamp .>= month_start) .& (mast.clean_data.df.timestamp .<= month_end)
                monthly_data = mast.clean_data.df[month_mask, sensor_col]
                monthly_points = count(!ismissing, monthly_data)
                expected_monthly_points > 0 ? (monthly_points / expected_monthly_points) * 100 : 0.0
            else
                0.0
            end

            short_name => coverage
        end

        # Add all sensor coverages to this month
        for (sensor_name, coverage) in sensor_coverages
            monthly_coverage[month_name][sensor_name] = coverage
        end

        current_month = next_month
    end

    # Convert to array format for table generation, sorted chronologically
    # Create month ordering based on actual dates
    month_dates = mapreduce(vcat, keys(monthly_coverage); init=Tuple{Date,String}[]) do month_name
        # Extract year and month from "2024年1月" format
        year_match = match(r"(\d{4})年", month_name)
        month_match = match(r"(\d{1,2})月", month_name)
        if !isnothing(year_match) && !isnothing(month_match)
            year = parse(Int, year_match.captures[1])
            month = parse(Int, month_match.captures[1])
            [(Date(year, month, 1), month_name)]
        else
            Tuple{Date,String}[]
        end
    end

    # Sort by date and create result array
    sorted_months = sort(month_dates, by=x->x[1])
    result = map(sorted_months) do (_, month_name)
        month_data = Dict{String,Any}("month" => month_name)
        merge!(month_data, monthly_coverage[month_name])
        month_data
    end

    return result
end

"""
    create_monthly_coverage_plot(monthly_coverage, mast_name, output_dir)

Create a monthly coverage visualization plot.
Returns the path to the generated plot file.
"""
function create_monthly_coverage_plot(monthly_coverage::Vector{Dict{String,Any}}, mast_name::String, output_dir::String)::Union{String, Nothing}
    if isempty(monthly_coverage)
        return nothing
    end

    # Prepare data for plotting
    plot_data = []

    for month_data in monthly_coverage
        month_name = month_data["month"]
        for (sensor_name, coverage) in month_data
            if sensor_name != "month"
                push!(plot_data, (
                    month = month_name,
                    sensor = sensor_name,
                    coverage = coverage
                ))
            end
        end
    end

    if isempty(plot_data)
        return nothing
    end

    # Convert to DataFrame
    df = DataFrame(plot_data)

    # Create the plot using AlgebraOfGraphics - Bar plot with dodged bars
    plot_spec = data(df) *
        mapping(:month, :coverage, color = :sensor, dodge = :sensor) *
        visual(BarPlot)

    # Create the figure
    fig = draw(plot_spec,
        figure = (size = (1200, 600),),
        axis = (
            xlabel = "月份",
            ylabel = "数据覆盖率 (%)",
            title = "$(mast_name) 月度数据覆盖率",
            xticklabelrotation = π/4
        )
    )

    # Save plot
    mkpath(output_dir)
    plot_path = joinpath(output_dir, "monthly_coverage_$(mast_name).png")
    save(plot_path, fig.figure)

    return plot_path
end

"""
    generate_data_coverage_section(mast_data, detect_interval_fn, calculate_points_fn)

Generate the complete data coverage section in Typst format.
Returns a string containing the Typst markup for the data coverage analysis.
"""
function generate_data_coverage_section(mast_data::Vector{MastReportData}, plots_dir::String)::String
    header_sections = ["== 数据覆盖率对比", ""]

    mast_sections = map(mast_data) do mast
        # Calculate time range and expected points using detected interval
        time_start, time_end, expected_points, representative_interval = calculate_time_range_and_expected_points(mast)

        # Get unique sensors (only avg statType)
        unique_sensors = get_unique_avg_sensors(mast)

        # Calculate coverage for each sensor
        sensor_coverage = calculate_sensor_coverage(mast, unique_sensors, expected_points, representative_interval)

        # Generate sensor coverage rows
        coverage_rows = map(sensor_coverage) do coverage
            "  [$(coverage.name)], [$(coverage.raw_coverage)%], [$(coverage.clean_coverage)%], [$(coverage.total_missing_days)天],"
        end

        # Generate basic mast section
        basic_section = [
            "=== $(mast.name)",
            "",
            "时间范围: $(time_start) 至 $(time_end)",
            "检测到的数据间隔: $(representative_interval.interval.value)分钟",
            "预期数据点数: $(expected_points)",
            "",
            "#table(",
            "  columns: 4,",
            "  [传感器名称], [原始覆盖率], [清洗后覆盖率], [最终缺失时长],",
        ]

        table_end = [")", ""]

        # Add monthly coverage visualization
        monthly_coverage = calculate_monthly_coverage(mast, unique_sensors, representative_interval)
        monthly_section = if !isempty(monthly_coverage)
            # Create plots directory
            mkpath(plots_dir)

            plot_path = create_monthly_coverage_plot(monthly_coverage, mast.name, plots_dir)

            if !isnothing(plot_path)
                [
                    "==== 月度数据覆盖率",
                    "",
                    "#figure(",
                    "  image(\"plots/$(basename(plot_path))\"),",
                    "  caption: [$(mast.name) 月度数据覆盖率趋势图 - 显示各传感器按月的数据覆盖率变化],",
                    ")",
                    ""
                ]
            else
                String[]
            end
        else
            String[]
        end

        # Combine all sections for this mast
        vcat(basic_section, coverage_rows, table_end, monthly_section)
    end

    all_sections = vcat(header_sections, vcat(mast_sections...))
    return join(all_sections, "\n")
end

end # module DataCoverageReport
