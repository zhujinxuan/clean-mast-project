"""
    CommandReportReconstructCross.jl

Main command implementation for report cross-mast.
Orchestrates complete workflow: data loading → analysis → visualization → Chinese report generation.
"""
module CommandReportReconstructCross

using DataFrames
using Dates
using Statistics

# Import configuration types
using ...Types.ReportReconstructCrossConfig: ReportReconstructCrossConfiguration, from_dict
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ...TypstUtils
using ...PandocUtils

# Import analysis modules
using ..AnalysisCore: load_all_mast_data, analyze_mast_pair, filter_valid_results
using ..DataVisualization: create_mast_pair_plots
using ..ReportGeneration: generate_typst_report, export_csv_data

export execute

"""
    execute(config_path::String)

Execute the report cross-mast command.

# Arguments
- `config_path::String`: Path to report-cross-mast.toml configuration file

# Workflow
1. Load and validate configuration
2. Create output directory structure
3. Load all mast time series data
4. Analyze all mast pairs (N² combinations)
5. Generate individual plots for each pair
6. Export CSV data for each pair
7. Generate comprehensive Chinese Typst report

# Example
```bash
julia bin/CleanMast.jl report cross-mast report-cross-mast.toml
```

This generates:
- Chinese Typst report with embedded plots and tables
- Individual PNG plots for each mast pair
- Individual CSV data exports for each pair
- Comprehensive analysis summary
"""
function execute(config_path::String)
    println("🚀 Starting cross-mast analysis...")
    
    # 1. Load and validate configuration
    config_dict = load_dict(config_path)
    config = from_dict(ReportReconstructCrossConfiguration, config_dict)

    # Use config directory as base for all path resolution
    config_dir = dirname(config_path)

    println("📋 Configuration loaded:")
    println("  - Masts: $(length(config.masts))")
    println("  - Output: $(config.analyze.output_dir)")
    println("  - Language: $(config.analyze.language)")
    println("  - Include plots: $(config.analyze.include_plots)")

    # 2. Create output directory structure (paths relative to config file location)
    output_dir = joinpath(config_dir, config.analyze.output_dir)
    create_output_directories(output_dir, config.analyze.include_plots)

    # 3. Load all mast time series data (including optional before data)
    println("\n📊 Loading mast time series data...")
    mast_data_with_before = load_all_mast_data_with_before(config, config_dir)
    mast_data = Dict(name => entry.data for (name, entry) in mast_data_with_before)
    println("✅ Loaded data for $(length(mast_data)) masts")
    
    # 4. Analyze all mast pairs (N² combinations)
    println("\n🔍 Analyzing mast pair relationships...")
    analysis_results = analyze_all_mast_pairs(config.masts, mast_data)
    
    valid_results = filter_valid_results(analysis_results)
    println("✅ Completed analysis for $(length(valid_results)) valid mast pairs")
    
    if isempty(valid_results)
        @warn "No valid analysis results found. Check data quality and overlap periods."
        return
    end
    
    # 5. Generate visualizations
    if config.analyze.include_plots
        println("\n🎨 Generating visualizations...")
        create_mast_pair_plots(valid_results, output_dir, mast_data)
    end
    
    # 6. Export CSV data
    println("\n💾 Exporting data...")
    export_csv_data(valid_results, output_dir)
    
    # 7. Generate comprehensive report
    println("\n📄 Generating report...")
    generate_typst_report(valid_results, config, output_dir, mast_data_with_before)

    # Compile Typst report to PDF if Typst is available
    TypstUtils.typst_try_compile(output_dir, "report.typ")
    PandocUtils.pandoc_try_convert(output_dir, "report.typ")

    # 8. Print completion summary
    print_completion_summary(valid_results, output_dir, config)
    
    println("\n✅ Cross-mast analysis completed successfully!")
end

"""
    create_output_directories(output_dir, include_plots)

Create the complete output directory structure.

# Arguments
- `output_dir::String`: Base output directory
- `include_plots::Bool`: Whether to create plots directory
"""
function create_output_directories(output_dir::String, include_plots::Bool)
    println("📁 Creating output directory structure...")
    
    mkpath(output_dir)
    mkpath(joinpath(output_dir, "tables"))
    mkpath(joinpath(output_dir, "data"))
    
    if include_plots
        mkpath(joinpath(output_dir, "plots"))
    end
    
    println("  ✓ Output structure: $(output_dir)")
end

