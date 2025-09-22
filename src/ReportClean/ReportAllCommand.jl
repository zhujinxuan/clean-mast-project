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
    
    # Step 1: Generate report configuration (internal)
    println("Step 1: Generating report configuration...")
    config = RecommendReportCleanCommand.execute_internal(project_dir)
    
    # Step 2: Generate actual report
    println("Step 2: Generating report...")
    ReportCleanCommand.execute_internal(config, project_dir)
    
    println("✓ Process clean report generated successfully!")
    println("Report location: $(joinpath(project_dir, "report-masts", "clean", "report.typ"))")
        
end

end # module
