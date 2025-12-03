"""
    RecommendReportAllCommand.jl

Generates all necessary TOML configuration files for comprehensive mast reporting.
This command prepares all configurations needed for the 'report all' command.
"""
module RecommendReportAllCommand

using ...ReportClean.RecommendReportCleanCommand
using ...ReportRecovery.RecommendReportRecoveryCommand
using ...ReportReconstructCross.RecommendCrossMastReportCommand
using ...ReportReconstructSingle.RecommendReportReconstructSingleCommand
using ...ReportReconstructMeso.RecommendReportReconstructMesoCommand
using ...ReportTimeSeries.RecommendReportTimeSeriesMesoCommand
using ...ReportTimeSeries.RecommendReportTimeSeriesRepCommand

export execute

"""
    execute(project_dir::String)

Generate all report TOML configuration files for comprehensive mast analysis.

# Arguments
- `project_dir::String`: Project directory containing processing configurations

# Description
This command generates all necessary TOML configuration files for the main reports:

1. **report-clean.toml** - For clean report (raw vs clean data comparison)
2. **report-recovery.toml** - For data recovery status across reconstruction stages
3. **report-cross-mast.toml** - For cross-mast correlation analysis
4. **report-reconstruct-single.yaml** - For single-mast reconstruction effectiveness
5. **report-timeseries-meso.toml** - For time series analysis of meso-reconstructed data
6. **report-timeseries-rep.toml** - For time series analysis of representative year data
7. **report-reconstruct-meso.toml** - For meso-mast reconstruction quality analysis

Note: Representative year report uses representative-year.toml directly, so no additional config needed.

# Generated Files Under report-masts/
```
project-dir/
├── report-masts/
│   ├── report-recovery.toml
│   ├── report-cross-mast.toml
│   ├── report-reconstruct-single.yaml
│   ├── report-timeseries-meso.toml
│   └── report-timeseries-rep.toml
```

# Requirements
The project directory should contain:
- `reconstruct-meso.toml` - For recovery report config generation and timeseries-meso config
- `reconstruct-single.toml` - For cross-mast and reconstruct-single report configs
- `tower-shading.toml` - For reconstruct-single report config
- `representative-year.toml` - For timeseries-rep config generation

# Example Usage
```bash
# First, generate all report configurations
julia bin/CleanMast.jl recommend report-all my-project

# Then, generate all reports using those configurations
julia bin/CleanMast.jl report all my-project
```

# Error Handling
- Continues with remaining configurations if one fails
- Provides detailed messages about which configs were generated successfully
- Reports which source configurations are missing
"""
function execute(project_dir::String)
    println("🔍 Generating All Report Configurations")
    println("=" ^ 50)

    # Validate input
    if !isdir(project_dir)
        error("Project directory not found: $project_dir")
    end

    # Create report-masts directory if it doesn't exist
    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    # Track configuration generation results
    results = Dict{String, Bool}()
    errors = Dict{String, Exception}()

    println("📊 Generating report configuration files...")
    println("   Project: $(basename(project_dir))")
    println()

    # 1. Generate report-clean.toml
    println("📋 Config 1/7: Report Clean Configuration")
    try
        process_clean_config = joinpath(project_dir, "process-clean.toml")
        if isfile(process_clean_config)
            RecommendReportCleanCommand.execute(project_dir)
            results["clean"] = true
            println("   ✅ report-clean.toml generated successfully")
        else
            println("   ⚠️  Skipping: process-clean.toml not found")
            results["clean"] = false
        end
    catch e
        results["clean"] = false
        errors["clean"] = e
        println("   ❌ Clean config failed: $(e)")
    end
    println()

    # 2. Generate report-recovery.toml
    println("📋 Config 2/7: Report Recovery Configuration")
    try
        reconstruct_meso_config = joinpath(project_dir, "reconstruct-meso.toml")
        if isfile(reconstruct_meso_config)
            RecommendReportRecoveryCommand.execute(project_dir)
            results["recovery"] = true
            println("   ✅ report-recovery.toml generated successfully")
        else
            println("   ⚠️  Skipping: reconstruct-meso.toml not found")
            results["recovery"] = false
        end
    catch e
        results["recovery"] = false
        errors["recovery"] = e
        println("   ❌ Recovery config failed: $(e)")
    end
    println()

    # 3. Generate report-cross-mast.toml
    println("🔗 Config 3/7: Cross-Mast Report Configuration")
    try
        reconstruct_single_config = joinpath(project_dir, "reconstruct-single.toml")
        if isfile(reconstruct_single_config)
            RecommendCrossMastReportCommand.execute(project_dir)
            results["cross_mast"] = true
            println("   ✅ report-cross-mast.toml generated successfully")
        else
            println("   ⚠️  Skipping: reconstruct-single.toml not found")
            results["cross_mast"] = false
        end
    catch e
        results["cross_mast"] = false
        errors["cross_mast"] = e
        println("   ❌ Cross-mast config failed: $(e)")
    end
    println()

    # 4. Generate report-reconstruct-single.yaml
    println("📈 Config 4/7: Reconstruct Single Report Configuration")
    try
        tower_shading_config = joinpath(project_dir, "tower-shading.toml")
        if isfile(tower_shading_config)
            RecommendReportReconstructSingleCommand.execute(project_dir)
            results["reconstruct_single"] = true
            println("   ✅ report-reconstruct-single.yaml generated successfully")
        else
            println("   ⚠️  Skipping: tower-shading.toml not found")
            results["reconstruct_single"] = false
        end
    catch e
        results["reconstruct_single"] = false
        errors["reconstruct_single"] = e
        println("   ❌ Reconstruct single config failed: $(e)")
    end
    println()

    # 5. Generate report-timeseries-meso.toml
    println("📊 Config 5/7: Time Series Meso Report Configuration")
    try
        reconstruct_meso_config = joinpath(project_dir, "reconstruct-meso.toml")
        if isfile(reconstruct_meso_config)
            RecommendReportTimeSeriesMesoCommand.execute(project_dir)
            results["timeseries_meso"] = true
            println("   ✅ report-timeseries-meso.toml generated successfully")
        else
            println("   ⚠️  Skipping: reconstruct-meso.toml not found")
            results["timeseries_meso"] = false
        end
    catch e
        results["timeseries_meso"] = false
        errors["timeseries_meso"] = e
        println("   ❌ Timeseries meso config failed: $(e)")
    end
    println()

    # 6. Generate report-timeseries-rep.toml
    println("📊 Config 6/7: Time Series Representative Year Report Configuration")
    try
        representative_year_config = joinpath(project_dir, "representative-year.toml")
        if isfile(representative_year_config)
            RecommendReportTimeSeriesRepCommand.execute(project_dir)
            results["timeseries_rep"] = true
            println("   ✅ report-timeseries-rep.toml generated successfully")
        else
            println("   ⚠️  Skipping: representative-year.toml not found")
            results["timeseries_rep"] = false
        end
    catch e
        results["timeseries_rep"] = false
        errors["timeseries_rep"] = e
        println("   ❌ Timeseries rep config failed: $(e)")
    end
    println()

    # 7. Generate report-reconstruct-meso.toml
    println("🌍 Config 7/7: Reconstruct Meso Report Configuration")
    try
        reconstruct_meso_config = joinpath(project_dir, "reconstruct-meso.toml")
        if isfile(reconstruct_meso_config)
            RecommendReportReconstructMesoCommand.execute(project_dir)
            results["reconstruct_meso"] = true
            println("   ✅ report-reconstruct-meso.toml generated successfully")
        else
            println("   ⚠️  Skipping: reconstruct-meso.toml not found")
            results["reconstruct_meso"] = false
        end
    catch e
        results["reconstruct_meso"] = false
        errors["reconstruct_meso"] = e
        println("   ❌ Reconstruct meso config failed: $(e)")
    end
    println()

    # Summary
    successful_configs = count(values(results))
    total_attempted = length(results)

    println("📋 Configuration Generation Summary:")
    println("   • Configurations attempted: $total_attempted")
    println("   • Configurations successful: $successful_configs")
    println("   • Configurations skipped/failed: $(total_attempted - successful_configs)")
    println()

    # Detailed results
    println("📁 Configuration Status:")
    for (config_name, success) in results
        status_icon = success ? "✅" : "❌"
        config_display = Dict(
            "clean" => "Report Clean Configuration",
            "recovery" => "Report Recovery Configuration",
            "cross_mast" => "Cross-Mast Report Configuration",
            "reconstruct_single" => "Reconstruct Single Report Configuration",
            "timeseries_meso" => "Time Series Meso Report Configuration",
            "timeseries_rep" => "Time Series Representative Year Report Configuration",
            "reconstruct_meso" => "Reconstruct Meso Report Configuration"
        )[config_name]

        output_file = Dict(
            "clean" => "report-masts/report-clean.toml",
            "recovery" => "report-masts/report-recovery.toml",
            "cross_mast" => "report-masts/report-cross-mast.toml",
            "reconstruct_single" => "report-masts/report-reconstruct-single.yaml",
            "timeseries_meso" => "report-masts/report-timeseries-meso.toml",
            "timeseries_rep" => "report-masts/report-timeseries-rep.toml",
            "reconstruct_meso" => "report-masts/report-reconstruct-meso.toml"
        )[config_name]

        println("   $status_icon $config_display")
        if success
            println("      Generated: $output_file")
        elseif haskey(errors, config_name)
            println("      Error: $(errors[config_name])")
        end
    end
    println()

    # Additional notes about configs that are used directly
    println("📝 Direct Configuration Usage:")
    rep_year_exists = isfile(joinpath(project_dir, "representative-year.toml"))
    rep_year_icon = rep_year_exists ? "✅" : "❌"

    println("   $rep_year_icon Representative Year Report uses representative-year.toml directly")
    println()

    if successful_configs > 0 || rep_year_exists
        println("✅ Report configuration generation completed!")
        println("   All configurations are organized under: report-masts/")
        println()
        println("💡 Next steps:")
        println("   1. Review generated configurations in report-masts/")
        println("   2. Run: julia bin/CleanMast.jl report all $project_dir")

        if successful_configs < total_attempted
            println()
            println("⚠️  Some configurations were skipped due to missing source files.")
            println("   Complete the processing pipeline before generating all reports.")
        end
    else
        println("❌ No report configurations were successfully generated.")
        println("   Please ensure processing configurations exist (reconstruct-meso.toml, etc.)")

        if !isempty(errors)
            println()
            println("🔍 Troubleshooting:")
            for (config_name, error) in errors
                println("   • $config_name: $(error)")
            end
        end
    end
end

end # module