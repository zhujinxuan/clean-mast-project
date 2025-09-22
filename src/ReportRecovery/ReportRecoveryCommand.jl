module ReportRecoveryCommand

using Dates
using TOML
using ...Types.ReportRecoveryConfig: ReportRecoveryConfiguration, from_dict
using ...Types.ReportRecoveryData: RecoveryReportData
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ..RecoveryAnalysis: analyze_mast_recovery
using ..RecoveryStatusReport: generate_recovery_report_section, generate_recovery_table, create_recovery_bar_chart

export execute

"""
    execute(config_path::String)

Execute data recovery status report generation.

# Arguments
- `config_path::String`: Path to report-recovery.toml configuration file

# Workflow
1. Load report-recovery.toml configuration
2. For each mast, analyze recovery statistics across all reconstruction stages
3. Generate comprehensive Typst report with tables and charts
4. Save report to specified output directory
"""
function execute(config_path::String)
    println("📊 Generating data recovery status report...")
    
    # Determine project directory from config path
    # If config is in report-masts/, the project dir is the parent of that
    config_dir = dirname(config_path)
    project_dir = if basename(config_dir) == "report-masts"
        dirname(config_dir)  # Go up one level from report-masts to project root
    else
        config_dir  # For backward compatibility with configs in project root
    end
    
    # Load configuration
    config = load_recovery_config(config_path)
    
    # Setup report directory
    report_dir = setup_report_directory(config.output.report_dir, project_dir)
    
    # Analyze recovery for each mast
    println("🔍 Analyzing recovery statistics...")
    mast_recovery_data = map(config.masts) do mast_config
        analyze_mast_recovery(mast_config, project_dir)
    end
    
    # Create complete report data
    report_data = RecoveryReportData(
        masts = mast_recovery_data,
        generation_time = now()
    )
    
    # Generate Typst report with charts
    println("📝 Generating Typst report...")
    typst_content = generate_complete_report(report_data, report_dir)

    # Save report
    report_file = joinpath(report_dir, config.output.report_filename)
    open(report_file, "w") do io
        write(io, typst_content)
    end
    
    # Generate summary
    print_report_summary(report_data, report_file)
    
    println("✅ Data recovery status report generated successfully!")
    println("📁 Report saved to: $report_file")
end

"""
    load_recovery_config(config_path::String)::ReportRecoveryConfiguration

Load and parse report-recovery.toml configuration.
"""
function load_recovery_config(config_path::String)::ReportRecoveryConfiguration
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end
    
    config_dict = load_dict(config_path)
    return from_dict(ReportRecoveryConfiguration, config_dict)
end

"""
    setup_report_directory(report_dir::String, project_dir::String)::String

Create report directory and return absolute path.
"""
function setup_report_directory(report_dir::String, project_dir::String)::String
    # Resolve relative path
    abs_report_dir = isabspath(report_dir) ? report_dir : joinpath(project_dir, report_dir)
    
    # Create directory if it doesn't exist
    if !isdir(abs_report_dir)
        mkpath(abs_report_dir)
        println("📁 Created report directory: $abs_report_dir")
    end
    
    return abs_report_dir
end

