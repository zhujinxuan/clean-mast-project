module ReportTimeSeriesCommand

using ...Types.AnalyzeConfiguration: load_analyze_config
using ...TypstUtils
using ..TimeSeriesAnalysis: analyze_all, generate_comprehensive_report

export execute

"""
    execute(config_path::String)

Execute time series analysis report using the provided analyze configuration file.

# Arguments
- `config_path::String`: Path to the analyze configuration file (supports .yaml, .toml, .json)

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
    @info "Loading analyze configuration from: $config_path"

    # Load and process the analyze configuration
    config = load_analyze_config(config_path)

    @info "Starting analysis for $(length(config.masts)) mast(s)"

    # Run all analyses
    results = analyze_all(config)

    # Generate comprehensive Typst report
    @info "Generating comprehensive Typst report..."
    report_path = generate_comprehensive_report(config)
    results["report_path"] = report_path

    # Compile Typst reports if Typst is available
    TypstUtils.typst_try_compile_all(config.output.path)

    @info "Analysis complete. Results saved to: $(config.output.path)"

    return results
end

end # module