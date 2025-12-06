module ReportGeneration

using Dates
using Printf
using DataFrames
using SummaryTables
using ...Types.ReportFrozenPeriodData: FrozenReportData, MastFrozenData
using ...Types.ReportFrozenPeriodConfig: FrozenDetectionSettings, FrozenThresholdSet
using ..MonthlyStatistics: generate_monthly_frozen_table, generate_monthly_missing_table, MonthlyData

export generate_frozen_period_report, generate_frozen_table, generate_missing_table

"""
    generate_frozen_period_report(report_data::FrozenReportData)::String

Generate complete Typst report with frozen period tables for all threshold sets.

# Arguments
- `report_data::FrozenReportData`: Complete report data

# Returns
- `String`: Typst report content
"""
function generate_frozen_period_report(report_data::FrozenReportData)::String
    sections = String[]

    # Header
    push!(sections, generate_header())

    # Summary
    push!(sections, generate_summary(report_data))

    # For each mast
    for mast in report_data.masts
        push!(sections, generate_mast_section(mast, report_data.detection_settings))
    end

    # Footer with methodology
    push!(sections, generate_methodology_section(report_data.detection_settings))

    return join(sections, "\n\n")
end

"""
    generate_header()::String

Generate Typst document header.
"""
function generate_header()::String
    return """
#set page(paper: "a4", margin: 2cm)
#set heading(numbering: "1.")
#set text(font: "SimSun", size: 10pt)

= 冻结期检测报告

本报告分析测风塔传感器的冻结期，基于温度、风速风向稳定性的综合判据。
支持多种阈值配置（加热型和非加热型传感器）。
"""
end

"""
    generate_summary(report_data::FrozenReportData)::String

Generate summary section.
"""
function generate_summary(report_data::FrozenReportData)::String
    total_sensors = sum(length(mast.sensor_frozen_info) for mast in report_data.masts)

    threshold_names = [t.name for t in report_data.detection_settings.thresholds]
    threshold_list = join(threshold_names, "、")

    return """
== 执行摘要

- 分析塔数：$(length(report_data.masts))
- 分析传感器数：$total_sensors
- 阈值配置：$threshold_list
- 报告生成时间：$(report_data.generation_time)
"""
end

"""
    generate_mast_section(mast::MastFrozenData, settings::FrozenDetectionSettings)::String

Generate section for one mast with tables for each threshold set.
"""
function generate_mast_section(mast::MastFrozenData, settings::FrozenDetectionSettings)::String
    rh_note = if length(mast.sensor_frozen_info) > 0 && mast.sensor_frozen_info[1].rh_sensor_available
        "（已检测到RH传感器）"
    else
        "（未检测到RH传感器，仅使用温度和风速风向判据）"
    end

    sections = String["""
== $(mast.name)

- 分析周期：$(mast.analysis_start) 至 $(mast.analysis_end)
- 数据间隔：$(mast.interval_minutes) 分钟
- 传感器数：$(length(mast.sensor_frozen_info))
- RH传感器：$rh_note
"""]

    # Generate frozen duration tables for each threshold set
    for threshold in settings.thresholds
        push!(sections, """
=== 月度冻结时长统计 - $(threshold.name)（天）

<!-- FROZEN_TABLE_$(mast.name)_$(threshold.name) -->
""")
    end

    # Generate missing data table (only once, independent of thresholds)
    push!(sections, """
=== 月度缺测时长统计（天）

<!-- MISSING_TABLE_$(mast.name) -->
""")

    return join(sections, "\n")
end

"""
    generate_frozen_table(mast::MastFrozenData, threshold_name::String)

Generate frozen duration table for one threshold set using SummaryTables.
Returns a SummaryTables.Table object or nothing if no data.
"""
function generate_frozen_table(mast::MastFrozenData, threshold_name::String)
    monthly_data = generate_monthly_frozen_table(mast, threshold_name)

    if isempty(monthly_data)
        return nothing
    end

    # Get unique sensors and months
    sensors = unique([data.sensor_name for data in monthly_data])
    months = unique([data.year_month for data in monthly_data])
    sort!(sensors)
    sort!(months)

    # Create data matrix
    data_matrix = Dict{Tuple{Tuple{Int, Int}, String}, Float64}()
    for data in monthly_data
        data_matrix[(data.year_month, data.sensor_name)] = data.duration_days
    end

    # Create DataFrame for the table with explicit column order
    # First column is 年月, followed by sensors in their original order
    column_names = ["年月"; sensors]

    # Build column data
    year_month_col = String[]
    sensor_cols = Dict{String, Vector{String}}()
    for sensor in sensors
        sensor_cols[sensor] = String[]
    end

    for (year, month) in months
        month_str = @sprintf("%04d-%02d", year, month)
        push!(year_month_col, month_str)

        for sensor in sensors
            val = get(data_matrix, ((year, month), sensor), 0.0)
            push!(sensor_cols[sensor], val > 0.0 ? @sprintf("%.2f", val) : "-")
        end
    end

    # Construct DataFrame column by column with explicit order
    df = DataFrame()
    df[!, Symbol("年月")] = year_month_col
    for sensor in sensors
        df[!, Symbol(sensor)] = sensor_cols[sensor]
    end

    return simple_table(df)
