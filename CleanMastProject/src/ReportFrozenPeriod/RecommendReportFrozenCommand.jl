module RecommendReportFrozenCommand

using TOML
using ...Types.ReportFrozenPeriodConfig: ReportFrozenPeriodConfiguration,
                                          ReportFrozenPeriodMast,
                                          ReportFrozenPeriodOutput,
                                          FrozenDetectionSettings,
                                          FrozenThresholdSet,
                                          to_dict
using ...Types.MastTimeSeries: TimeSeriesSource, adjust_timeseries_source_paths
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate report-frozen-period.toml configuration from parse-sensors.toml.
Creates configuration with default threshold sets for frozen period detection.

# Arguments
- `project_dir::String`: Project directory containing parse-sensors.toml

# Algorithm
1. Read parse-sensors.toml to get mast names and sensor formats
2. Create TimeSeriesSource pointing to raw/ directory for each mast
3. Generate configuration with BOTH threshold sets (加热型, 非加热型)
4. Adjust paths for report-masts/ directory
5. Save to report-masts/report-frozen-period.toml
"""
function execute(project_dir::String)
    println("🔍 Generating report-frozen-period configuration...")

    # Read parse-sensors.toml
    parse_sensors_config = load_parse_sensors_config(project_dir)

    if !haskey(parse_sensors_config, "masts") || isempty(parse_sensors_config["masts"])
        error("No masts found in parse-sensors.toml")
    end

    # Create frozen period masts configuration
    # Filter out lidar masts (names starting with 'L')
    frozen_masts = map(filter(m -> !startswith(m["name"], "L"), parse_sensors_config["masts"])) do mast_dict
        mast_name = mast_dict["name"]

        # Create TimeSeriesSource pointing to raw/ directory
        # Raw data is in ./raw/{mast_name}.csv
        # Sensors metadata is in ./raw/{mast_name}.sensors.toml
        raw_data_path = "./raw/$(mast_name).csv"
        raw_sensors_path = "./raw/$(mast_name).sensors.toml"

        # Adjust paths for report-masts/ directory (convert "./raw/" to "../raw/")
        raw_source = TimeSeriesSource(raw_data_path, raw_sensors_path)
        adjusted_source = adjust_timeseries_source_paths(raw_source, "../")

        ReportFrozenPeriodMast(
            name = mast_name,
            input = adjusted_source
        )
    end

    # Create default threshold sets based on Chinese wind energy standard
    # Reference: F.1 直接计算冰冻等效的发电量折减
    thresholds = [
        # 非加热型传感器 (Non-heated sensors) - stricter wind stability checks
        FrozenThresholdSet(
            name = "非加热型",
            temperature_threshold = 2.0,
            windspeed_change_threshold = 0.1,
            winddirection_change_threshold = 5.0,
            min_duration_seconds = 21600  # 6 hours
        ),
        # 加热型传感器 (Heated sensors) - only temperature and RH checks
        # Note: For heated sensors, wind stability checks are skipped
        # Only T < 2°C and RH < 80% conditions apply
        # No minimum duration requirement for heated sensors
        FrozenThresholdSet(
            name = "加热型",
            temperature_threshold = 2.0,
            windspeed_change_threshold = 999.0,  # Effectively disabled (very high threshold)
            winddirection_change_threshold = 360.0,  # Effectively disabled
            rh_threshold = 80.0  # RH < 80% for heated sensors
            # min_duration_seconds not specified - no duration requirement
        )
    ]

    # Create frozen detection settings
    frozen_detection = FrozenDetectionSettings(thresholds = thresholds)

    # Create final configuration
    config = ReportFrozenPeriodConfiguration(
        masts = frozen_masts,
        frozen_detection = frozen_detection,
        output = ReportFrozenPeriodOutput(
            report_dir = "./frozen-period",
            report_filename = "frozen-period-report.typ"
        )
    )

    # Save configuration to report-masts directory
    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    output_file = joinpath(report_masts_dir, "report-frozen-period.toml")
    open(output_file, "w") do io
        TOML.print(io, to_dict(config))
    end

    println("✓ Generated report-frozen-period.toml with $(length(frozen_masts)) masts")
    println("📊 Threshold sets configured: $(join([t.name for t in thresholds], ", "))")
    println("📁 Configuration saved to: $output_file")

    return config
end

"""
    load_parse_sensors_config(project_dir::String)::Dict{String, Any}

Load and parse parse-sensors.toml configuration.
"""
function load_parse_sensors_config(project_dir::String)::Dict{String, Any}
    parse_sensors_path = joinpath(project_dir, "parse-sensors.toml")
    if !isfile(parse_sensors_path)
        error("parse-sensors.toml not found in $project_dir")
    end

    return load_dict(parse_sensors_path)
end

end # module
