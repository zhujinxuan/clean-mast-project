"""
    ReportGeneration.jl

Chinese report generation functions using Typst format.
Creates comprehensive reports with individual tables and embedded plots for each mast pair.
"""
module ReportGeneration

using Dates
using DataFrames
using Printf
using CSV
using Statistics

using ...Types.MastTimeSeries: TimeSeriesData
using ..MonthlyCoverage: generate_monthly_coverage_tables

export generate_typst_report, export_csv_data

# Chinese text constants
const CHINESE_TEXTS = Dict(
    "title" => "跨测风塔分析报告",
    "generated_on" => "生成时间",
    "mast_pair" => "测风塔配对",
    "wind_speed_correlations" => "风速相关性",
    "wind_direction_relationships" => "风向关系",
    "data_coverage" => "数据覆盖情况",
    "speed_correlation_table" => "风速传感器相关性表",
    "direction_analysis_table" => "风向传感器分析表", 
    "target_sensor" => "目标传感器",
    "source_sensor" => "源传感器",
    "correlation" => "相关系数",
    "slope" => "斜率",
    "intercept" => "截距",
    "data_points" => "数据点数",
    "mean_offset" => "平均偏移",
    "std_deviation" => "标准偏差",
    "sensor_height" => "传感器高度",
    "overlap_days" => "重叠天数",
    "target_mast" => "目标测风塔",
    "source_mast" => "源测风塔",
    "analysis_summary" => "分析汇总",
    "unit_degrees" => "度",
    "unit_days" => "天",
    "unit_points" => "个",
    "unit_ms" => "m/s",
    "coverage_summary" => "数据覆盖汇总",
    "best_correlations" => "最佳相关性",
    "analysis_period" => "分析周期"
)

"""
    generate_typst_report(analysis_results, config, output_dir, mast_data_with_before)

Generate comprehensive Chinese Typst report with individual tables for each mast pair.

# Arguments
- `analysis_results::Vector`: Array of AnalyzePairResult
- `config`: ReportReconstructCrossConfiguration
- `output_dir::String`: Output directory path
- `mast_data_with_before::Dict{String, @NamedTuple{data::TimeSeriesData, before_data::TimeSeriesData}}`: Dictionary mapping mast names to NamedTuples with data and before_data fields

# Description
Creates:
- Main report.typ with embedded plots and tables
- Individual table files in tables/ subdirectory
- CSV data exports in data/ subdirectory
- Monthly coverage tables for all masts with before/after comparison
"""
function generate_typst_report(
    analysis_results::Vector,
    config,
    output_dir::String,
    mast_data_with_before::Dict{String, @NamedTuple{data::TimeSeriesData, before_data::TimeSeriesData}}
)::Nothing
    println("📄 Generating Chinese Typst report...")

    # Create directory structure
    tables_dir = joinpath(output_dir, "tables")
    mkpath(tables_dir)

    # Generate monthly coverage tables for all masts (with before/after comparison)
    println("  📊 Generating monthly coverage tables...")
    monthly_coverage_content = generate_monthly_coverage_tables(mast_data_with_before)

    # Generate individual table files for each mast pair
    table_files = map(analysis_results) do result
        target_name = result.target_mast
        source_name = result.source_mast

        table_file = "$(target_name)_$(source_name)_summary.typ"
        table_path = joinpath(tables_dir, table_file)

        generate_pair_table(result, table_path)
        table_file
    end
    
    # Generate main report
    report_file = joinpath(output_dir, "report.typ")
    generate_main_report(analysis_results, table_files, report_file, monthly_coverage_content)

    println("✅ Report generation completed")
    println("    📋 Main report: $(report_file)")
    println("    📊 Table files: $(length(table_files)) individual summaries")
    println("    📅 Monthly coverage tables included")
end

