module RecommendReportCleanCommand

using ...Types.ProcessCleanConfig: ProcessCleanConfiguration
using ...Types.ReportCleanConfig: ReportCleanConfiguration, ReportCleanMast, ReportCleanMastGroup, ReportCleanOutput
import ...Types.Utils: from_dict
using ...Types.MastTimeSeries: TimeSeriesSource
using TOML

export execute_internal

"""
    execute_internal(project_dir::String) -> ReportCleanConfiguration

Generate ReportCleanConfiguration from process-clean.toml (internal function).
Returns the configuration object directly without saving to file.
"""
function execute_internal(project_dir::String)::ReportCleanConfiguration
    println("Generating report clean configuration...")
    
    # Load process-clean.toml
    process_clean_path = joinpath(project_dir, "process-clean.toml")
    if !isfile(process_clean_path)
        error("process-clean.toml not found in $project_dir")
    end
    
    process_config_dict = TOML.parsefile(process_clean_path)
    process_config = from_dict(ProcessCleanConfiguration, process_config_dict)
    
    # Generate report clean configuration
    report_config = generate_report_clean_config(process_config)
    
    println("✓ Report clean configuration generated successfully")
    return report_config
end

"""
    generate_report_clean_config(process_config::ProcessCleanConfiguration) -> ReportCleanConfiguration

Create ReportCleanConfiguration from ProcessCleanConfiguration.
Maps process_config.masts[].input to raw masts and process_config.masts[].output to clean masts.
"""
function generate_report_clean_config(process_config::ProcessCleanConfiguration)::ReportCleanConfiguration
    # Create raw masts from process_config.masts[].input
    raw_masts = [
        ReportCleanMast(
            name = mast.name,
            input = mast.input  # Raw data source
        )
        for mast in process_config.masts
    ]
    
    # Create clean masts from process_config.masts[].output  
    clean_masts = [
        ReportCleanMast(
            name = mast.name,
            input = mast.output  # Clean data source (output of cleaning)
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