"""
    analyze_all_mast_pairs(masts, mast_data)

Analyze all possible mast pairs (N² combinations excluding self-pairs).

# Arguments
- `masts::Vector`: Array of mast configurations
- `mast_data::Dict`: Dictionary mapping mast names to TimeSeriesData

# Returns
- `Vector`: Array of analysis results (including Nothing for failed analyses)
"""
function analyze_all_mast_pairs(masts, mast_data::Dict)
    analysis_results = []
    total_pairs = length(masts) * (length(masts) - 1)
    current_pair = 0
    
    for target_mast in masts
        for source_mast in masts
            if target_mast.name == source_mast.name
                continue  # Skip self-pairs
            end
            
            current_pair += 1
            println("  🔍 Analyzing pair $(current_pair)/$(total_pairs): $(target_mast.name) ← $(source_mast.name)")
            
            target_ts = mast_data[target_mast.name]
            source_ts = mast_data[source_mast.name]
            
            result = analyze_mast_pair(
                target_ts,
                source_ts,
                target_mast.name,
                source_mast.name
            )
            
            push!(analysis_results, result)
        end
    end
    
    return analysis_results
end

"""
    load_all_mast_data_with_before(config, config_dir)

Load all mast time series data, including before-reconstruction data.
Returns Dict{String, NamedTuple{(:data, :before_data), Tuple{TimeSeriesData, TimeSeriesData}}}
"""
function load_all_mast_data_with_before(config, config_dir)::Dict{String, @NamedTuple{data::TimeSeriesData, before_data::TimeSeriesData}}
    mast_data_dict = Dict{String, @NamedTuple{data::TimeSeriesData, before_data::TimeSeriesData}}()

    for mast_config in config.masts
        # Load before and after reconstruction data
        before_data = load_timeseries(mast_config.before_reconstruction, config_dir)
        data = load_timeseries(mast_config.after_reconstruction, config_dir)

        mast_data_dict[mast_config.name] = (
            data = data,
            before_data = before_data
        )
    end

    return mast_data_dict
end

"""
    print_completion_summary(results, output_dir, config)

Print detailed completion summary with file listings and statistics.

# Arguments
- `results::Vector`: Valid analysis results
- `output_dir::String`: Output directory path
- `config`: Configuration object
"""
function print_completion_summary(results::Vector, output_dir::String, config)
    println("\n📋 Analysis Summary:")
    println("  📊 Mast pairs analyzed: $(length(results))")
    
    # Speed correlation statistics
    total_speed_pairs = sum(length(r.speed_correlations) for r in results)
    if total_speed_pairs > 0
        all_speed_corrs = vcat([r.speed_correlations for r in results]...)
        best_corr = maximum(c.correlation for c in all_speed_corrs)
        avg_corr = mean(c.correlation for c in all_speed_corrs)
        println("  🌪️  Speed sensor pairs: $(total_speed_pairs) (best r=$(round(best_corr, digits=3)), avg r=$(round(avg_corr, digits=3)))")
    end
    
    # Direction analysis statistics
    total_direction_pairs = sum(length(r.direction_analysis) for r in results)
    if total_direction_pairs > 0
        all_direction_pairs = vcat([r.direction_analysis for r in results]...)
        best_std = minimum(d.std_deviation for d in all_direction_pairs)
        avg_std = mean(d.std_deviation for d in all_direction_pairs)
        println("  🧭 Direction sensor pairs: $(total_direction_pairs) (best std=$(round(best_std, digits=1))°, avg std=$(round(avg_std, digits=1))°)")
    end
    
    # Coverage statistics
    avg_overlap = mean(r.coverage.overlap_days for r in results)
    println("  📅 Average overlap: $(round(avg_overlap, digits=1)) days")
    
    println("\n📁 Generated files:")
    println("  📄 Main report: $(joinpath(output_dir, "report.typ"))")
    println("  📊 Table files: $(length(results)) individual summaries")
    println("  💾 CSV files: $(length(results) * 2) data exports")
    
    if config.analyze.include_plots
        println("  🎨 Plot files: $(length(results) * 2) visualizations")
    end
    
    println("\n🎯 Next steps:")
    println("  1. Review report.typ with Typst compiler")
    println("  2. Examine individual plots in plots/ directory")
    println("  3. Use CSV data for further analysis or model training")
    
    if config.analyze.language == "zh"
        println("  📝 Report generated in Chinese (中文)")
    end
end

end # module 