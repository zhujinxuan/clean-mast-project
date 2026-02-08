module ReportTimeSeriesCommand

using Logging
using ...Types.ReportTimeSeriesConfiguration: ReportTimeSeriesConfig, ReportTimeSeriesConfigYAML,
                                              MastReportTimeSeriesConfig, MastReportTimeSeriesConfigYAML,
                                              OutputConfig, AnalysisToggles, resolve_path
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesData
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ...TypstUtils
using ...PandocUtils
using ...CleanMastLogging: create_cleanmast_logger
using ..TimeSeriesAnalysis: analyze_all, generate_comprehensive_report

export execute, process_mast_config, load_report_timeseries_config

"""
    execute(config_path::String)

Execute time series analysis report using the provided configuration file.

# Arguments
- `config_path::String`: Path to the report timeseries configuration file (supports .yaml, .toml, .json)

# Examples
```
julia bin/CleanMast.jl report timeseries path/to/analyze.yaml
julia bin/CleanMast.jl report timeseries path/to/analyze.toml
julia bin/CleanMast.jl report timeseries path/to/analyze.json
```

The configuration file should specify:
- Multiple masts with their data files and sensor configurations
- Air density settings for each mast
- Output directory for results
- Optional min_plot_height for turbulence intensity plotting (default: 100.0m)
- Optional DOCX report settings

For each mast, the analysis includes:
- Wind temporal analysis (time series, daily/monthly patterns)
- Vertical profile analysis
- Wind direction frequency and power distribution
- Wind rose plots (frequency and power)
- Turbulence intensity analysis (with meteodyn_ti.txt files)
- Weibull distribution analysis
"""
function execute(config_path::String)
    config_dir = dirname(config_path)
    config_basename = splitext(basename(config_path))[1]

    logger = create_cleanmast_logger(
        job_name="report-timeseries",
        worker_id=1,
        config_dir=config_dir,
        config_basename=config_basename
    )
    global_logger(logger)

    @info "Loading report timeseries configuration from: $config_path"

    config = load_report_timeseries_config(config_path)

    @info "Starting analysis for $(length(config.masts)) mast(s)"

    results = analyze_all(config, config_dir, config_basename)

    @info "Generating comprehensive Typst report..."
    report_path = generate_comprehensive_report(config)
    results["report_path"] = report_path

    TypstUtils.typst_try_compile_all(config.output.path)
    PandocUtils.pandoc_try_convert_all(config.output.path)

    @info "Analysis complete. Results saved to: $(config.output.path)"

    return results
end

"""
    process_mast_config(mast_yaml::MastReportTimeSeriesConfigYAML, config_dir::String) -> MastReportTimeSeriesConfig

Process a single mast configuration by loading time series data.
Uses load_timeseries which handles path resolution, format auto-detection (CSV/Parquet),
and embedded metadata for Parquet files.
"""
function process_mast_config(mast_yaml::MastReportTimeSeriesConfigYAML, config_dir::String)::MastReportTimeSeriesConfig
    timeseries_data = load_timeseries(mast_yaml.input, config_dir)

    return MastReportTimeSeriesConfig(
        mast_yaml.name,
        timeseries_data,
        mast_yaml.airDensity
    )
end

"""
    load_report_timeseries_config(config_path::String) -> ReportTimeSeriesConfig

Load and process report timeseries configuration from a YAML, TOML, or JSON file.
Resolves all paths relative to the configuration file location and loads time series data.
"""
function load_report_timeseries_config(config_path::String)::ReportTimeSeriesConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end

    config_dir = dirname(abspath(config_path))

    config_dict = load_dict(config_path)
    config_yaml = from_dict(ReportTimeSeriesConfigYAML, config_dict)

    processed_masts = MastReportTimeSeriesConfig[]
    for mast_yaml in config_yaml.masts
        try
            push!(processed_masts, process_mast_config(mast_yaml, config_dir))
            @info "Loaded mast configuration: $(mast_yaml.name)"
        catch e
            @error "Failed to load mast $(mast_yaml.name): $e"
            rethrow(e)
        end
    end

    output_config = OutputConfig(
        resolve_path(config_yaml.output.path, config_dir)
    )

    min_plot_height = isnothing(config_yaml.min_plot_height) ? 100.0 : config_yaml.min_plot_height

    analysis_toggles = isnothing(config_yaml.analysis) ?
        AnalysisToggles(true, true, true, true, true, true, true) :
        config_yaml.analysis

    return ReportTimeSeriesConfig(
        processed_masts,
        output_config,
        config_dir,
        min_plot_height,
        analysis_toggles
    )
end

end # module