"""
    generate_pair_table(result, table_path)

Generate individual Typst table file for a single mast pair.

# Arguments
- `result`: AnalyzePairResult for this pair
- `table_path::String`: Output path for table file

# Description
Creates detailed tables showing:
- Wind speed correlations with regression parameters
- Wind direction analysis with offsets and standard deviations
- Data coverage summary
"""
function generate_pair_table(result, table_path::String)
    open(table_path, "w") do io
        target_name = result.target_mast
        source_name = result.source_mast
        
        # Speed correlations table
        if !isempty(result.speed_correlations)
            write(io, """
=== $(CHINESE_TEXTS["speed_correlation_table"])

#table(
  columns: 6,
  align: center + horizon,
  table.header(
    [$(target_name)], [$(source_name)], [$(CHINESE_TEXTS["correlation"])],
    [$(CHINESE_TEXTS["slope"])], [$(CHINESE_TEXTS["intercept"])], [$(CHINESE_TEXTS["data_points"])]
  ),
""")
            
            # Add speed correlation data rows
            for corr in result.speed_correlations
                target_height = corr.target_sensor.height
                source_height = corr.source_sensor.height
                correlation_str = @sprintf("%.3f", floor(corr.correlation * 1000) / 1000)
                slope_str = @sprintf("%.3f", corr.slope)
                intercept_str = @sprintf("%.3f", corr.intercept)
                
                write(io, """
  [$(target_height)m], [$(source_height)m], [$(correlation_str)], 
  [$(slope_str)], [$(intercept_str)], [$(corr.data_points)],
""")
            end
            
            write(io, ")\n\n")
        else
            write(io, """
=== $(CHINESE_TEXTS["speed_correlation_table"])

_本测风塔对无风速传感器相关性数据_

""")
        end
        
        # Direction analysis table
        if !isempty(result.direction_analysis)
            write(io, """
=== $(CHINESE_TEXTS["direction_analysis_table"])

#table(
  columns: 5,
  align: center + horizon,
  table.header(
    [$(target_name)], [$(source_name)], [$(CHINESE_TEXTS["mean_offset"])],
    [$(CHINESE_TEXTS["std_deviation"])], [$(CHINESE_TEXTS["data_points"])]
  ),
""")
            
            # Add direction analysis data rows
            for dir_result in result.direction_analysis
                target_height = dir_result.target_sensor.height
                source_height = dir_result.source_sensor.height
                offset_str = @sprintf("%.1f", dir_result.offset)
                std_str = @sprintf("%.1f", dir_result.std_deviation)
                
                write(io, """
  [$(target_height)m], [$(source_height)m], [$(offset_str)°], 
  [$(std_str)°], [$(dir_result.data_points)],
""")
            end
            
            write(io, ")\n\n")
        else
            write(io, """
=== $(CHINESE_TEXTS["direction_analysis_table"])

_本测风塔对无风向传感器分析数据_

""")
        end
        
        # Data coverage summary
        coverage = result.coverage
        write(io, """
=== $(CHINESE_TEXTS["data_coverage"])

- *$(CHINESE_TEXTS["overlap_days"]):* $(round(coverage.overlap_days, digits=1)) $(CHINESE_TEXTS["unit_days"])
- *$(CHINESE_TEXTS["data_points"]):* $(coverage.concurrent_records) $(CHINESE_TEXTS["unit_points"])
- *数据覆盖率:* $(round(coverage.coverage_percentage, digits=1))%

""")
        
        # Best performance summary
        if !isempty(result.speed_correlations)
            best_speed_corr = floor(result.speed_summary.best_high_elevation_correlation * 1000) / 1000
            write(io, """
- *最佳高空风速相关性:* $(best_speed_corr)
""")
        end
        
        if !isempty(result.direction_analysis)
            best_dir_std = round(result.direction_summary.best_high_elevation_std, digits=1)
            write(io, """
- *最佳高空风向标准偏差:* $(best_dir_std)°
""")
        end
        
        write(io, "\n")
    end
end

