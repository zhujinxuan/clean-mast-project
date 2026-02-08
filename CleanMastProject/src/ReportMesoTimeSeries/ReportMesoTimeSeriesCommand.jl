module ReportMesoTimeSeriesCommand

using Logging
using ...Types.ReportMesoTimeSeriesConfiguration: ReportMesoTimeSeriesConfig, ReportMesoTimeSeriesConfigYAML,
                                                    MesoReportMesoTimeSeriesConfig, MesoReportMesoTimeSeriesConfigYAML,
                                                    OutputConfig, resolve_path
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesData
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ...TypstUtils
using ...PandocUtils
using ...CleanMastLogging: create_cleanmast_logger
using ..AnnualClimatology: analyze_all

export execute, process_meso_config, load_report_meso_timeseries_config

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
    PandocUtils.pandoc_try_convert_all(config.output.path)

    @info "Analysis complete. Results saved to: $(config.output.path)"

    return results
end

"""
    process_meso_config(meso_yaml::MesoReportMesoTimeSeriesConfigYAML, config_dir::String) -> MesoReportMesoTimeSeriesConfig

Process a single meso configuration by loading time series data.
Uses load_timeseries which handles path resolution, format auto-detection (CSV/Parquet),
and embedded metadata for Parquet files.
"""
function process_meso_config(meso_yaml::MesoReportMesoTimeSeriesConfigYAML, config_dir::String)::MesoReportMesoTimeSeriesConfig
    timeseries_data = load_timeseries(meso_yaml.input, config_dir)

    return MesoReportMesoTimeSeriesConfig(
        meso_yaml.name,
        timeseries_data
    )
end

"""
    load_report_meso_timeseries_config(config_path::String) -> ReportMesoTimeSeriesConfig

Load and process report meso-timeseries configuration from a YAML, TOML, or JSON file.
Resolves all paths relative to the configuration file location and loads time series data.
"""
function load_report_meso_timeseries_config(config_path::String)::ReportMesoTimeSeriesConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end

    config_dir = dirname(abspath(config_path))

    config_dict = load_dict(config_path)
    config_yaml = from_dict(ReportMesoTimeSeriesConfigYAML, config_dict)

    processed_mesos = MesoReportMesoTimeSeriesConfig[]
    for meso_yaml in config_yaml.mesos
        try
            push!(processed_mesos, process_meso_config(meso_yaml, config_dir))
            @info "Loaded meso configuration: $(meso_yaml.name)"
        catch e
            @error "Failed to load meso $(meso_yaml.name): $e"
            rethrow(e)
        end
    end

    output_config = OutputConfig(
        resolve_path(config_yaml.output.path, config_dir)
    )

    return ReportMesoTimeSeriesConfig(
        processed_mesos,
        output_config,
        config_dir
    )
end

end # module
