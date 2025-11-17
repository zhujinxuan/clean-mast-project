module ReportAllCommand

using ..RecommendReportCleanCommand
using ..ReportCleanCommand

export execute

"""
    execute(project_dir::String)

Single command that handles both recommendation and generation.
User-facing command for generating complete process clean reports.
"""
function execute(project_dir::String)::Nothing
    println("Generating process clean report for: $project_dir")

    # Step 1: Generate and save report configuration
    println("Step 1: Generating report configuration...")
    RecommendReportCleanCommand.execute(project_dir)

    # Step 2: Generate actual report (loads from saved config)
    println("\nStep 2: Generating report...")
    ReportCleanCommand.execute(project_dir)

    println("\n✓ Process clean report generated successfully!")
    println("Report location: $(joinpath(project_dir, "report-masts", "clean", "report.typ"))")
end

end # module
