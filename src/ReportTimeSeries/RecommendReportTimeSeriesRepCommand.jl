module RecommendReportTimeSeriesRepCommand

using TOML
using ...Types.RepresentativeYearConfig: RepresentativeYearConfiguration, from_dict
using ...Types.ReportTimeSeriesConfiguration: ReportTimeSeriesConfigYAML, MastReportTimeSeriesConfigYAML, OutputConfig, to_dict
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate report-timeseries-rep.toml configuration for time series analysis of representative year data.

# Arguments
- `project_dir::String`: Project directory containing representative-year.toml

# Example
```bash
julia bin/CleanMast.jl recommend report-timeseries-rep ./projects/my-project
```

This command reads representative-year.toml and generates a configuration for time series analysis
of the representative year data output. The configuration will be saved as:
`report-masts/report-timeseries-rep.toml`

# Algorithm
1. Read representative-year.toml to get mast configurations
2. Extract output data sources (representative year calibrated data)
3. Create analyze configuration without air density (as requested)
4. Save to report-masts/report-timeseries-rep.toml
"""
function execute(project_dir::String)
    println("🔍 Generating report-timeseries-rep configuration...")

    # 1. Read representative-year.toml
    rep_year_config = load_rep_year_config(project_dir)

    # 2. Create mast configurations for time series analysis
    analyze_masts = map(rep_year_config.masts) do rep_year_mast
        # Adjust paths to be relative to report-masts/ directory
        adjusted_data_path = if startswith(rep_year_mast.output.data, "./")
            "../" * rep_year_mast.output.data[3:end]  # Remove "./" and add "../"
        else
            "../" * rep_year_mast.output.data
        end

        adjusted_sensors_path = if startswith(rep_year_mast.output.sensors, "./")
            "../" * rep_year_mast.output.sensors[3:end]  # Remove "./" and add "../"
        else
            "../" * rep_year_mast.output.sensors
        end

        adjusted_output = TimeSeriesSource(adjusted_data_path, adjusted_sensors_path)

        MastReportTimeSeriesConfigYAML(
            rep_year_mast.name,
            adjusted_output,  # Use the adjusted paths
            nothing  # No air density as requested
        )
    end

    # 3. Create analyze configuration
    analyze_config = ReportTimeSeriesConfigYAML(
        analyze_masts,
        OutputConfig("./timeseries-rep"),
        nothing,  # No min_plot_height specified
        nothing   # No analysis toggles specified (all default to true)
    )

    # 4. Save configuration to report-masts directory
    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    output_file = joinpath(report_masts_dir, "report-timeseries-rep.toml")
    open(output_file, "w") do io
        TOML.print(io, to_dict(analyze_config))
    end

    println("✅ Generated report-timeseries-rep.toml with $(length(analyze_masts)) masts")
    println("📁 Configuration saved to: $output_file")
    println("📋 Use with: julia bin/CleanMast.jl report timeseries $output_file")

    return analyze_config
end

"""
    load_rep_year_config(project_dir::String)::RepresentativeYearConfiguration

Load and parse representative-year.toml configuration.
"""
function load_rep_year_config(project_dir::String)::RepresentativeYearConfiguration
    rep_year_path = joinpath(project_dir, "representative-year.toml")
    if !isfile(rep_year_path)
        error("representative-year.toml not found in $project_dir")
    end

    config_dict = load_dict(rep_year_path)
    return from_dict(RepresentativeYearConfiguration, config_dict)
end

end # module