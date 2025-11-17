module ReportCleanCommand

using DataFrames
using ...Types.ReportCleanConfig: ReportCleanConfiguration
using ...Types.ReportCleanData: MastReportData, SensorCoverageInfo, ReportGenerationData, DetectedInterval
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesData
using ...Types.ViolationData: ViolationAnalysisData, ProcessingInfo, ViolationSummary, ViolationColumn
using ...Types.CleanRules: Rule
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ...TypstUtils
using YAML
using Dates

# Import interval detection functionality
using ...TimeSeriesProcessing.IntervalDetection: detect_representative_interval, calculate_expected_points

# Import modular report components
using ..SensorInventoryReport
using ..DataCoverageReport
using ..ViolationAnalysisReport
using ..MonthlyCoverageTable
using ..LayerDiffParametersTable

export execute

"""
    execute(project_dir::String)

Generate report from report-clean.toml configuration file.
User-facing command that loads configuration from report-masts/report-clean.toml.
"""
function execute(project_dir::String)::Nothing
    println("Loading report configuration...")

    # Load report-clean.toml
    config_path = joinpath(project_dir, "report-masts", "report-clean.toml")
    if !isfile(config_path)
        error("report-clean.toml not found at: $config_path\nPlease run 'recommend report-clean $project_dir' first")
    end

    config_dict = load_dict(config_path)
    config = from_dict(ReportCleanConfiguration, config_dict)

    println("✓ Configuration loaded from: $config_path")

    # Generate report
    execute_internal(config, project_dir)
end

"""
    execute_internal(config::ReportCleanConfiguration, project_dir::String)

Generate actual Typst report from configuration (internal function).
Loads data, processes violation summaries, and generates Chinese Typst report.
"""
function execute_internal(config::ReportCleanConfiguration, project_dir::String)::Nothing
    println("Generating process clean report...")
    
    # Setup report directory
    report_dir = setup_report_directory(config.output.report_dir, project_dir)
    
    # Setup logging
    log_file = joinpath(report_dir, "generation.log")
    err_file = joinpath(report_dir, "generation.err")
    
    # Redirect logging to files
    open(log_file, "w") do log_io
        open(err_file, "w") do err_io
            redirect_stdout(log_io) do
                redirect_stderr(err_io) do
                    generate_report_content(config, project_dir, report_dir)
                end
            end
        end
    end
    
    println("✓ Report generated successfully!")
    println("Report location: $(joinpath(report_dir, config.output.report_filename))")

    # Compile Typst report if Typst is available
    TypstUtils.typst_try_compile(report_dir, config.output.report_filename)

end

"""
    setup_report_directory(report_dir::String, project_dir::String) -> String

Create report directory and return absolute path.
"""
function setup_report_directory(report_dir::String, project_dir::String)::String
    # Resolve report directory path
    abs_report_dir = isabspath(report_dir) ? report_dir : joinpath(project_dir, report_dir)
    
    # Create directory structure
    mkpath(abs_report_dir)
    mkpath(joinpath(abs_report_dir, "plots"))
    
    return abs_report_dir
end

"""
    generate_report_content(config::ReportCleanConfiguration, project_dir::String, report_dir::String)

Main report generation logic. Loads data and generates all report sections.
"""
function generate_report_content(config::ReportCleanConfiguration, project_dir::String, report_dir::String)::Nothing
    println("Loading data and generating report sections...")

    # Collect data for all masts
    mast_data = map(zip(config.raw.masts, config.clean.masts)) do (raw_mast, clean_mast)
        println("Processing mast: $(raw_mast.name)")

        # Load raw and clean data using existing functions (automatic path resolution)
        raw_data = load_timeseries(raw_mast.input, project_dir)
        clean_data = load_timeseries(clean_mast.input, project_dir)

        # Load violation data from YAML
        violation_file = joinpath(project_dir, "process-stats", "process-clean-$(raw_mast.name).yaml")
        violation_data = load_violation_data(violation_file)

        # Detect representative interval and calculate expected points
        raw_interval = detect_representative_interval(raw_data)
        expected_points = calculate_expected_points(raw_data, raw_interval)

        # Create proper DetectedInterval object
        detected_interval = DetectedInterval(
            interval = raw_interval,
            confidence = 1.0,
            description = "Auto-detected from raw data"
        )

        # Create MastReportData structure
        MastReportData(
            name = raw_mast.name,
            raw_data = raw_data,
            clean_data = clean_data,
            sensor_coverage = SensorCoverageInfo[],  # Will be populated by report generation
            violation_data = violation_data,
            detected_interval = detected_interval,
            expected_points = expected_points
        )
    end

    # Get rules from the first clean mast (rules are already loaded in config)
    rules = get_rules_from_config(config)

    # Generate Typst report with plots directory
    plots_dir = joinpath(report_dir, "plots")
    typst_content = generate_typst_report(mast_data, plots_dir, rules)

    # Save report
    report_file = joinpath(report_dir, config.output.report_filename)
    open(report_file, "w") do io
        write(io, typst_content)
    end

    println("Report saved to: $report_file")
