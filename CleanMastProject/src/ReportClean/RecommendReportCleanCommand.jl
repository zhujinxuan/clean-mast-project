module RecommendReportCleanCommand

using ...Types.ProcessCleanConfig: ProcessCleanConfiguration
using ...Types.ReportCleanConfig: ReportCleanConfiguration, to_report_clean_config
import ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using TOML

export execute

"""
    execute(project_dir::String) -> Nothing

Generate and save report-clean.toml configuration file.
User-facing command that saves the configuration to report-masts/report-clean.toml.

# Workflow
1. Loads process-clean.toml from project directory
2. Converts ProcessCleanConfiguration to ReportCleanConfiguration
3. Adjusts paths to be relative to report-masts/ directory
4. Loads and parses rules for each mast
5. Saves configuration to report-masts/report-clean.toml

# Example
```bash
julia bin/CleanMast.jl recommend report-clean ./projects/my-project
```
"""
function execute(project_dir::String)::Nothing
    println("Generating report-clean configuration...")

    # Load process-clean.toml
    process_clean_path = joinpath(project_dir, "process-clean.toml")
    if !isfile(process_clean_path)
        error("process-clean.toml not found in $project_dir")
    end

    process_config_dict = load_dict(process_clean_path)
    process_config = from_dict(ProcessCleanConfiguration, process_config_dict)

    # Convert to report clean configuration
    # Use "../" prefix since config will be saved in report-masts/ subdirectory
    report_config = to_report_clean_config(process_config, project_dir, "../")

    # Save to report-masts/report-clean.toml
    output_path = joinpath(project_dir, "report-masts", "report-clean.toml")
    mkpath(dirname(output_path))

    config_dict = to_dict(report_config)
    open(output_path, "w") do io
        TOML.print(io, config_dict)
    end

    println("✓ Report clean configuration saved to: $output_path")
    println("You can now run: report clean $output_path")
end

end # module
