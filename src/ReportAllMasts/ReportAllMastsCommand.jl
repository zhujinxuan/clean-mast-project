"""
    ReportAllMastsCommand.jl

Comprehensive report generation command that creates all mast-related reports:
1. Clean report (raw vs clean data comparison)
2. Recovery report (data coverage across reconstruction stages)
3. Cross-mast report (correlation analysis between mast pairs)
4. Representative year report (calibration analysis)

Provides a single command to generate complete mast analysis documentation.
"""
module ReportAllMastsCommand

using ...ReportClean.ReportAllCommand
using ...ReportRecovery.RecommendReportRecoveryCommand
using ...ReportRecovery.ReportRecoveryCommand
using ...RepresentativeYear.ReportRepresentativeYearCommand
using ...AnalyzeReconstructCross.RecommendAnalyzeReconstructCrossCommand
using ...AnalyzeReconstructCross.RecommendCrossMastReportCommand
using ...AnalyzeReconstructCross.CommandAnalyzeReconstructCross

export execute

"""
    execute(project_dir::String)

Generate all comprehensive mast reports for a project.

# Arguments
- `project_dir::String`: Project directory containing all necessary configurations

# Description
This command generates four comprehensive reports:

1. **Clean Report** (`report-masts/clean/`)
   - Raw vs clean data comparison
   - Data coverage analysis
   - Violation analysis and sensor inventory

2. **Recovery Report** (`report-masts/recovery/`)
   - Data coverage tracking across all reconstruction stages
   - Shows data filled by: tower shading → single-mast → cross-mast → mesoscale
   - Recovery effectiveness analysis with bar charts

3. **Cross-Mast Report** (`report-masts/cross-mast/`)
   - Cross-mast correlation analysis and relationships
   - Wind speed and direction correlation matrices
   - Reconstruction effectiveness between mast pairs

4. **Representative Year Report** (`report-masts/representative-year/`)
   - Climatology vs training vs representative year analysis
   - 16-sector calibration analysis with slopes and intercepts
   - Sensor-level calibration status

# Requirements
The project directory must contain:
- `process-clean.toml` - For clean report generation
- `reconstruct-meso.toml` - For recovery report generation
- `analyze-reconstruct-cross.toml` - For cross-mast analysis report generation
- `representative-year.toml` - For representative year report generation
- All associated data files as specified in configurations

# Output Structure
```
project-dir/
├── report-masts/
│   ├── clean/
│   │   ├── report.typ
│   │   ├── plots/
│   │   └── ...
│   ├── recovery/
│   │   ├── recovery-report.typ
│   │   ├── plots/
│   │   └── ...
│   ├── cross-mast/
│   │   ├── report.typ
│   │   ├── tables/
│   │   ├── plots/
│   │   └── ...
│   └── representative-year/
│       ├── report.typ
│       ├── tables/
│       ├── data/
│       └── ...
```

# Example Usage
```bash
julia bin/CleanMast.jl report all my-project
```

# Error Handling
- Continues with remaining reports if one fails
- Provides detailed error messages for troubleshooting
- Reports which configurations are missing vs which reports succeeded
"""
function execute(project_dir::String)
    println("🔍 Comprehensive Mast Reports Generation")
    println("=" ^ 50)

    # Validate input
    if !isdir(project_dir)
        error("Project directory not found: $project_dir")
    end

    # Track report generation results
    results = Dict{String, Bool}()
    errors = Dict{String, Exception}()

    println("📊 Generating comprehensive mast analysis reports...")
    println("   Project: $(basename(project_dir))")
    println()

    # 1. Generate Clean Report
    println("📋 Report 1/4: Clean Report (Raw vs Clean Data)")
    try
        process_clean_config = joinpath(project_dir, "process-clean.toml")
        if isfile(process_clean_config)
            ReportAllCommand.execute(project_dir)
            results["clean"] = true
            println("   ✅ Clean report generated successfully")
        else
            println("   ⚠️  Skipping: process-clean.toml not found")
            results["clean"] = false
        end
    catch e
        results["clean"] = false
        errors["clean"] = e
        println("   ❌ Clean report failed: $(e)")
    end
    println()

    # 2. Generate Recovery Report
    println("📈 Report 2/4: Recovery Report (Data Coverage Across Stages)")
    try
        reconstruct_meso_config = joinpath(project_dir, "reconstruct-meso.toml")
        if isfile(reconstruct_meso_config)
            # Generate recovery report configuration
            RecommendReportRecoveryCommand.execute(project_dir)

            # Generate actual recovery report
            recovery_config_path = joinpath(project_dir, "report-masts", "report-recovery.toml")
            ReportRecoveryCommand.execute(recovery_config_path)
            results["recovery"] = true
            println("   ✅ Recovery report generated successfully")
        else
            println("   ⚠️  Skipping: reconstruct-meso.toml not found")
            results["recovery"] = false
        end
    catch e
        results["recovery"] = false
        errors["recovery"] = e
        println("   ❌ Recovery report failed: $(e)")
    end
    println()

    # 3. Generate Cross-Mast Report
    println("🔗 Report 3/4: Cross-Mast Report (Correlation Analysis)")
    try
        cross_mast_config = joinpath(project_dir, "report-masts", "report-cross-mast.toml")
        reconstruct_single_config = joinpath(project_dir, "reconstruct-single.toml")

        if isfile(reconstruct_single_config)
            # Generate cross-mast configuration if it doesn't exist
            if !isfile(cross_mast_config)
                println("   📝 Generating report-cross-mast.toml configuration...")
                RecommendCrossMastReportCommand.execute(project_dir)
            end

            # Generate cross-mast report
            CommandAnalyzeReconstructCross.execute(cross_mast_config)
            results["cross_mast"] = true
            println("   ✅ Cross-mast report generated successfully")
        else
            println("   ⚠️  Skipping: reconstruct-single.toml not found")
            results["cross_mast"] = false
        end
    catch e
        results["cross_mast"] = false
        errors["cross_mast"] = e
        println("   ❌ Cross-mast report failed: $(e)")
        println("   🔍 Stacktrace:")
        for (i, frame) in enumerate(stacktrace(catch_backtrace()))
            println("     $i. $frame")
            if i > 10  # Limit to first 10 frames
                break
            end
        end
    end
    println()

    # 4. Generate Representative Year Report
    println("📅 Report 4/4: Representative Year Report (Calibration Analysis)")
    try
        rep_year_config = joinpath(project_dir, "representative-year.toml")
        if isfile(rep_year_config)
            ReportRepresentativeYearCommand.execute(project_dir)
            results["representative_year"] = true
            println("   ✅ Representative year report generated successfully")
        else
            println("   ⚠️  Skipping: representative-year.toml not found")
            results["representative_year"] = false
        end
    catch e
        results["representative_year"] = false
        errors["representative_year"] = e
        println("   ❌ Representative year report failed: $(e)")
    end
    println()

    # Summary
    successful_reports = count(values(results))
    total_attempted = length(results)

    println("📋 Generation Summary:")
    println("   • Reports attempted: $total_attempted")
    println("   • Reports successful: $successful_reports")
    println("   • Reports skipped/failed: $(total_attempted - successful_reports)")
    println()

    # Detailed results
    println("📁 Report Status:")
    for (report_name, success) in results
        status_icon = success ? "✅" : "❌"
        report_display = Dict(
            "clean" => "Clean Report",
            "recovery" => "Recovery Report",
            "cross_mast" => "Cross-Mast Report",
            "representative_year" => "Representative Year Report"
        )[report_name]

        output_path = Dict(
            "clean" => "report-masts/clean/report.typ",
            "recovery" => "report-masts/recovery/recovery-report.typ",
            "cross_mast" => "report-masts/cross-mast/report.typ",
            "representative_year" => "report-masts/representative-year/report.typ"
        )[report_name]

        println("   $status_icon $report_display")
        if success
            println("      Location: $output_path")
        elseif haskey(errors, report_name)
            println("      Error: $(errors[report_name])")
        end
    end
    println()

    if successful_reports > 0
        println("✅ Comprehensive mast reports generation completed!")
        println("   All reports are organized under: report-masts/")
        println("   Use Typst to compile individual reports to PDF")

        if successful_reports < total_attempted
            println()
            println("💡 Some reports were skipped due to missing configuration files.")
            println("   Ensure all processing stages are complete before generating reports.")
        end
    else
        println("❌ No reports were successfully generated.")
        println("   Please check configuration files and data availability.")

        if !isempty(errors)
            println()
            println("🔍 Troubleshooting:")
            for (report_name, error) in errors
                println("   • $report_name: $(error)")
            end
        end
    end
end

end # module