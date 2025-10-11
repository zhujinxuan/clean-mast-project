"""
    ReportGeneration.jl

Typst report generation and CSV data export for meso-mast reconstruction analysis.
"""
module ReportGeneration

using DataFrames
using CSV
using Printf
using Dates

using ...Types.SensorColumns: create_sensor_short_name

export generate_typst_report, export_csv_data

"""
    generate_typst_report(analysis_results, output_dir)

Generate Chinese Typst report with summary tables and embedded plots.

# Arguments
- `analysis_results::Vector`: Analysis results
- `output_dir::String`: Output directory
"""
function generate_typst_report(analysis_results::Vector, output_dir::String)
    report_file = joinpath(output_dir, "report.typ")

    open(report_file, "w") do io
        write_typst_header(io)
        write_typst_summary_section(io, analysis_results)
        write_typst_sensor_pairs_section(io, analysis_results)
        write_typst_details_section(io, analysis_results)
    end

    println("      ✓ Generated report: $(basename(report_file))")
end

"""
    write_typst_header(io)

Write Typst document header.
"""
function write_typst_header(io)
    println(io, "#set page(paper: \"a4\", margin: 2cm)")
    println(io, "#set text(size: 10.5pt, lang: \"zh\")")
    println(io, "#set par(justify: true, leading: 0.65em)")
    println(io, "#set heading(numbering: \"1.1\")")
    println(io, "")
    println(io, "#let breakable-figure(..args) = {")
    println(io, "  show figure: set block(breakable: true)")
    println(io, "  figure(..args)")
    println(io, "}")
    println(io, "")
    println(io, "#align(center)[")
    println(io, "  #text(size: 18pt, weight: \"bold\")[")
    println(io, "    中尺度数据重构质量分析报告")
    println(io, "  ]")
    println(io, "]")
    println(io, "")
    println(io, "#align(center)[")
    println(io, "  #text(size: 12pt)[")
    println(io, "    生成日期: $(Dates.format(now(), "yyyy-mm-dd HH:MM"))")
    println(io, "  ]")
    println(io, "]")
    println(io, "")
    println(io, "#pagebreak()")
    println(io, "")
end

"""
    write_typst_summary_section(io, analysis_results)

Write summary section with table of all meso-mast pairs.
"""
function write_typst_summary_section(io, analysis_results::Vector)
    println(io, "= 重构质量汇总")
    println(io, "")
    println(io, "本节总结所有测风塔与中尺度数据对的重构质量指标。")
    println(io, "")
    println(io, "#figure(")
    println(io, "  table(")
    println(io, "    columns: 6,")
    println(io, "    align: (center, center, center, center, center, center),")
    println(io, "    [*测风塔*], [*中尺度数据*], [*重叠天数*], [*传感器对数*], [*最佳相关系数*], [*最佳RMSE (m/s)*],")

    for result in analysis_results
        mast = result.mast_name
        meso = result.meso_name
        overlap_days = @sprintf "%.1f" result.overlap_days
        n_sensors = length(result.sensor_metrics)

        best_idx = argmax([m.correlation for m in result.sensor_metrics])
        best_metrics = result.sensor_metrics[best_idx]
        best_corr = @sprintf "%.3f" best_metrics.correlation
        best_rmse = @sprintf "%.2f" best_metrics.rmse

        println(io, "    [$mast], [$meso], [$overlap_days], [$n_sensors], [$best_corr], [$best_rmse],")
    end

    println(io, "  ),")
    println(io, "  caption: [测风塔-中尺度数据对重构质量汇总表]")
    println(io, ")")
    println(io, "")
end

