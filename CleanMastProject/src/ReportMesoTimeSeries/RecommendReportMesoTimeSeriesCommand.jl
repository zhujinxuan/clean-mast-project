module RecommendReportMesoTimeSeriesCommand

using TOML
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration
using ...Types.ReportMesoTimeSeriesConfiguration: ReportMesoTimeSeriesConfigYAML, MesoReportMesoTimeSeriesConfigYAML, OutputConfig
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict, to_dict, strip_nothing_values
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate report-meso-timeseries.toml configuration for annual climatology analysis of meso data.

# Arguments
- `project_dir::String`: Project directory containing parse-sensors.toml

# Example
```bash
julia bin/CleanMast.jl recommend report-meso-timeseries ./projects/my-project
```

This command reads parse-sensors.toml to find meso data sources and generates a configuration
for annual climatology analysis. The configuration will be saved as:
`report-masts/report-meso-timeseries.toml`

# Algorithm
1. Read parse-sensors.toml from the project directory
2. Extract meso configurations with their output paths
3. Create analyze configuration with found meso datasets
4. Save to report-masts/report-meso-timeseries.toml
"""
function execute(project_dir::String)
    println("🔍 Generating report-meso-timeseries configuration...")

    parse_sensors_path = joinpath(project_dir, "parse-sensors.toml")
    if !isfile(parse_sensors_path)
        error("parse-sensors.toml not found in $project_dir")
    end

    @info "Reading parse-sensors.toml"
    parse_config = load_parse_sensors_config(parse_sensors_path)

    if isempty(parse_config.mesos)
        error("No meso datasets found in parse-sensors.toml")
    end

    meso_sources = extract_mesos_from_parse_sensors(parse_config)

    analyze_config = ReportMesoTimeSeriesConfigYAML(
        meso_sources,
        OutputConfig("meso-timeseries")
    )

    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    output_file = joinpath(report_masts_dir, "report-meso-timeseries.toml")
    open(output_file, "w") do io
        TOML.print(io, strip_nothing_values(Dict{String, Any}(to_dict(analyze_config))))
    end

    println("✅ Generated report-meso-timeseries.toml with $(length(meso_sources)) meso dataset(s)")
    println("📁 Configuration saved to: $output_file")
    println("📊 Data source: parse-sensors.toml")
    println("📋 Use with: julia bin/CleanMast.jl report meso-timeseries $output_file")

    return analyze_config
end

"""
    load_parse_sensors_config(config_path::String)::ParseSensorsConfiguration

Load and parse parse-sensors.toml configuration.
"""
function load_parse_sensors_config(config_path::String)::ParseSensorsConfiguration
    if !isfile(config_path)
        error("parse-sensors.toml not found at $config_path")
    end

    config_dict = load_dict(config_path)
    return from_dict(ParseSensorsConfiguration, config_dict)
end

"""
    extract_mesos_from_parse_sensors(parse_config::ParseSensorsConfiguration)::Vector{MesoReportMesoTimeSeriesConfigYAML}

Extract meso configurations from parse-sensors configuration.
If output is not explicitly defined, generates standard output paths based on meso name:
- Data: raw/{name}.parquet
- Sensors: raw/{name}.sensors.toml
Adjusts paths to be relative to report-masts/ directory.
"""
function extract_mesos_from_parse_sensors(parse_config::ParseSensorsConfiguration)::Vector{MesoReportMesoTimeSeriesConfigYAML}
    meso_sources = map(parse_config.mesos) do meso
        meso_name = isnothing(meso.name) ? splitext(basename(meso.input))[1] : meso.name

        if !isnothing(meso.output)
            adjusted_data_path = joinpath("..", meso.output.data)
            adjusted_sensors_path = joinpath("..", meso.output.sensors)
        else
            adjusted_data_path = joinpath("..", "raw", "$(meso_name).parquet")
            adjusted_sensors_path = joinpath("..", "raw", "$(meso_name).sensors.toml")
        end

        adjusted_output = TimeSeriesSource(adjusted_data_path, adjusted_sensors_path)

        MesoReportMesoTimeSeriesConfigYAML(
            meso_name,
            adjusted_output
        )
    end

    return meso_sources
end

end # module