"""
    generate_complete_report(report_data::RecoveryReportData, report_dir::String)::String

Generate complete Typst report content with charts and tables.
"""
function generate_complete_report(report_data::RecoveryReportData, report_dir::String)::String
    # Generate header
    header_section = """
#set page(paper: "a4", margin: 2cm)
#set heading(numbering: "1.")
#set text(font: "SimSun", size: 10pt)

= 数据恢复状态报告

== 执行摘要

本报告分析了 $(length(report_data.masts)) 座测风塔在数据重构过程中的恢复效果。
报告展示了同塔插补、异塔插补和中尺度插补三个阶段的数据恢复统计。

分析时间：$(report_data.masts[1].analysis_start) 至 $(report_data.masts[1].analysis_end)

$(join([
    "- $(mast.name): $(length(mast.sensor_recovery)) 个传感器"
    for mast in report_data.masts
], "\n"))

"""

    # Create charts directory
    charts_dir = joinpath(report_dir, "charts")
    mkpath(charts_dir)

    # Generate charts for each mast
    chart_paths = Dict{String, String}()
    for mast in report_data.masts
        chart_path = create_recovery_bar_chart(mast, charts_dir)
        if !isnothing(chart_path)
            chart_paths[mast.name] = chart_path
        end
    end

    # Generate main content with placeholders
    recovery_section = generate_recovery_report_section(report_data)

    # Replace table and chart placeholders with actual content
    for mast in report_data.masts
        # Replace table placeholder
        table_placeholder = "<!-- RECOVERY_TABLE_$(mast.name) -->"
        recovery_table = generate_recovery_table(mast)
        if !isnothing(recovery_table)
            # Create a temporary string buffer to capture the table output
            table_io = IOBuffer()
            show(table_io, MIME"text/typst"(), recovery_table)
            table_content = String(take!(table_io))
            recovery_section = replace(recovery_section, table_placeholder => table_content)
        else
            recovery_section = replace(recovery_section, table_placeholder => "未找到传感器数据。")
        end

        # Replace chart placeholder
        chart_placeholder = "<!-- RECOVERY_CHART_$(mast.name) -->"
        if haskey(chart_paths, mast.name)
            chart_path = chart_paths[mast.name]
            rel_chart_path = relpath(chart_path, report_dir)
            rel_chart_path = replace(rel_chart_path, "\\" => "/")  # Use forward slashes for Typst
            chart_content = """
#figure(
  image("$(rel_chart_path)", width: 100%),
  caption: [$(mast.name) 数据恢复柱状图]
)
"""
            recovery_section = replace(recovery_section, chart_placeholder => chart_content)
        else
            recovery_section = replace(recovery_section, chart_placeholder => "无图表数据。")
        end
    end
    
    # Generate footer
    footer_section = """

== 技术说明

=== 数据恢复方法

1. *同塔插补*：利用同一测风塔不同高度传感器间的物理相关性，通过线性回归等方法重构缺失数据
2. *异塔插补*：利用不同测风塔间的空间相关性，基于训练的跨塔模型进行数据重构
3. *中尺度插补*：利用ERA5等中尺度气象数据，通过相关性模型进行最终数据填补

=== 统计指标说明

- *初始缺失*：塔影处理后的缺失数据点数量
- *同塔插补*：单塔重构填补的数据点数量
- *异塔插补*：跨塔重构填补的数据点数量  
- *中尺度插补*：中尺度重构填补的数据点数量
- *最终缺失*：所有重构完成后仍缺失的数据点数量

---
_报告生成时间：$(report_data.generation_time)_
_配置文件：report-recovery.toml_
"""

    # Combine all sections
    return join([
        header_section,
        recovery_section,
        footer_section
    ], "\n")
end

"""
    print_report_summary(report_data::RecoveryReportData, report_file::String)

Print summary statistics to console.
"""
function print_report_summary(report_data::RecoveryReportData, report_file::String)
    total_sensors = sum(length(mast.sensor_recovery) for mast in report_data.masts)
    total_initial_missing = sum(
        sum(sensor.initial_missing for sensor in mast.sensor_recovery)
        for mast in report_data.masts
    )
    total_filled = sum(
        sum(sensor.single_filled + sensor.cross_filled + sensor.meso_filled 
            for sensor in mast.sensor_recovery)
        for mast in report_data.masts
    )
    
    recovery_rate = total_initial_missing > 0 ? 
                   (total_filled / total_initial_missing) * 100.0 : 0.0
    
    println("\n📈 Recovery Summary:")
    println("   Masts analyzed: $(length(report_data.masts))")
    println("   Total sensors: $total_sensors")
    println("   Initial missing points: $total_initial_missing")
    println("   Total recovered points: $total_filled")
    println("   Overall recovery rate: $(round(recovery_rate, digits=1))%")
    println("   Report file: $report_file")
end

end # module
