"""
    ReportAllMastsCommand.jl

Comprehensive report generation command that creates all mast-related reports:
1. Clean report (raw vs clean data comparison)
2. Recovery report (data coverage across reconstruction stages)
3. Reconstruct single report (single-mast reconstruction analysis)
4. Cross-mast report (correlation analysis between mast pairs)
5. Representative year report (calibration analysis)
6. Time series reports (meso and representative year wind analysis)
7. Reconstruct meso report (meso-mast reconstruction quality)

Provides a single command to generate complete mast analysis documentation.
"""
module ReportAllMastsCommand

using ...ReportClean.ReportCleanCommand
using ...ReportRecovery.ReportRecoveryCommand
using ...RepresentativeYear.ReportRepresentativeYearCommand
using ...ReportReconstructCross.CommandReportReconstructCross
using ...ReportTimeSeries.ReportTimeSeriesCommand
using ...ReportReconstructMeso
using ...ReportReconstructSingle.ReportReconstructSingleCommand

export execute

"""
    execute(project_dir::String)

Generate all comprehensive mast reports for a project.

# Arguments
- `project_dir::String`: Project directory containing all necessary configurations

# Description
This command generates eight comprehensive reports:

1. **Clean Report** (`report-masts/clean/`)
   - Raw vs clean data comparison
   - Data coverage analysis
   - Violation analysis and sensor inventory

2. **Recovery Report** (`report-masts/recovery/`)
   - Data coverage tracking across all reconstruction stages
   - Shows data filled by: tower shading → single-mast → cross-mast → mesoscale
   - Recovery effectiveness analysis with bar charts

3. **Reconstruct Single Report** (`report-masts/reconstruct-single/`)
   - Single-mast reconstruction analysis before/after comparison
   - Wind speed correlation (R²) matrices between heights
   - Wind direction difference analysis
   - Data coverage and reconstruction rate statistics

4. **Cross-Mast Report** (`report-masts/cross-mast/`)
   - Cross-mast correlation analysis and relationships
   - Wind speed and direction correlation matrices
   - Reconstruction effectiveness between mast pairs

5. **Representative Year Report** (`report-masts/representative-year/`)
   - Climatology vs training vs representative year analysis
   - 16-sector calibration analysis with slopes and intercepts
   - Sensor-level calibration status

6. **Time Series Meso Report** (`report-masts/timeseries-meso/`)
   - Wind temporal analysis of meso-reconstructed data
   - Vertical profile analysis and wind rose plots
   - Turbulence intensity and Weibull distribution analysis

7. **Time Series Representative Year Report** (`report-masts/timeseries-rep/`)
   - Wind temporal analysis of representative year data
   - Vertical profile analysis and wind rose plots
   - Turbulence intensity and Weibull distribution analysis

8. **Reconstruct Meso Report** (`report-masts/reconstruct-meso/`)
   - Meso-mast reconstruction quality analysis
   - Comparison of mesoscale vs reconstructed mast data

# Requirements
The project directory must contain the following configurations:
- `process-clean.toml` - For clean report generation
- `report-masts/report-recovery.toml` - For recovery report generation
- `report-masts/report-reconstruct-single.yaml` - For reconstruct single report generation
- `report-masts/report-cross-mast.toml` - For cross-mast analysis report generation
- `representative-year.toml` - For representative year report generation
- `report-masts/report-timeseries-meso.toml` - For time series meso report generation
- `report-masts/report-timeseries-rep.toml` - For time series representative year report generation
- `report-masts/report-reconstruct-meso.toml` - For reconstruct meso report generation

Generate these configurations first using:
```bash
julia bin/CleanMast.jl recommend report-all project-dir
```

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
│   ├── reconstruct-single/
│   │   ├── reconstruction_analysis_report.typ
│   │   ├── plots/
│   │   └── ...
│   ├── cross-mast/
│   │   ├── report.typ
│   │   ├── tables/
│   │   ├── plots/
│   │   └── ...
│   ├── representative-year/
│   │   ├── report.typ
│   │   ├── tables/
│   │   ├── data/
│   │   └── ...
│   ├── timeseries-meso/
│   │   ├── pn-002824/
│   │   ├── pn-013945/
│   │   ├── pn-014576/
│   │   └── ...
│   ├── timeseries-rep/
│   │   ├── pn-002824/
│   │   ├── pn-013945/
│   │   ├── pn-014576/
│   │   └── ...
│   └── reconstruct-meso/
│       ├── report.typ
│       └── ...
```

# Example Usage
```bash
# First, generate all report configurations
julia bin/CleanMast.jl recommend report-all my-project

# Then, generate all reports using those configurations
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
    println("📋 Report 1/8: Clean Report (Raw vs Clean Data)")
    try
        report_clean_config = joinpath(project_dir, "report-masts", "report-clean.toml")
        if isfile(report_clean_config)
            ReportCleanCommand.execute(report_clean_config)
            results["clean"] = true
            println("   ✅ Clean report generated successfully")
        else
            println("   ⚠️  Skipping: report-clean.toml not found in report-masts/")
            println("      Run 'recommend report-clean' first to generate configuration")
            results["clean"] = false
        end
    catch e
        results["clean"] = false
        errors["clean"] = e
        println("   ❌ Clean report failed: $(e)")
    end
    println()

    # 2. Generate Recovery Report
    println("📈 Report 2/8: Recovery Report (Data Coverage Across Stages)")
    try
        recovery_config_path = joinpath(project_dir, "report-masts", "report-recovery.toml")
        if isfile(recovery_config_path)
            ReportRecoveryCommand.execute(recovery_config_path)
            results["recovery"] = true
            println("   ✅ Recovery report generated successfully")
        else
            println("   ⚠️  Skipping: report-recovery.toml not found in report-masts/")
            println("      Run 'recommend report-all' first to generate configurations")
            results["recovery"] = false
        end
    catch e
        results["recovery"] = false
        errors["recovery"] = e
        println("   ❌ Recovery report failed: $(e)")
    end
    println()

    # 3. Generate Reconstruct Single Report
    println("🔄 Report 3/8: Reconstruct Single Report (Single-Mast Reconstruction)")
    try
        reconstruct_single_config = joinpath(project_dir, "report-masts", "report-reconstruct-single.yaml")
        if isfile(reconstruct_single_config)
            ReportReconstructSingleCommand.execute(reconstruct_single_config)
            results["reconstruct_single"] = true
            println("   ✅ Reconstruct single report generated successfully")
        else
            println("   ⚠️  Skipping: report-reconstruct-single.yaml not found in report-masts/")
            println("      Run 'recommend report-all' first to generate configurations")
            results["reconstruct_single"] = false
        end
    catch e
        results["reconstruct_single"] = false
        errors["reconstruct_single"] = e
        println("   ❌ Reconstruct single report failed: $(e)")
    end
    println()

    # 4. Generate Cross-Mast Report
    println("🔗 Report 4/8: Cross-Mast Report (Correlation Analysis)")
    try
        cross_mast_config = joinpath(project_dir, "report-masts", "report-cross-mast.toml")
        if isfile(cross_mast_config)
            CommandReportReconstructCross.execute(cross_mast_config)
            results["cross_mast"] = true
            println("   ✅ Cross-mast report generated successfully")
        else
            println("   ⚠️  Skipping: report-cross-mast.toml not found in report-masts/")
            println("      Run 'recommend report-all' first to generate configurations")
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

    # 5. Generate Representative Year Report
    println("📅 Report 5/8: Representative Year Report (Calibration Analysis)")
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

    # 6. Generate Time Series Meso Report
    println("📊 Report 6/8: Time Series Meso Report (Meso-Reconstructed Data Analysis)")
    try
        timeseries_meso_config = joinpath(project_dir, "report-masts", "report-timeseries-meso.toml")
        if isfile(timeseries_meso_config)
            ReportTimeSeriesCommand.execute(timeseries_meso_config)
            results["timeseries_meso"] = true
            println("   ✅ Time series meso report generated successfully")
        else
            println("   ⚠️  Skipping: report-timeseries-meso.toml not found in report-masts/")
            println("      Run 'recommend report-all' first to generate configurations")
            results["timeseries_meso"] = false
        end
    catch e
        results["timeseries_meso"] = false
        errors["timeseries_meso"] = e
        println("   ❌ Time series meso report failed: $(e)")
    end
    println()

    # 7. Generate Time Series Representative Year Report
    println("📊 Report 7/8: Time Series Representative Year Report (Rep Year Data Analysis)")
    try
        timeseries_rep_config = joinpath(project_dir, "report-masts", "report-timeseries-rep.toml")
        if isfile(timeseries_rep_config)
            ReportTimeSeriesCommand.execute(timeseries_rep_config)
            results["timeseries_rep"] = true
            println("   ✅ Time series representative year report generated successfully")
        else
            println("   ⚠️  Skipping: report-timeseries-rep.toml not found in report-masts/")
            println("      Run 'recommend report-all' first to generate configurations")
            results["timeseries_rep"] = false
        end
    catch e
        results["timeseries_rep"] = false
        errors["timeseries_rep"] = e
        println("   ❌ Time series representative year report failed: $(e)")
    end
    println()

    # 8. Generate Reconstruct Meso Report
    println("🌍 Report 8/8: Reconstruct Meso Report (Meso-Mast Reconstruction Quality)")
    try
        reconstruct_meso_config = joinpath(project_dir, "report-masts", "report-reconstruct-meso.toml")
        if isfile(reconstruct_meso_config)
            ReportReconstructMeso.CommandReportReconstructMeso.execute(reconstruct_meso_config)
            results["reconstruct_meso"] = true
            println("   ✅ Reconstruct meso report generated successfully")
        else
            println("   ⚠️  Skipping: report-reconstruct-meso.toml not found in report-masts/")
            println("      Run 'recommend report-all' first to generate configurations")
            results["reconstruct_meso"] = false
        end
    catch e
        results["reconstruct_meso"] = false
        errors["reconstruct_meso"] = e
        println("   ❌ Reconstruct meso report failed: $(e)")
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
            "reconstruct_single" => "Reconstruct Single Report",
            "cross_mast" => "Cross-Mast Report",
            "representative_year" => "Representative Year Report",
            "timeseries_meso" => "Time Series Meso Report",
            "timeseries_rep" => "Time Series Representative Year Report",
            "reconstruct_meso" => "Reconstruct Meso Report"
        )[report_name]

        output_path = Dict(
            "clean" => "report-masts/clean/report.typ",
            "recovery" => "report-masts/recovery/recovery-report.typ",
            "reconstruct_single" => "report-masts/reconstruct-single/reconstruction_analysis_report.typ",
            "cross_mast" => "report-masts/cross-mast/report.typ",
            "representative_year" => "report-masts/representative-year/report.typ",
            "timeseries_meso" => "report-masts/timeseries-meso/",
            "timeseries_rep" => "report-masts/timeseries-rep/",
            "reconstruct_meso" => "report-masts/reconstruct-meso/report.typ"
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
            println("   Run 'julia bin/CleanMast.jl recommend report-all $project_dir' to generate missing configs.")
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