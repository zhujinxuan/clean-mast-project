"""
    CommandReportReconstructMeso.jl

Main command implementation for report-reconstruct-meso.
Orchestrates complete workflow: config loading → data loading → analysis → visualization → report generation.
"""
module CommandReportReconstructMeso

using DataFrames
using Dates
using Statistics

using ...Types.ReportReconstructMesoConfig: ReportReconstructMesoConfiguration, from_dict
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ...TypstUtils

using ..AnalysisCore: load_all_data, analyze_meso_mast_pair
using ..DataVisualization: create_meso_mast_plots
using ..ReportGeneration: generate_typst_report, export_csv_data

export execute

"""
    execute(config_path::String)

Execute the report-reconstruct-meso command.

# Arguments
- `config_path::String`: Path to report-reconstruct-meso.toml configuration file

# Workflow
1. Load and validate configuration
2. Create output directory structure
3. Load all mast and meso time series data
4. Analyze all meso-mast pairs
5. Generate individual plots for each pair
6. Export CSV data for each pair
7. Generate comprehensive Chinese Typst report

# Example
```bash
julia bin/CleanMast.jl report reconstruct-meso report-masts/report-reconstruct-meso.toml
```

This generates:
- Chinese Typst report with embedded plots and tables
- Individual PNG plots for each meso-mast pair
- Individual CSV data exports for each pair
- Comprehensive analysis summary
"""
function execute(config_path::String)
    println("🚀 Starting meso-mast reconstruction quality analysis...")

    config_dict = load_dict(config_path)
    config = from_dict(ReportReconstructMesoConfiguration, config_dict)

    # Use config directory as base for all path resolution
    config_dir = dirname(config_path)

    println("📋 Configuration loaded:")
    println("  - Masts: $(length(config.masts))")
    println("  - Mesos: $(length(config.mesos))")
    println("  - Output: $(config.analyze.output_dir)")

    # Resolve output directory relative to config file location
    output_dir = joinpath(config_dir, config.analyze.output_dir)
    create_output_directories(output_dir)

    println("\n📊 Loading time series data...")
    mast_data, meso_data = load_all_data(config, config_dir)
    println("✅ Loaded data for $(length(mast_data)) masts and $(length(meso_data)) mesos")

    println("\n🔍 Analyzing meso-mast relationships...")
    results = analyze_all_pairs(config, mast_data, meso_data)
    println("✅ Completed analysis for $(length(results)) meso-mast pairs")

    println("\n🎨 Generating visualizations...")
    create_meso_mast_plots(results, output_dir, mast_data, meso_data)

    println("\n💾 Exporting data...")
    export_csv_data(results, output_dir)

    println("\n📄 Generating report...")
    generate_typst_report(results, output_dir)

    print_completion_summary(results, output_dir)

    println()
    TypstUtils.typst_try_compile(output_dir, "report.typ")

    println("\n✅ Meso-mast reconstruction quality analysis completed successfully!")
end

"""
    create_output_directories(output_dir)

Create the complete output directory structure.

# Arguments
- `output_dir::String`: Base output directory
"""
function create_output_directories(output_dir::String)
    println("📁 Creating output directory structure...")

    mkpath(output_dir)
    mkpath(joinpath(output_dir, "data"))
    mkpath(joinpath(output_dir, "plots"))

    println("  ✓ Output structure: $(output_dir)")
end

"""
    analyze_all_pairs(config, mast_data, meso_data)

Analyze all possible meso-mast combinations.

# Arguments
- `config`: ReportReconstructMesoConfiguration
- `mast_data::Dict`: Dictionary mapping mast names to TimeSeriesData
- `meso_data::Dict`: Dictionary mapping meso names to TimeSeriesData

# Returns
- `Vector{AnalyzeMesoMastResult}`: Array of analysis results (errors if any pair fails)
"""
function analyze_all_pairs(config, mast_data::Dict, meso_data::Dict)
    results = []
    total_pairs = length(config.masts) * length(config.mesos)
    pair_idx = 0

    for mast_config in config.masts
        mast_name = mast_config.name

        if !haskey(mast_data, mast_name)
            error("Mast data not found: $(mast_name)")
        end

        mast_ts = mast_data[mast_name]

        for meso_config in config.mesos
            meso_name = meso_config.name
            pair_idx += 1

            println("  🔍 Analyzing pair $(pair_idx)/$(total_pairs): $(mast_name) ← $(meso_name)")

            if !haskey(meso_data, meso_name)
                error("Meso data not found: $(meso_name)")
            end

            meso_ts = meso_data[meso_name]

            result = analyze_meso_mast_pair(
                mast_ts,
                meso_ts,
                mast_name,
                meso_name,
                mast_config.wind_speed_report_heights,
                meso_config.wind_speed_report_heights
            )

            push!(results, result)
        end
    end

    return results
end

"""
    print_completion_summary(results, output_dir, config)

Print detailed completion summary with file listings and statistics.

# Arguments
- `results::Vector`: Valid analysis results
- `output_dir::String`: Output directory path
- `config`: Configuration object
"""
function print_completion_summary(results::Vector, output_dir::String)
    println("\n📋 Analysis Summary:")
    println("  📊 Meso-mast pairs analyzed: $(length(results))")

    total_sensor_pairs = sum(length(r.sensor_metrics) for r in results)
    if total_sensor_pairs > 0
        all_metrics = vcat([r.sensor_metrics for r in results]...)
        best_corr = maximum(m.correlation for m in all_metrics)
        avg_corr = mean(m.correlation for m in all_metrics)
        best_rmse = minimum(m.rmse for m in all_metrics)
        avg_rmse = mean(m.rmse for m in all_metrics)

        println("  🌪️  Sensor pairs: $(total_sensor_pairs)")
        println("      Best correlation: $(round(best_corr, digits=3))")
        println("      Avg correlation: $(round(avg_corr, digits=3))")
        println("      Best RMSE: $(round(best_rmse, digits=2)) m/s")
        println("      Avg RMSE: $(round(avg_rmse, digits=2)) m/s")
    end

    avg_overlap = mean(r.overlap_days for r in results)
    println("  📅 Average overlap: $(round(avg_overlap, digits=1)) days")

    println("\n📁 Generated files:")
    println("  📄 Main report: $(joinpath(output_dir, "report.typ"))")
    println("  💾 CSV files: $(length(results)) data exports")
    println("  🎨 Plot files: $(length(results)) visualizations")

    println("\n🎯 Next steps:")
    println("  1. Review report.typ with Typst compiler")
    println("  2. Examine individual plots in plots/ directory")
    println("  3. Use CSV data for further analysis")
    println("  📝 Report generated in Chinese (中文)")

end

end # module
