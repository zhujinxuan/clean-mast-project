module ReportMesoTimeSeriesCommand

using Logging
using ...Types.ReportMesoTimeSeriesConfiguration: load_report_meso_timeseries_config
using ...TypstUtils
using ...CleanMastLogging: create_cleanmast_logger
using ..AnnualClimatology: analyze_all

export execute

"""
    execute(config_path::String)

Execute meso-timeseries analysis report using the provided configuration file.

# Arguments
- `config_path::String`: Path to the report-meso-timeseries configuration file (supports .yaml, .toml, .json)

# Examples
```
julia bin/CleanMast.jl report meso-timeseries path/to/report-meso-timeseries.yaml
julia bin/CleanMast.jl report meso-timeseries path/to/report-meso-timeseries.toml
julia bin/CleanMast.jl report meso-timeseries path/to/report-meso-timeseries.json
```

The configuration file should specify:
- Multiple meso datasets with their data files and sensor configurations
- Output directory for results

For each meso, the analysis includes:
- Annual wind speed climatology analysis
- Table of annual means and differences from climatology
- Plot showing annual timeseries with climatology line
- Typst report with summary statistics
"""
function execute(config_path::String)
    config_dir = dirname(config_path)
    config_basename = splitext(basename(config_path))[1]

    logger = create_cleanmast_logger(
        job_name="report-meso-timeseries",
        worker_id=1,
        config_dir=config_dir,
        config_basename=config_basename
    )
    global_logger(logger)

    @info "Loading report meso-timeseries configuration from: $config_path"

    config = load_report_meso_timeseries_config(config_path)

    @info "Starting analysis for $(length(config.mesos)) meso dataset(s)"

    results = analyze_all(config)

    @info "Compiling Typst reports..."
    TypstUtils.typst_try_compile_all(config.output.path)

    @info "Analysis complete. Results saved to: $(config.output.path)"

    return results
end

end # module
