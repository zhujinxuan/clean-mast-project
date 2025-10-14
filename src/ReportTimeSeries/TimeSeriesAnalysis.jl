module TimeSeriesAnalysis

using DataFrames
using CSV
using Statistics
using Dates
using ColorSchemes
using DataFramesMeta
using GLM
using StatsBase: mean, fit, Histogram
using YAML
using Logging

using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path, AirDensityConfig
using ...CleanMastLogging: create_cleanmast_logger
using ...CleanMastLogging.CleanMastLogger.LogRotation: archive_all_worker_logs

# Import functions from sub-modules
import ..WindTemporal: analyze_all_temporal
import ..Vertical: analyze_all_vertical
import ..WindFrequency: analyze_all_frequency
import ..WindRose: analyze_all_wind_rose
import ..Turbulence: analyze_all_turbulence
import ..Weibull: analyze_weibull_distribution
import ..FiftyYearsExtremeWind: analyze_fifty_years_extreme_wind

export analyze_all, generate_comprehensive_report

"""
    analyze_all(config::AnalyzeConfig, config_dir::String, config_basename::String)

Run all available analyses for all masts in the configuration in parallel.

# Arguments
- `config::AnalyzeConfig`: Analysis configuration with multiple masts
- `config_dir::String`: Configuration directory for log files
- `config_basename::String`: Base name for log files

# Returns
- `Dict{String, Any}`: Dictionary with results from all analyses
"""
function analyze_all(config::AnalyzeConfig, config_dir::String, config_basename::String)
    results = Dict{String, Any}()

    @info "Starting comprehensive time series analysis for $(length(config.masts)) mast(s)"

    mkpath(config.output.path)

    enabled_analyses = [
        (config.analysis.wind_temporal, "wind_temporal"),
        (config.analysis.vertical_profile, "vertical_profile"),
        (config.analysis.wind_frequency, "wind_frequency"),
        (config.analysis.wind_rose, "wind_rose"),
        (config.analysis.turbulence, "turbulence"),
        (config.analysis.weibull, "weibull"),
        (config.analysis.fifty_years_extreme, "fifty_years_extreme")
    ]

    tasks = [
        (analysis_type, mast)
        for (enabled, analysis_type) in enabled_analyses
        if enabled
        for mast in config.masts
    ]

    total_tasks = length(tasks)
    @info "Created analysis task queue" total_tasks=total_tasks

    if total_tasks == 0
        @info "No analyses enabled or no masts configured"
        return results
    end

    @info "Archiving old worker logs before parallel execution"
    archive_all_worker_logs(config_dir, config_basename, Threads.nthreads())

    @info "Pre-creating loggers for all worker threads"
    worker_loggers = Dict{Int, Any}()
    for worker_id in 1:Threads.nthreads()
        worker_loggers[worker_id] = create_cleanmast_logger(
            job_name="analyze-mast",
            worker_id=worker_id,
            config_dir=config_dir,
            config_basename=config_basename
        )
    end

    task_results = Vector{Any}(undef, total_tasks)

    Threads.@threads for idx in 1:total_tasks
        worker_id = Threads.threadid()
        worker_logger = worker_loggers[worker_id]

        with_logger(worker_logger) do
            analysis_type, mast_config = tasks[idx]

            @info "Running analysis" index=idx total=total_tasks type=analysis_type mast=mast_config.name

            try
                single_mast_config = AnalyzeConfig(
                    [mast_config],
                    config.output,
                    config.configDir,
                    config.min_plot_height,
                    config.analysis
                )

                result = nothing
                if analysis_type == "wind_temporal"
                    result = analyze_all_temporal(single_mast_config)
                elseif analysis_type == "vertical_profile"
                    result = analyze_all_vertical(single_mast_config)
                elseif analysis_type == "wind_frequency"
                    result = analyze_all_frequency(single_mast_config)
                elseif analysis_type == "wind_rose"
                    result = analyze_all_wind_rose(single_mast_config)
                elseif analysis_type == "turbulence"
                    result = analyze_all_turbulence(single_mast_config)
                elseif analysis_type == "weibull"
                    result = analyze_weibull_distribution(single_mast_config)
                elseif analysis_type == "fifty_years_extreme"
                    result = analyze_fifty_years_extreme_wind(single_mast_config)
                end

                task_results[idx] = (analysis_type, mast_config.name, result)
                @info "Analysis completed" type=analysis_type mast=mast_config.name
            catch e
                @error "Analysis failed" type=analysis_type mast=mast_config.name exception=(e, catch_backtrace())
                rethrow(e)
            end
        end
    end

    for (analysis_type, mast_name, result) in task_results
        if !haskey(results, analysis_type)
            results[analysis_type] = Dict{String, Any}()
        end
        if !isnothing(result)
            merge!(results[analysis_type], result)
        end
    end

    @info "Analysis complete for all masts"

    return results
