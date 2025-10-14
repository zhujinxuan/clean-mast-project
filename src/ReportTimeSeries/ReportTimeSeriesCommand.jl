module ReportTimeSeriesCommand

using Logging
using ...Types.ReportTimeSeriesConfiguration: load_report_timeseries_config
using ...TypstUtils
using ...CleanMastLogging: create_cleanmast_logger
using ..TimeSeriesAnalysis: analyze_all, generate_comprehensive_report

export execute

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
- Optional min_plot_height for turbulence intensity plotting (default: 120.0m)
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

    @info "Analysis complete. Results saved to: $(config.output.path)"

    return results
end

end # module