end

"""
    generate_missing_table(mast::MastFrozenData)

Generate missing data duration table using SummaryTables.
Returns a SummaryTables.Table object or nothing if no data.
"""
function generate_missing_table(mast::MastFrozenData)
    monthly_data = generate_monthly_missing_table(mast)

    if isempty(monthly_data)
        return nothing
    end

    # Get unique sensors and months
    sensors = unique([data.sensor_name for data in monthly_data])
    months = unique([data.year_month for data in monthly_data])
    sort!(sensors)
    sort!(months)

    # Create data matrix
    data_matrix = Dict{Tuple{Tuple{Int, Int}, String}, Float64}()
    for data in monthly_data
        data_matrix[(data.year_month, data.sensor_name)] = data.duration_days
    end

    # Create DataFrame for the table with explicit column order
    # First column is 年月, followed by sensors in their original order
    column_names = ["年月"; sensors]

    # Build column data
    year_month_col = String[]
    sensor_cols = Dict{String, Vector{String}}()
    for sensor in sensors
        sensor_cols[sensor] = String[]
    end

    for (year, month) in months
        month_str = @sprintf("%04d-%02d", year, month)
        push!(year_month_col, month_str)

        for sensor in sensors
            val = get(data_matrix, ((year, month), sensor), 0.0)
            push!(sensor_cols[sensor], val > 0.0 ? @sprintf("%.2f", val) : "-")
        end
    end

    # Construct DataFrame column by column with explicit order
    df = DataFrame()
    df[!, Symbol("年月")] = year_month_col
    for sensor in sensors
        df[!, Symbol(sensor)] = sensor_cols[sensor]
    end

    return simple_table(df)
end

"""
    generate_methodology_section(settings::FrozenDetectionSettings)::String

Generate methodology explanation section for all threshold sets.
"""
function generate_methodology_section(settings::FrozenDetectionSettings)::String
    sections = String["""
== 检测方法说明
"""]

    # Generate criteria for each threshold set
    for threshold in settings.thresholds
        # Build criteria list
        criteria = String[]
        push!(criteria, "1. 温度条件：T < $(threshold.temperature_threshold)°C")

        # Only show wind stability if thresholds are reasonable (not disabled)
        if threshold.windspeed_change_threshold < 100.0
            push!(criteria, "2. 风速稳定性：变化幅度 < $(threshold.windspeed_change_threshold) m/s")
            push!(criteria, "3. 风向稳定性：变化幅度 < $(threshold.winddirection_change_threshold)°")
        end

        # Add RH condition if present
        if !isnothing(threshold.rh_threshold)
            push!(criteria, "$(length(criteria)+1). 相对湿度条件：RH < $(threshold.rh_threshold)%")
        end

        # Add duration requirement if specified
        if !isnothing(threshold.min_duration_seconds)
            duration_hours = threshold.min_duration_seconds / 3600.0
            push!(criteria, "$(length(criteria)+1). 持续时间：≥ $duration_hours 小时")
        end

        criteria_text = join(criteria, "\n")

        push!(sections, """
=== 冻结判据 - $(threshold.name)（需同时满足）

$criteria_text
""")
    end

    push!(sections, """
=== 传感器配置

- *温度传感器*：使用最低高度的平均温度传感器
- *风向传感器*：对每个风速传感器，使用最近高度的风向传感器
- *RH传感器*：如存在则标注，但不参与判据
- *风向环绕处理*：355°到5°的差值计算为10°（而非350°）

=== 数据来源

- 使用原始数据（raw/目录，清洗前）进行分析
- 分析所有高度和方向的风速传感器
- 仅使用statType为"avg"的传感器
- 每个传感器使用所有阈值配置分别计算冻结期

---
_报告生成时间：$(Dates.now())_
""")

    return join(sections, "\n")
end

end # module
