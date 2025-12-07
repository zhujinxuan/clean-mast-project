"""
    CommandReportReconstructMeso.jl

Main command implementation for report-reconstruct-meso.
Orchestrates complete workflow: config loading → data loading → analysis → visualization → report generation.
"""
module CommandReportReconstructMeso

using DataFrames
using Dates
using Statistics
using Logging

using ...Types.ReportReconstructMesoConfig: ReportReconstructMesoConfiguration, from_dict
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ...TypstUtils
using ...PandocUtils
using ...CleanMastLogging: create_cleanmast_logger, WorkerLoggerManager, get_logger
using ...CleanMastLogging.CleanMastLogger.LogRotation: archive_all_worker_logs

using ..AnalysisCore: load_all_data, analyze_meso_mast_pair, AnalyzeMesoMastResult
using ..DataVisualization: create_meso_mast_plots
using ..ReportGeneration: generate_typst_report, export_csv_data

export execute

"""
    execute(config_path::String)

Execute the report-reconstruct-meso command.

# Arguments
- `config_path::String`: Path to report-reconstruct-meso.toml configuration file

# Workflow
1. Load and validate configuration
2. Create output directory structure
3. Load all mast and meso time series data
4. Analyze all meso-mast pairs
5. Generate individual plots for each pair
6. Export CSV data for each pair
7. Generate comprehensive Chinese Typst report

# Example
```bash
julia bin/CleanMast.jl report reconstruct-meso report-masts/report-reconstruct-meso.toml
```

This generates:
- Chinese Typst report with embedded plots and tables
- Individual PNG plots for each meso-mast pair
- Individual CSV data exports for each pair
- Comprehensive analysis summary
"""
function execute(config_path::String)
    config_dict = load_dict(config_path)
    config = from_dict(ReportReconstructMesoConfiguration, config_dict)

    config_dir = dirname(config_path)
    config_basename = splitext(basename(config_path))[1]

    logger = create_cleanmast_logger(
        job_name="report-reconstruct-meso",
        worker_id=1,
        config_dir=config_dir,
        config_basename=config_basename
    )
    global_logger(logger)

    @info "Starting meso-mast reconstruction quality analysis"

    @info "Configuration loaded" masts=length(config.masts) mesos=length(config.mesos) output=config.analyze.output_dir

    output_dir = joinpath(config_dir, config.analyze.output_dir)
    create_output_directories(output_dir)

    @info "Loading time series data"
    mast_data, meso_data = load_all_data(config, config_dir)
    @info "Loaded time series data" masts=length(mast_data) mesos=length(meso_data)

    @info "Archiving old worker logs before parallel execution"
    archive_all_worker_logs(config_dir, config_basename, Threads.nthreads())

    @info "Analyzing meso-mast relationships"
    results = analyze_all_pairs_parallel(config, mast_data, meso_data, config_dir, config_basename)
    @info "Completed analysis" pairs=length(results)

    @info "Generating visualizations"
    create_meso_mast_plots(results, output_dir, mast_data, meso_data, config_dir, config_basename)

    @info "Exporting data"
    export_csv_data(results, output_dir)

    @info "Generating report"
    generate_typst_report(results, output_dir)

    print_completion_summary(results, output_dir)

    @info "Compiling Typst report"
    TypstUtils.typst_try_compile(output_dir, "report.typ")
    PandocUtils.pandoc_try_convert(output_dir, "report.typ")

    @info "Meso-mast reconstruction quality analysis completed successfully"
end

"""
    create_output_directories(output_dir)

Create the complete output directory structure.

# Arguments
- `output_dir::String`: Base output directory
"""
function create_output_directories(output_dir::String)
    @info "Creating output directory structure" path=output_dir

    mkpath(output_dir)
    mkpath(joinpath(output_dir, "data"))
    mkpath(joinpath(output_dir, "plots"))

    @info "Output structure created" path=output_dir
