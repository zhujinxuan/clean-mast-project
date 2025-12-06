module ReportFrozenPeriodCommand

using Dates
using DataFrames
using TOML
using ...Types.ReportFrozenPeriodConfig: ReportFrozenPeriodConfiguration, from_dict
using ...Types.ReportFrozenPeriodData: FrozenReportData, MastFrozenData
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries
using ...Types.Utils: from_dict as utils_from_dict
using ...CleanMastUtils: load_dict
using ...TypstUtils
using ...PandocUtils
using ..FrozenDetection: detect_frozen_periods_for_mast
using ..ReportGeneration: generate_frozen_period_report, generate_frozen_table, generate_missing_table

export execute

"""
    execute(config_path::String)

Execute frozen period detection and report generation.

# Arguments
- `config_path::String`: Path to report-frozen-period.toml configuration file

# Workflow
1. Load report-frozen-period.toml configuration
2. For each mast, load raw data and detect frozen periods using ALL threshold sets
3. Generate comprehensive Typst report with monthly frozen/missing tables
4. Save report to specified output directory
"""
function execute(config_path::String)
    println("🧊 Generating frozen period detection report...")

    # Use config directory as base for all path resolution
    config_dir = dirname(config_path)

    # Load configuration
    config = load_frozen_config(config_path)

    # Setup report directory (paths are relative to config file location)
    report_dir = setup_report_directory(config.output.report_dir, config_dir)

    # Detect frozen periods for each mast
    println("🔍 Detecting frozen periods...")
    mast_frozen_data = map(config.masts) do mast_config
        analyze_mast_frozen_periods(mast_config, config, config_dir)
    end

    # Create complete report data
    report_data = FrozenReportData(
        masts = mast_frozen_data,
        detection_settings = config.frozen_detection,
        generation_time = now()
    )

    # Generate Typst report with table placeholders
    println("📝 Generating Typst report...")
    typst_content = generate_frozen_period_report(report_data)

    # Render and replace table placeholders
    for mast in report_data.masts
        # Render frozen tables for each threshold
        for threshold in report_data.detection_settings.thresholds
            table_placeholder = "<!-- FROZEN_TABLE_$(mast.name)_$(threshold.name) -->"
            frozen_table = generate_frozen_table(mast, threshold.name)
            if !isnothing(frozen_table)
                table_io = IOBuffer()
                show(table_io, MIME"text/typst"(), frozen_table)
                table_content = String(take!(table_io))
                typst_content = replace(typst_content, table_placeholder => table_content)
            else
                typst_content = replace(typst_content, table_placeholder => "无冻结期检测数据。")
            end
        end

        # Render missing data table
        table_placeholder = "<!-- MISSING_TABLE_$(mast.name) -->"
        missing_table = generate_missing_table(mast)
        if !isnothing(missing_table)
            table_io = IOBuffer()
            show(table_io, MIME"text/typst"(), missing_table)
            table_content = String(take!(table_io))
            typst_content = replace(typst_content, table_placeholder => table_content)
        else
            typst_content = replace(typst_content, table_placeholder => "无缺测数据。")
        end
    end

    # Save report
    report_file = joinpath(report_dir, config.output.report_filename)
    open(report_file, "w") do io
        write(io, typst_content)
    end

    # Generate summary
    print_report_summary(report_data, report_file)

    # Compile Typst report if Typst is available
    TypstUtils.typst_try_compile(report_dir, config.output.report_filename)
    PandocUtils.pandoc_try_convert(report_dir, config.output.report_filename)

    println("✅ Frozen period detection report generated successfully!")
    println("📁 Report saved to: $report_file")
end

"""
    load_frozen_config(config_path::String)::ReportFrozenPeriodConfiguration

Load and parse report-frozen-period.toml configuration.
"""
function load_frozen_config(config_path::String)::ReportFrozenPeriodConfiguration
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end

    config_dict = load_dict(config_path)
    return from_dict(ReportFrozenPeriodConfiguration, config_dict)
end

"""
    setup_report_directory(report_dir::String, config_dir::String)::String

Create report directory and return absolute path.
"""
function setup_report_directory(report_dir::String, config_dir::String)::String
    # Resolve relative path (relative to config file location)
    abs_report_dir = isabspath(report_dir) ? report_dir : joinpath(config_dir, report_dir)

    # Create directory if it doesn't exist
    if !isdir(abs_report_dir)
        mkpath(abs_report_dir)
        println("📁 Created report directory: $abs_report_dir")
    end

    return abs_report_dir
end

"""
    analyze_mast_frozen_periods(mast_config, full_config, config_dir)::MastFrozenData

Load mast data and detect frozen periods for all threshold sets.
"""
function analyze_mast_frozen_periods(
    mast_config,
    full_config::ReportFrozenPeriodConfiguration,
    config_dir::String
)::MastFrozenData
    mast_name = mast_config.name
    println("  🏗️  Processing mast: $mast_name")

    # Load raw time series data
    raw_data = load_timeseries(mast_config.input, config_dir)

    # Detect frozen periods using ALL threshold sets
    sensor_frozen_info = detect_frozen_periods_for_mast(
        raw_data,
        full_config.frozen_detection
    )

    # Calculate analysis period and data interval
    timestamps = raw_data.df[!, :timestamp]
    analysis_start = minimum(timestamps)
    analysis_end = maximum(timestamps)

    # Calculate interval in minutes (assuming regular interval)
    interval_minutes = if nrow(raw_data.df) > 1
        time_diff = timestamps[2] - timestamps[1]
        Int(round(Dates.value(time_diff) / (1000 * 60)))
    else
        10  # Default to 10 minutes
    end

    return MastFrozenData(
        name = mast_name,
        sensor_frozen_info = sensor_frozen_info,
        analysis_start = analysis_start,
        analysis_end = analysis_end,
        interval_minutes = interval_minutes
    )
end

"""
    print_report_summary(report_data::FrozenReportData, report_file::String)

Print summary statistics to console.
"""
function print_report_summary(report_data::FrozenReportData, report_file::String)
    total_sensors = sum(length(mast.sensor_frozen_info) for mast in report_data.masts)

    # Count frozen periods across all threshold sets
    total_frozen_periods = 0
    total_frozen_points = 0

    for mast in report_data.masts
        for sensor_info in mast.sensor_frozen_info
            for (threshold_name, frozen_periods) in sensor_info.frozen_periods_by_threshold
                total_frozen_periods += length(frozen_periods)
                total_frozen_points += sum(fp.duration_points for fp in frozen_periods; init=0)
            end
        end
    end

    threshold_names = [t.name for t in report_data.detection_settings.thresholds]

    println("\n❄️  Frozen Period Detection Summary:")
    println("   Masts analyzed: $(length(report_data.masts))")
    println("   Total sensors: $total_sensors")
    println("   Threshold sets: $(join(threshold_names, ", "))")
    println("   Total frozen periods detected: $total_frozen_periods")
    println("   Total frozen data points: $total_frozen_points")
    println("   Report file: $report_file")
end

end # module
