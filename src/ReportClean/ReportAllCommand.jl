module ReportAllCommand

using ..RecommendReportCleanCommand
using ..ReportCleanCommand

export execute

"""
    execute(project_dir::String)

Composite command that handles both recommendation and generation.

# Arguments
- `project_dir::String`: Path to project directory

# Workflow
1. Generates report-clean.toml in report-masts/
2. Generates report using that config

# Example
```bash
julia bin/CleanMast.jl recommend report-clean ./projects/my-project
julia bin/CleanMast.jl report clean ./projects/my-project/report-masts/report-clean.toml
```

# Note
This is a convenience wrapper. For production use, run the commands separately.
"""
function execute(project_dir::String)::Nothing
    println("Generating process clean report for: $project_dir")

    # Step 1: Generate and save report configuration
    println("Step 1: Generating report configuration...")
    RecommendReportCleanCommand.execute(project_dir)

    # Step 2: Generate actual report (loads from saved config)
    println("\nStep 2: Generating report...")
    config_path = joinpath(project_dir, "report-masts", "report-clean.toml")
    ReportCleanCommand.execute(config_path)

    println("\n✓ Process clean report generated successfully!")
end

end # module
