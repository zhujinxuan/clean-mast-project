module RecommendReportTimeSeriesMesoCommand

using TOML
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration, from_dict
using ...Types.AnalyzeConfiguration: AnalyzeConfigYAML, MastAnalyzeConfigYAML, OutputConfig, to_dict
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate report-timeseries-meso.toml configuration for time series analysis of meso-reconstructed data.

# Arguments
- `project_dir::String`: Project directory containing reconstruct-meso.toml

# Example
```bash
julia bin/CleanMast.jl recommend report-timeseries-meso ./projects/my-project
```

This command reads reconstruct-meso.toml and generates a configuration for time series analysis
of the meso-reconstructed data output. The configuration will be saved as:
`report-masts/report-timeseries-meso.toml`

# Algorithm
1. Read reconstruct-meso.toml to get mast configurations
2. Extract output data sources (meso-reconstructed data)
3. Create analyze configuration without air density (as requested)
4. Save to report-masts/report-timeseries-meso.toml
"""
function execute(project_dir::String)
    println("🔍 Generating report-timeseries-meso configuration...")

    # 1. Read reconstruct-meso.toml
    meso_config = load_meso_config(project_dir)

    # 2. Create mast configurations for time series analysis
    analyze_masts = map(meso_config.masts) do meso_mast
        # Adjust paths to be relative to report-masts/ directory
        adjusted_data_path = if startswith(meso_mast.output.data, "./")
            "../" * meso_mast.output.data[3:end]  # Remove "./" and add "../"
        else
            "../" * meso_mast.output.data
        end

        adjusted_sensors_path = if startswith(meso_mast.output.sensors, "./")
            "../" * meso_mast.output.sensors[3:end]  # Remove "./" and add "../"
        else
            "../" * meso_mast.output.sensors
        end

        adjusted_output = TimeSeriesSource(adjusted_data_path, adjusted_sensors_path)

        MastAnalyzeConfigYAML(
            meso_mast.name,
            adjusted_output,  # Use the adjusted paths
            nothing  # No air density as requested
        )
    end

    # 3. Create analyze configuration
    analyze_config = AnalyzeConfigYAML(
        analyze_masts,
        OutputConfig("timeseries-meso"),
        nothing  # No min_plot_height specified
    )

    # 4. Save configuration to report-masts directory
    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    output_file = joinpath(report_masts_dir, "report-timeseries-meso.toml")
    open(output_file, "w") do io
        TOML.print(io, to_dict(analyze_config))
    end

    println("✅ Generated report-timeseries-meso.toml with $(length(analyze_masts)) masts")
    println("📁 Configuration saved to: $output_file")
    println("📋 Use with: julia bin/CleanMast.jl report timeseries $output_file")

    return analyze_config
end

"""
    load_meso_config(project_dir::String)::ReconstructMesoConfiguration

Load and parse reconstruct-meso.toml configuration.
"""
function load_meso_config(project_dir::String)::ReconstructMesoConfiguration
    meso_path = joinpath(project_dir, "reconstruct-meso.toml")
    if !isfile(meso_path)
        error("reconstruct-meso.toml not found in $project_dir")
    end

    config_dict = load_dict(meso_path)
    return from_dict(ReconstructMesoConfiguration, config_dict)
end

end # module