"""
    write_typst_sensor_pairs_section(io, analysis_results)

Write detailed sensor pairs table showing all individual sensor comparisons.
"""
function write_typst_sensor_pairs_section(io, analysis_results::Vector)
    println(io, "#pagebreak()")
    println(io, "")
    println(io, "= 传感器对详细信息")
    println(io, "")
    println(io, "本节列出所有传感器对的详细指标。")
    println(io, "")

    # Collect all sensor pairs sorted by mast, meso, mast height, meso height
    all_pairs = []
    for result in analysis_results
        for metrics in result.sensor_metrics
            push!(all_pairs, (
                mast_name = result.mast_name,
                meso_name = result.meso_name,
                overlap_days = result.overlap_days,
                mast_height = metrics.mast_sensor.height,
                meso_height = metrics.meso_sensor.height,
                correlation = metrics.correlation,
                rmse = metrics.rmse,
                sample_count = metrics.sample_count
            ))
        end
    end

    # Sort by mast, meso, mast height, meso height
    sort!(all_pairs, by = x -> (x.mast_name, x.meso_name, x.mast_height, x.meso_height))

    println(io, "#breakable-figure(")
    println(io, "  table(")
    println(io, "    columns: 7,")
    println(io, "    align: (center, center, center, center, center, center, center),")
    println(io, "    [*测风塔*], [*中尺度数据*], [*测风塔风速高度 (m)*], [*中尺度高度 (m)*], [*相关系数*], [*RMSE (m/s)*], [*重叠天数*],")

    for pair in all_pairs
        mast = pair.mast_name
        meso = pair.meso_name
        mast_h = @sprintf "%.0f" pair.mast_height
        meso_h = @sprintf "%.0f" pair.meso_height
        corr = @sprintf "%.3f" pair.correlation
        rmse_val = @sprintf "%.2f" pair.rmse
        overlap = @sprintf "%.1f" pair.overlap_days

        println(io, "    [$mast], [$meso], [$mast_h], [$meso_h], [$corr], [$rmse_val], [$overlap],")
    end

    println(io, "  ),")
    println(io, "  caption: [所有传感器对详细指标表]")
    println(io, ")")
    println(io, "")
end

"""
    write_typst_details_section(io, analysis_results)

Write detailed section with plots for each meso-mast pair.
"""
function write_typst_details_section(io, analysis_results::Vector)
    println(io, "#pagebreak()")
    println(io, "")
    println(io, "= 详细分析")
    println(io, "")
    println(io, "本节展示每个测风塔-中尺度数据对的散点图和拟合线。")
    println(io, "")

    for result in analysis_results
        mast = result.mast_name
        meso = result.meso_name

        println(io, "== $(mast) ← $(meso)")
        println(io, "")

        best_idx = argmax([m.correlation for m in result.sensor_metrics])
        best_metrics = result.sensor_metrics[best_idx]
        best_corr = @sprintf "%.3f" best_metrics.correlation
        best_rmse = @sprintf "%.2f" best_metrics.rmse

        println(io, "*重叠天数*: $(round(result.overlap_days, digits=1)) 天 \\")
        println(io, "*最佳相关系数*: $best_corr \\")
        println(io, "*最佳RMSE*: $best_rmse m/s \\")
        println(io, "*传感器对数*: $(length(result.sensor_metrics))")
        println(io, "")

        plot_file = "plots/$(mast)_$(meso)_sensors.png"
        println(io, "#figure(")
        println(io, "  image(\"$plot_file\", width: 100%),")
        println(io, "  caption: [$(mast) ← $(meso) 传感器相关性分析]")
        println(io, ")")
        println(io, "")
        println(io, "#pagebreak()")
        println(io, "")
    end
end

"""
    export_csv_data(analysis_results, output_dir)

Export CSV data for each meso-mast pair.

# Arguments
- `analysis_results::Vector`: Analysis results
- `output_dir::String`: Output directory
"""
function export_csv_data(analysis_results::Vector, output_dir::String)
    data_dir = joinpath(output_dir, "data")
    mkpath(data_dir)

    for result in analysis_results
        mast = result.mast_name
        meso = result.meso_name

        df = DataFrame(
            mast_sensor = String[],
            meso_sensor = String[],
            correlation = Float64[],
            rmse = Float64[],
            sample_count = Int[]
        )

        for metrics in result.sensor_metrics
            push!(df, (
                create_sensor_short_name(metrics.mast_sensor),
                create_sensor_short_name(metrics.meso_sensor),
                metrics.correlation,
                metrics.rmse,
                metrics.sample_count
            ))
        end

        csv_file = joinpath(data_dir, "$(mast)_$(meso)_metrics.csv")
        CSV.write(csv_file, df)
        println("      ✓ Exported CSV: $(basename(csv_file))")
    end
end

end # module