end

"""
    analyze_all_pairs_parallel(config, mast_data, meso_data, config_dir, config_basename)

Analyze all possible meso-mast combinations in parallel with per-worker logging.

# Arguments
- `config`: ReportReconstructMesoConfiguration
- `mast_data::Dict`: Dictionary mapping mast names to TimeSeriesData
- `meso_data::Dict`: Dictionary mapping meso names to TimeSeriesData
- `config_dir::String`: Configuration directory for log files
- `config_basename::String`: Base name for log files

# Returns
- `Vector{AnalyzeMesoMastResult}`: Array of analysis results (errors if any pair fails)
"""
function analyze_all_pairs_parallel(config, mast_data::Dict, meso_data::Dict, config_dir::String, config_basename::String)
    pairs = []
    for mast_config in config.masts
        for meso_config in config.mesos
            push!(pairs, (mast_config, meso_config))
        end
    end

    total_pairs = length(pairs)
    @info "Created analysis task queue" total_pairs=total_pairs

    @info "Creating worker logger manager"
    manager = WorkerLoggerManager(
        config_dir,
        config_basename
    )

    results = Vector{Union{AnalyzeMesoMastResult, Nothing}}(undef, total_pairs)

    Threads.@threads for idx in 1:total_pairs
        worker_id = Threads.threadid()
        worker_logger = get_logger(manager, worker_id)

        with_logger(worker_logger) do
            mast_config, meso_config = pairs[idx]
            mast_name = mast_config.name
            meso_name = meso_config.name

            @info "Analyzing pair" index=idx total=total_pairs mast=mast_name meso=meso_name

            try
                if !haskey(mast_data, mast_name)
                    @error "Mast data not found" mast=mast_name
                    error("Mast data not found: $(mast_name)")
                end

                if !haskey(meso_data, meso_name)
                    @error "Meso data not found" meso=meso_name
                    error("Meso data not found: $(meso_name)")
                end

                mast_ts = mast_data[mast_name]
                meso_ts = meso_data[meso_name]

                result = analyze_meso_mast_pair(
                    mast_ts,
                    meso_ts,
                    mast_name,
                    meso_name,
                    mast_config.wind_speed_report_heights,
                    meso_config.wind_speed_report_heights
                )

                results[idx] = result
                @info "Pair analysis completed" mast=mast_name meso=meso_name sensor_pairs=length(result.sensor_metrics)
            catch e
                @error "Pair analysis failed" mast=mast_name meso=meso_name exception=(e, catch_backtrace())
                rethrow(e)
            end
        end
    end

    return results
end

"""
    print_completion_summary(results, output_dir, config)

Print detailed completion summary with file listings and statistics.

# Arguments
- `results::Vector`: Valid analysis results
- `output_dir::String`: Output directory path
- `config`: Configuration object
"""
function print_completion_summary(results::Vector, output_dir::String)
    @info "Analysis Summary" pairs=length(results)

    total_sensor_pairs = sum(length(r.sensor_metrics) for r in results)
    if total_sensor_pairs > 0
        all_metrics = vcat([r.sensor_metrics for r in results]...)
        best_corr = maximum(m.correlation for m in all_metrics)
        avg_corr = mean(m.correlation for m in all_metrics)
        best_rmse = minimum(m.rmse for m in all_metrics)
        avg_rmse = mean(m.rmse for m in all_metrics)

        @info "Sensor pair statistics" total=total_sensor_pairs best_corr=round(best_corr, digits=3) avg_corr=round(avg_corr, digits=3) best_rmse=round(best_rmse, digits=2) avg_rmse=round(avg_rmse, digits=2)
    end

    avg_overlap = mean(r.overlap_days for r in results)
    @info "Average overlap" days=round(avg_overlap, digits=1)

    @info "Generated files" report=joinpath(output_dir, "report.typ") csv_files=length(results) plot_files=length(results)

end

end # module
