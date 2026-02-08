module RecommendReportFrozenCommand

using TOML
using ...Types.ReportFrozenPeriodConfig: ReportFrozenPeriodConfiguration,
                                          ReportFrozenPeriodMast,
                                          ReportFrozenPeriodOutput,
                                          FrozenDetectionSettings,
                                          FrozenThresholdSet,
                                          to_dict
using ...Types.ProcessCleanConfig: ProcessCleanConfiguration
using ...Types.MastTimeSeries: TimeSeriesSource, adjust_timeseries_source_paths
using ...Types.Utils: from_dict, strip_nothing_values
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate report-frozen-period.toml configuration from process-clean.toml.
Creates configuration with default threshold sets for frozen period detection.

# Arguments
- `project_dir::String`: Project directory containing process-clean.toml

# Algorithm
1. Read process-clean.toml to get mast configurations
2. Use mast input paths (pointing to raw/ directory) for each mast
3. Filter out lidar masts (names starting with 'L')
4. Generate configuration with BOTH threshold sets (加热型, 非加热型)
5. Adjust paths for report-masts/ directory
6. Save to report-masts/report-frozen-period.toml
"""
function execute(project_dir::String)
    println("🔍 Generating report-frozen-period configuration...")

    # Read process-clean.toml to get mast configurations
    process_clean_path = joinpath(project_dir, "process-clean.toml")
    if !isfile(process_clean_path)
        error("process-clean.toml not found in $project_dir. Please run 'recommend process-clean' first.")
    end

    config_dict = load_dict(process_clean_path)
    process_clean_config = from_dict(ProcessCleanConfiguration, config_dict)

    if isempty(process_clean_config.masts)
        error("No masts found in process-clean.toml")
    end

    # Create frozen period masts configuration
    # Filter out lidar masts (names starting with 'L')
    frozen_masts = map(filter(m -> !startswith(m.name, "L"), process_clean_config.masts)) do mast
        # Use mast input paths from process-clean.toml
        # These point to the raw/ directory with parsed sensor data
        raw_source = mast.input

        # Adjust paths for report-masts/ directory
        adjusted_source = adjust_timeseries_source_paths(raw_source, "../")

        ReportFrozenPeriodMast(
            name = mast.name,
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
        TOML.print(io, strip_nothing_values(to_dict(config)))
    end

    println("✓ Generated report-frozen-period.toml with $(length(frozen_masts)) masts")
    println("📊 Threshold sets configured: $(join([t.name for t in thresholds], ", "))")
    println("📁 Configuration saved to: $output_file")

    return config
end

end # module