"""
    generate_main_report(results, table_files, report_path, monthly_coverage_content)

Generate main Typst report file with embedded plots and included tables.

# Arguments
- `results::Vector`: Array of AnalyzePairResult
- `table_files::Vector{String}`: List of individual table file names
- `report_path::String`: Output path for main report
- `monthly_coverage_content::String`: Pre-generated monthly coverage tables in Typst format

# Description
Creates comprehensive report with:
- Chinese fonts and formatting
- Executive summary
- Monthly coverage tables for all masts
- Individual sections for each mast pair
- Embedded plots and tables
- Analysis conclusions
"""
function generate_main_report(results::Vector, table_files::Vector{String}, report_path::String, monthly_coverage_content::String)
    open(report_path, "w") do io
        write(io, """
#set text(lang: "zh")
#set page(paper: "a4", margin: 2cm)
#set heading(numbering: "1.")

= $(CHINESE_TEXTS["title"])

$(CHINESE_TEXTS["generated_on"]): #datetime.today().display("[year]年[month]月[day]日")

== 执行摘要

本报告分析了 $(length(results)) 对测风塔之间的相关关系，包括风速传感器相关性分析、风向传感器偏移分析和数据覆盖情况统计。

=== $(CHINESE_TEXTS["analysis_summary"])

""")
        
        # Add summary statistics
        total_speed_pairs = sum(length(r.speed_correlations) for r in results)
        total_direction_pairs = sum(length(r.direction_analysis) for r in results)
        
        if total_speed_pairs > 0
            all_speed_corrs = vcat([r.speed_correlations for r in results]...)
            best_overall_corr = maximum(c.correlation for c in all_speed_corrs)
            avg_corr = mean(c.correlation for c in all_speed_corrs)

            write(io, """
- *风速传感器对总数:* $(total_speed_pairs) 对
- *最佳相关系数:* $(floor(best_overall_corr * 1000) / 1000)
- *平均相关系数:* $(floor(avg_corr * 1000) / 1000)
""")
        end
        
        if total_direction_pairs > 0
            all_direction_pairs = vcat([r.direction_analysis for r in results]...)
            best_std = minimum(d.std_deviation for d in all_direction_pairs)
            avg_std = mean(d.std_deviation for d in all_direction_pairs)
            
            write(io, """
- *风向传感器对总数:* $(total_direction_pairs) 对
- *最佳标准偏差:* $(round(best_std, digits=1))°
- *平均标准偏差:* $(round(avg_std, digits=1))°
""")
        end
        
        # Coverage summary
        total_overlap = sum(r.coverage.overlap_days for r in results)
        avg_overlap = total_overlap / length(results)
        
        write(io, """
- *平均数据重叠期:* $(round(avg_overlap, digits=1)) 天

""")

        # Insert monthly coverage tables
        write(io, monthly_coverage_content)
        write(io, "\n")

        # Individual mast pair sections
        for (i, result) in enumerate(results)
            target_name = result.target_mast
            source_name = result.source_mast
            
            write(io, """
== $(target_name) ← $(source_name)

=== 图表分析

#figure(
  image("plots/$(target_name)_$(source_name)_speed_correlations.png", width: 100%),
  caption: [$(CHINESE_TEXTS["wind_speed_correlations"]): $(target_name) ← $(source_name)]
)

#figure(
  image("plots/$(target_name)_$(source_name)_direction_scatter.png", width: 100%),
  caption: [$(CHINESE_TEXTS["wind_direction_relationships"]): $(target_name) ← $(source_name)]
)

=== 数据分析

#include "tables/$(table_files[i])"

""")
            
            # Add performance assessment
            if !isempty(result.speed_correlations)
                best_corr = result.speed_summary.best_high_elevation_correlation
                if best_corr >= 0.7
                    assessment = "优秀"
                elseif best_corr >= 0.5
                    assessment = "良好"
                else
                    assessment = "需要改进"
                end

                write(io, """
*风速相关性评估:* $(assessment) (最佳相关系数: $(floor(best_corr * 1000) / 1000))

""")
            end
            
            if !isempty(result.direction_analysis)
                best_std = result.direction_summary.best_high_elevation_std
                if best_std <= 12.5
                    assessment = "优秀"
                elseif best_std <= 20.0
                    assessment = "良好"
                else
                    assessment = "需要改进"
                end
                
                write(io, """
*风向一致性评估:* $(assessment) (最佳标准偏差: $(round(best_std, digits=1))°)

""")
            end
            
            write(io, "#pagebreak()\n\n")
        end
        
        # Conclusions section
        write(io, """
== 分析结论

=== 重构模型适用性

基于分析结果，以下测风塔对适合用于跨测风塔重构：

""")
        
        # Recommend suitable pairs
        for result in results
            target_name = result.target_mast
            source_name = result.source_mast
            
            suitable_for_speed = false
            suitable_for_direction = false
            
            if !isempty(result.speed_correlations)
                best_corr = result.speed_summary.best_high_elevation_correlation
                overlap_days = result.coverage.overlap_days
                suitable_for_speed = (best_corr >= 0.7 && overlap_days >= 120)
            end
            
            if !isempty(result.direction_analysis)
                best_std = result.direction_summary.best_high_elevation_std
                overlap_days = result.coverage.overlap_days
                suitable_for_direction = (best_std <= 45.0 && overlap_days >= 120)
            end
            
            if suitable_for_speed || suitable_for_direction
                capabilities = vcat(
                    suitable_for_speed ? ["风速重构"] : String[],
                    suitable_for_direction ? ["风向重构"] : String[]
                )
                capability_str = join(capabilities, "、")
                
                write(io, """
- *$(target_name) ← $(source_name):* 适合 $(capability_str)
""")
            end
        end
        
        write(io, """

=== 数据质量建议

为提高跨测风塔重构精度，建议：

1. 优先使用高海拔传感器 (≥120m) 进行重构
2. 确保数据重叠期不少于120天
3. 定期校准传感器以减少系统偏差
4. 考虑地形和气候因素对传感器性能的影响

=== 技术参数

本分析使用以下技术参数：
- 最小相关系数要求：0.7 (风速重构)
- 最大标准偏差要求：12.5° (风向重构)
- 最小数据重叠期：120天
- 分析方法：Pearson相关性分析、圆形统计学

""")
    end
    
    println("    📝 Chinese report: report.typ")