end

"""
    generate_comprehensive_report(config::AnalyzeConfig)

Generate a comprehensive Typst report that includes all individual Typst files
created by the various analysis modules for all masts.

# Arguments
- `config::AnalyzeConfig`: Analysis configuration with multiple masts

# Returns
- `String`: Path to the generated main Typst report file
"""
function generate_comprehensive_report(config::AnalyzeConfig)
    # Define the main report file path
    report_path = joinpath(config.output.path, "comprehensive_analysis_report.typ")

    @info "Generating comprehensive Typst report at: $report_path"

    # Open the main report file
    open(report_path, "w") do io
        # Write document header
        write(io, """
        // Comprehensive Wind Mast Analysis Report
        // Generated by CleanMastProject.jl
        // Date: $(Dates.format(now(), "yyyy-mm-dd HH:MM:SS"))

        #set document(
          title: "Wind Mast Comprehensive Analysis Report",
          author: "CleanMastProject Analysis System",
        )

        #set page(
          paper: "a4",
          margin: (x: 2cm, y: 2.5cm),
          numbering: "1",
          number-align: center,
        )

        #set heading(numbering: "1.")

        #set par(justify: true)

        // Title page
        #align(center)[
          #v(5cm)
          #text(size: 24pt, weight: "bold")[风能资源评估综合分析报告]

          #v(1cm)

          #text(size: 18pt)[Wind Resource Assessment Comprehensive Analysis Report]

          #v(2cm)

          #text(size: 14pt)[
            项目包含 $(length(config.masts)) 个测风塔数据分析
          ]

          #v(4cm)

          #text(size: 12pt)[
            生成日期: #datetime.today().display("[year]年[month]月[day]日")
          ]
        ]

        #pagebreak()

        // Table of contents
        #outline(
          title: [目录 / Table of Contents],
          indent: 1em,
          depth: 3,
        )

        #pagebreak()

        // Executive summary
        = 执行摘要 / Executive Summary

        本报告包含了 $(length(config.masts)) 个测风塔的综合风能资源分析结果，涵盖以下分析内容：

        - 风速时序分析 (Wind Speed Temporal Analysis)
        - 垂直风廓线分析 (Vertical Wind Profile Analysis)
        - 风向频率分析 (Wind Direction Frequency Analysis)
        - 风玫瑰图分析 (Wind Rose Analysis)

        """)

        # Process each mast
        for (idx, mast) in enumerate(config.masts)
            write(io, """

            #pagebreak()

            = 测风塔 $(mast.name) 分析结果

            """)

            # Define the expected Typst files and their locations
            typst_files = [
                ("wind-temporal", "wind-temporal.typ"),
                ("wind-rose", "wind-rose.typ"),
                ("vertical-profile", "wind_shear_exponent.typ"),
                ("wind-power-frequency", "wind-frequency.typ"),
                ("weibull", "weibull.typ"),
                ("turbulence", "turbulence.typ"),
                ("fifty-years", "fifty-years.typ")
            ]

            # Include each Typst file if it exists
            for (dir_name, file_name) in typst_files
                file_path = joinpath(get_output_path(config, mast.name, dir_name), file_name)

                if isfile(file_path)
                    # Calculate relative path from report location
                    rel_path = relpath(file_path, config.output.path)
                    # Convert Windows path separators to forward slashes for Typst
                    rel_path = replace(rel_path, "\\" => "/")


                    write(io, """
                    #include "$(rel_path)"

                    """)
                else
                    @debug "Typst file not found (analysis may have been skipped): $file_path"
                end
            end

            # Add page break between masts (except for the last one)
            if idx < length(config.masts)
                write(io, "\n#pagebreak()\n")
            end
        end
    end

    @info "Comprehensive Typst report generated successfully at: $report_path"

    return report_path
end

end # module