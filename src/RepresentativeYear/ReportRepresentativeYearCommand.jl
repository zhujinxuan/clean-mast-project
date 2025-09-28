"""
    ReportRepresentativeYearCommand.jl

CLI command for generating representative year calibration analysis reports.
Provides comprehensive analysis of climatology selection, calibration effectiveness,
and 16-sector performance metrics with detailed Typst report generation.
"""
module ReportRepresentativeYearCommand

using ...TypstUtils
using ..ReportGeneration: load_representative_year_analysis_data, generate_representative_year_report

export execute

"""
    execute(project_dir::String)

Generate comprehensive representative year calibration analysis report.

# Arguments
- `project_dir::String`: Project directory containing representative year results and configuration

# Description
This command analyzes representative year calibration results and generates:
- Comprehensive Typst report with bilingual support (Chinese/English)
- Executive summary of calibration status across all mast-meso pairs
- Detailed climatology vs training vs representative year comparisons  
- 16-sector analysis tables with slopes, intercepts, and data quality metrics
- Sensor-level calibration effectiveness analysis
- Supporting CSV data files for further analysis

# Requirements
The project directory must contain:
- `representative-year.toml` - Configuration file
- `process-stats/representative-year-info-<mast>.yaml` - Calibration results (if applied)
- Input data files as specified in configuration
- Meso data sources for climatology analysis

# Output Structure
```
project-dir/
├── representative-year-report/
│   ├── report.typ                          # Main Typst report
│   ├── tables/
│   │   ├── <mast>_<meso>_sectors.typ      # 16-sector analysis tables
│   │   └── <mast>_<meso>_sensors.typ      # Sensor calibration tables  
│   └── data/
│       ├── calibration_summary.csv         # Overall calibration status
│       └── sector_analysis.csv             # Detailed 16-sector data
```

# Example Usage
```bash
julia bin/CleanMast.jl report representative-year my-project
```

# Error Handling
- Validates that representative-year.toml exists
- Warns about missing calibration results files (treats as calibration not needed)
- Skips mast-meso pairs with insufficient sensor data
- Provides detailed error messages for troubleshooting
"""
function execute(project_dir::String)
    println("🔍 Representative Year Calibration Analysis Report")
    println("=" ^ 50)
    
    # Validate input
    if !isdir(project_dir)
        error("Project directory not found: $project_dir")
    end
    
    config_path = joinpath(project_dir, "representative-year.toml")
    if !isfile(config_path)
        error("Representative year configuration not found: $config_path")
    end
    
    try
        println("📊 Step 1/3: Loading and analyzing calibration data...")
        analysis_results = load_representative_year_analysis_data(project_dir)
        
        if isempty(analysis_results)
            error("No valid mast-meso pairs found for analysis")
        end
        
        println("📄 Step 2/3: Generating comprehensive report...")
        report_path = generate_representative_year_report(analysis_results, project_dir)
        
        println("📋 Step 3/3: Report generation completed successfully!")
        println()
        println("📈 Analysis Summary:")
        println("  • Analyzed mast-meso pairs: $(length(analysis_results))")
        
        calibrated_count = count(r -> r.calibration_applied, analysis_results)
        not_needed_count = length(analysis_results) - calibrated_count
        
        println("  • Calibration applied: $calibrated_count")
        println("  • Calibration not needed: $not_needed_count")
        
        # Show performance metrics
        if calibrated_count > 0
            calibrated_results = filter(r -> r.calibration_applied, analysis_results)
            avg_threshold_deviation = mean(r.threshold_deviation for r in calibrated_results)
            println("  • Average threshold deviation: $(round(avg_threshold_deviation, digits=1))%")
            
            if any(r -> !isnothing(r.representative_year_mean), calibrated_results)
                effectiveness_values = [r.performance_metrics["calibration_effectiveness"] 
                                      for r in calibrated_results 
                                      if haskey(r.performance_metrics, "calibration_effectiveness")]
                if !isempty(effectiveness_values)
                    avg_effectiveness = mean(effectiveness_values)
                    println("  • Average calibration effectiveness: $(round(avg_effectiveness, digits=1))%")
                end
            end
        end
        
        println()
        println("📁 Output Files:")
        println("  📋 Main report: $(basename(report_path))")
        println("  📊 Report directory: $(dirname(report_path))")
        println("  💾 Supporting data: tables/ and data/ subdirectories")
        
        # Compile Typst report if Typst is available
        report_dir = dirname(report_path)
        report_filename = basename(report_path)
        TypstUtils.typst_try_compile(report_dir, report_filename)

        println()
        println("✅ Representative year analysis report generated successfully!")
        
    catch e
        println()
        println("❌ Error during report generation:")
        println("   $(e)")
        
        if isa(e, SystemError)
            println()
            println("💡 Troubleshooting tips:")
            println("   • Check that all input files are accessible")
            println("   • Verify representative-year.toml configuration")
            println("   • Ensure meso data files are properly formatted")
        elseif isa(e, ArgumentError) || isa(e, BoundsError)
            println()
            println("💡 Troubleshooting tips:")
            println("   • Check sensor data formatting and completeness")
            println("   • Verify time range specifications in configuration")
            println("   • Review calibration results file structure")
        end
        
        rethrow(e)
    end
end

end # module