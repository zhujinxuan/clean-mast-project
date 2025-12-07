module RecoveryStatusReport

using Dates
using DataFrames
using SummaryTables
using AlgebraOfGraphics
using CairoMakie
using ...Types.ReportRecoveryData: MastRecoveryData, SensorRecoveryInfo, RecoveryReportData

export generate_recovery_report_section, generate_recovery_table, generate_recovery_chart, create_recovery_bar_chart

"""
    generate_recovery_report_section(report_data::RecoveryReportData)::String

Generate complete recovery status report section in Chinese Typst format.

# Arguments
- `report_data::RecoveryReportData`: Complete recovery data for all masts

# Returns
- `String`: Typst formatted report section
"""
function generate_recovery_report_section(report_data::RecoveryReportData)::String
    if isempty(report_data.masts)
        return "== 数据恢复状态报告\n\n未找到测风塔数据。\n"
    end

    # Generate report header
    sections = String[
        "== 数据恢复状态报告",
        "",
        "本节展示各测风塔在数据重构过程中的恢复情况，包括同塔插补、异塔插补和中尺度插补的效果。",
        "",
        "分析时间范围：$(report_data.masts[1].analysis_start) 至 $(report_data.masts[1].analysis_end)",
        ""
    ]

    # Generate sections for each mast
    for mast in report_data.masts
        # Add mast header
        push!(sections, "=== $(mast.name) 数据恢复统计")
        push!(sections, "")

        # Add recovery table using SummaryTables
        recovery_table = generate_recovery_table(mast)
        if !isnothing(recovery_table)
            push!(sections, "表格：$(mast.name) 数据恢复统计表")
            push!(sections, "")
            # Note: The actual table will be rendered separately in the main report generation
            push!(sections, "<!-- RECOVERY_TABLE_$(mast.name) -->")
            push!(sections, "")
        end

        # Add recovery chart placeholder
        push!(sections, "<!-- RECOVERY_CHART_$(mast.name) -->")
        push!(sections, "")
    end

    # Add summary section
    push!(sections, generate_recovery_summary(report_data))

    return join(sections, "\n")
end

"""
    generate_recovery_table(mast::MastRecoveryData)

Generate recovery statistics table for a single mast using SummaryTables.jl.
Returns a SummaryTables.Table object that can be rendered to Typst format.
"""
function generate_recovery_table(mast::MastRecoveryData)
    if isempty(mast.sensor_recovery)
        return nothing
    end

    # Create DataFrame from sensor recovery data
    recovery_df = DataFrame(
        通道 = [info.sensor_name for info in mast.sensor_recovery],
        初始缺失 = [info.initial_missing for info in mast.sensor_recovery],
        同塔插补 = [info.single_filled for info in mast.sensor_recovery],
        异塔插补 = [info.cross_filled for info in mast.sensor_recovery],
        中尺度插补 = [info.meso_filled for info in mast.sensor_recovery],
        最终缺失 = [info.final_missing for info in mast.sensor_recovery]
    )

    # Create SummaryTables table
    return simple_table(recovery_df)
end

"""
    create_recovery_bar_chart(mast::MastRecoveryData, output_dir::String)::Union{String, Nothing}

Create bar chart visualization of recovery statistics for a single mast.
Returns the path to the generated SVG file, or nothing if no data.
"""
function create_recovery_bar_chart(mast::MastRecoveryData, output_dir::String)::Union{String, Nothing}
    if isempty(mast.sensor_recovery)
        return nothing
    end

    # Prepare data for plotting
    plot_data = NamedTuple{(:sensor, :category, :count), Tuple{String, String, Int}}[]

    for sensor_info in mast.sensor_recovery
        sensor_name = sensor_info.sensor_name

        # Add data points for each category
        push!(plot_data, (sensor = sensor_name, category = "同塔插补", count = sensor_info.single_filled))
        push!(plot_data, (sensor = sensor_name, category = "异塔插补", count = sensor_info.cross_filled))
        push!(plot_data, (sensor = sensor_name, category = "中尺度插补", count = sensor_info.meso_filled))
        push!(plot_data, (sensor = sensor_name, category = "最终缺失", count = sensor_info.final_missing))
    end

    # Convert to DataFrame
    df = DataFrame(plot_data)

    # Create grouped bar chart
    fig = data(df) *
          mapping(:sensor, :count, color=:category, dodge=:category) *
          visual(BarPlot) |>
          draw(
              figure=(size=(1200, 600),),
              axis=(
                  xlabel="传感器",
                  ylabel="数据点数量",
                  title="$(mast.name) 数据恢复统计",
                  xticklabelrotation=π/4
              )
          )

    # Save plot
    mkpath(output_dir)
    plot_path = joinpath(output_dir, "recovery_chart_$(mast.name).png")
    save(plot_path, fig.figure)

    return plot_path
end

"""
    generate_recovery_summary(report_data::RecoveryReportData)::String

Generate overall recovery summary statistics.
"""
function generate_recovery_summary(report_data::RecoveryReportData)::String
    total_masts = length(report_data.masts)
    total_sensors = sum(length(mast.sensor_recovery) for mast in report_data.masts)
    
    # Calculate overall statistics
    total_initial_missing = 0
    total_single_filled = 0
    total_cross_filled = 0
    total_meso_filled = 0
    total_final_missing = 0
    
    for mast in report_data.masts
        for sensor in mast.sensor_recovery
            total_initial_missing += sensor.initial_missing
            total_single_filled += sensor.single_filled
            total_cross_filled += sensor.cross_filled
            total_meso_filled += sensor.meso_filled
            total_final_missing += sensor.final_missing
        end
    end
    
    total_filled = total_single_filled + total_cross_filled + total_meso_filled
    overall_recovery_rate = total_initial_missing > 0 ? 
                           (total_filled / total_initial_missing) * 100.0 : 0.0
    
    summary_lines = String[
        "=== 总体恢复统计",
        "",
        "#table(",
        "  columns: 2,",
        "  [*统计项目*], [*数值*],",
        "  [测风塔数量], [$total_masts],",
        "  [传感器总数], [$total_sensors],",
        "  [初始缺失数据点], [$total_initial_missing],",
        "  [同塔插补恢复], [$total_single_filled],",
        "  [异塔插补恢复], [$total_cross_filled],",
        "  [中尺度插补恢复], [$total_meso_filled],",
        "  [总恢复数据点], [$total_filled],",
        "  [最终缺失数据点], [$total_final_missing],",
        "  [总体恢复率], [$(round(overall_recovery_rate, digits=1))%],",
        ")",
        "",
        "=== 恢复效果分析",
        "",
        "数据恢复过程通过三个阶段逐步填补缺失数据：",
        "",
        "1. *同塔插补*：利用同一测风塔不同高度传感器间的相关性进行数据重构",
        "2. *异塔插补*：利用不同测风塔间的空间相关性进行数据重构", 
        "3. *中尺度插补*：利用中尺度气象数据进行最终的数据填补",
        "",
        "总体恢复率达到 $(round(overall_recovery_rate, digits=1))%，" *
        "有效提高了数据的完整性和可用性。"
    ]
    
    return join(summary_lines, "\n")
end

end # module