end

"""
    get_rules_from_config(config::ReportCleanConfiguration) -> Vector{Rule}

Get rules from the first clean mast configuration.
Rules are already loaded as Vector{Rule} during the recommend phase.
Assumes all masts use the same rules.
"""
function get_rules_from_config(config::ReportCleanConfiguration)::Vector{Rule}
    if isempty(config.clean.masts)
        @warn "No clean masts found in configuration"
        return Rule[]
    end

    first_mast = config.clean.masts[1]

    if isnothing(first_mast.rules)
        @warn "No rules specified in configuration for mast $(first_mast.name)"
        return Rule[]
    end

    println("Using $(length(first_mast.rules)) rules from configuration")

    return first_mast.rules
end

"""
    load_violation_data(violation_file::String) -> ViolationAnalysisData

Load violation data from YAML file and convert to properly typed structure.
"""
function load_violation_data(violation_file::String)::ViolationAnalysisData
    if !isfile(violation_file)
        @warn "Violation file not found: $violation_file"
        # Return empty violation data structure
        return ViolationAnalysisData(
            processing_info = ProcessingInfo(
                mast_name = "unknown",
                start_time = "1970-01-01T00:00:00",
                end_time = "1970-01-01T00:00:00",
                total_timestamps = 0
            ),
            violation_summary = ViolationSummary(
                total_violations = 0,
                violation_percentage = 0.0
            ),
            violations_by_column = ViolationColumn[]
        )
    end

    yaml_data = load_dict(violation_file)
    return from_dict(ViolationAnalysisData, Dict(yaml_data))
end

"""
    generate_typst_report(mast_data::Vector{MastReportData}, plots_dir::String, rules::Vector{Rule}) -> String

Generate Chinese Typst report content from mast data using modular components.
"""
function generate_typst_report(mast_data::Vector{MastReportData}, plots_dir::String, rules::Vector{Rule})::String
    # Generate header and executive summary
    header_section = """
#set page(paper: "a4", margin: 2cm)
#set heading(numbering: "1.")

= 数据清洗报告

== 1. 执行摘要

本报告分析了 $(length(mast_data)) 座测风塔的数据清洗结果。

$(join([
    let processing_info = mast.violation_data.processing_info
        start_time = processing_info.start_time
        end_time = processing_info.end_time
        "- $(mast.name): $start_time 至 $end_time"
    end
    for mast in mast_data
], "\n"))
"""

    # Generate modular sections
    sensor_inventory_section = generate_sensor_inventory_section(mast_data)
    data_coverage_section = generate_data_coverage_section(mast_data, plots_dir)
    monthly_coverage_section = generate_monthly_coverage_table(mast_data)

    # Generate layer difference parameters table (if rules available)
    layer_diff_section = if !isempty(rules) && !isempty(mast_data)
        sensors = mast_data[1].clean_data.sensors
        generate_layer_diff_parameters_section(rules, sensors)
    else
        ""
    end

    violation_analysis_section = generate_violation_analysis_section(mast_data, plots_dir)

    # Generate footer
    footer_section = """

== 结论

数据清洗过程成功完成，共处理 $(length(mast_data)) 座测风塔的数据。

---
_报告生成时间：$(now())_
_配置文件：process-clean.toml_
"""

    # Combine all sections
    return join([
        header_section,
        sensor_inventory_section,
        layer_diff_section,
        data_coverage_section,
        monthly_coverage_section,
        violation_analysis_section,
        footer_section
    ], "\n")
end

end # module