end

"""
    export_csv_data(analysis_results, output_dir)

Export analysis results to CSV files for further processing.

# Arguments
- `analysis_results::Vector`: Array of AnalyzePairResult
- `output_dir::String`: Output directory path

# Description
Creates CSV files in data/ subdirectory:
- Individual correlation and direction files for each pair
- Summary statistics file
"""
function export_csv_data(analysis_results::Vector, output_dir::String)::Nothing
    data_dir = joinpath(output_dir, "data")
    mkpath(data_dir)
    
    println("💾 Exporting CSV data files...")
    
    for result in analysis_results
        target_name = result.target_mast
        source_name = result.source_mast
        
        # Export speed correlations
        if !isempty(result.speed_correlations)
            speed_data = map(result.speed_correlations) do corr
                (
                    target_mast = target_name,
                    source_mast = source_name,
                    target_height = corr.target_sensor.height,
                    source_height = corr.source_sensor.height,
                    correlation = corr.correlation,
                    slope = corr.slope,
                    intercept = corr.intercept,
                    data_points = corr.data_points
                )
            end
            speed_df = DataFrame(speed_data)

            speed_csv = joinpath(data_dir, "$(target_name)_$(source_name)_correlations.csv")
            CSV.write(speed_csv, speed_df)
        end
        
        # Export direction analysis
        if !isempty(result.direction_analysis)
            direction_data = map(result.direction_analysis) do dir_result
                (
                    target_mast = target_name,
                    source_mast = source_name,
                    target_height = dir_result.target_sensor.height,
                    source_height = dir_result.source_sensor.height,
                    mean_offset = dir_result.offset,
                    std_deviation = dir_result.std_deviation,
                    data_points = dir_result.data_points
                )
            end
            direction_df = DataFrame(direction_data)

            direction_csv = joinpath(data_dir, "$(target_name)_$(source_name)_directions.csv")
            CSV.write(direction_csv, direction_df)
        end
    end
    
    println("    📈 CSV exports: $(length(analysis_results) * 2) files")
end

end # module 