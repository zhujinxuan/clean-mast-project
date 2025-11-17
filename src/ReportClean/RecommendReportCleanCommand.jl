module RecommendReportCleanCommand

using ...Types.ProcessCleanConfig: ProcessCleanConfiguration
using ...Types.ReportCleanConfig: ReportCleanConfiguration, ReportCleanMast, ReportCleanMastGroup, ReportCleanOutput
using ...Types.CleanRules: Rule
import ...Types.Utils: from_dict, to_dict
using ...Types.MastTimeSeries: TimeSeriesSource
using ...CleanMastUtils: load_dict
using TOML

export execute

"""
    execute(project_dir::String) -> Nothing

Generate and save report-clean.toml configuration file.
User-facing command that saves the configuration to report-masts/report-clean.toml.
"""
function execute(project_dir::String)::Nothing
    println("Generating report-clean configuration...")

    # Load process-clean.toml
    process_clean_path = joinpath(project_dir, "process-clean.toml")
    if !isfile(process_clean_path)
        error("process-clean.toml not found in $project_dir")
    end

    process_config_dict = TOML.parsefile(process_clean_path)
    process_config = from_dict(ProcessCleanConfiguration, process_config_dict)

    # Generate report clean configuration (load rules during this step)
    report_config = generate_report_clean_config(process_config, project_dir)

    # Save to report-masts/report-clean.toml
    output_path = joinpath(project_dir, "report-masts", "report-clean.toml")
    mkpath(dirname(output_path))

    config_dict = to_dict(report_config)
    open(output_path, "w") do io
        TOML.print(io, config_dict)
    end

    println("✓ Report clean configuration saved to: $output_path")
    println("You can now run: report clean $project_dir")
end

"""
    load_rules(rules_config::Union{String, Array}, project_dir::String) -> Vector{Rule}

Load rules from either a file path (String) or inline configuration (Array).
"""
function load_rules(rules_config::Union{String, Array}, project_dir::String)::Vector{Rule}
    rules_dict = if isa(rules_config, String)
        load_dict(joinpath(project_dir, rules_config))
    else
        Dict("rules" => rules_config)
    end

    return [from_dict(Rule, r) for r in rules_dict["rules"]]
end

"""
    generate_report_clean_config(process_config::ProcessCleanConfiguration, project_dir::String) -> ReportCleanConfiguration

Create ReportCleanConfiguration from ProcessCleanConfiguration.
Maps process_config.masts[].input to raw masts and process_config.masts[].output to clean masts.
Loads and parses rules for each mast.
"""
function generate_report_clean_config(process_config::ProcessCleanConfiguration, project_dir::String)::ReportCleanConfiguration
    # Create raw masts from process_config.masts[].input
    raw_masts = [
        ReportCleanMast(
            name = mast.name,
            input = mast.input  # Raw data source
        )
        for mast in process_config.masts
    ]

    # Create clean masts from process_config.masts[].output
    # Load and parse rules for each mast
    clean_masts = [
        ReportCleanMast(
            name = mast.name,
            input = mast.output,  # Clean data source (output of cleaning)
            rules = load_rules(mast.rules, project_dir)
        )
        for mast in process_config.masts
    ]

    # Create configuration with default output settings
    return ReportCleanConfiguration(
        raw = ReportCleanMastGroup(masts = raw_masts),
        clean = ReportCleanMastGroup(masts = clean_masts),
        output = ReportCleanOutput()  # Uses defaults: "./report-clean", "report.typ"
    )
end

end # module
