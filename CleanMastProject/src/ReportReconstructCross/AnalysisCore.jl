"""
    AnalysisCore.jl

Core analysis functions for cross-mast relationship analysis.
Reuses existing cross-mast analysis infrastructure with proper missing value handling.
"""
module AnalysisCore

using DataFrames
using Statistics
using Dates

# Import existing analysis functions
using ...TrainReconstructCross.DataCoverage: analyze_mast_pair_coverage
using ...TrainReconstructCross.CrossMastSpeedCorrelation: analyze_windspeed_correlations
using ...TrainReconstructCross.CrossMastDirectionAnalysis: analyze_winddirection_differences
using ...TrainReconstructCross.CrossMastSummary: summarize_correlations, summarize_direction_analysis

# Import types
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries
using ...Types.CrossMastAnalysisResults: MastPairCoverage, CorrelationSummary, DirectionSummary

export AnalyzePairResult, analyze_mast_pair, load_all_mast_data

"""
    AnalyzePairResult

Result struct for a single mast pair analysis (analyze command specific).

# Fields
- `target_mast::String`: Name of target mast
- `source_mast::String`: Name of source mast
- `coverage::MastPairCoverage`: Data coverage analysis
- `speed_correlations::Vector`: Wind speed correlation results
- `direction_analysis::Vector`: Wind direction analysis results
- `speed_summary::CorrelationSummary`: Summary of speed correlations
- `direction_summary::DirectionSummary`: Summary of direction analysis
"""
struct AnalyzePairResult
    target_mast::String
    source_mast::String
    coverage::MastPairCoverage
    speed_correlations::Vector
    direction_analysis::Vector
    speed_summary::CorrelationSummary
    direction_summary::DirectionSummary
end

"""
    load_all_mast_data(config, config_dir)

Load time series data for all masts in configuration.

# Arguments
- `config`: ReportReconstructCrossConfiguration
- `config_dir::String`: Config directory path for resolving relative paths

# Returns
- `Dict{String, TimeSeriesData}`: Dictionary mapping mast names to loaded data

# Description
Loads all mast time series data with proper error handling for missing files.
"""
function load_all_mast_data(config, config_dir::String)::Dict{String, TimeSeriesData}
    mast_data = Dict{String, TimeSeriesData}()

    for mast_config in config.masts
        println("  📈 Loading $(mast_config.name)...")
        mast_data[mast_config.name] = load_timeseries(mast_config.input, config_dir)

        # Basic data validation
        ts = mast_data[mast_config.name]
        println("    ✓ Loaded $(nrow(ts.df)) records from $(first(ts.df.timestamp)) to $(last(ts.df.timestamp))")
    end

    return mast_data
end

"""
    analyze_mast_pair(target_ts, source_ts, target_name, source_name)

Perform complete analysis for a single mast pair.

# Arguments
- `target_ts::TimeSeriesData`: Target mast time series
- `source_ts::TimeSeriesData`: Source mast time series  
- `target_name::String`: Target mast name
- `source_name::String`: Source mast name

# Returns
- `Union{AnalyzePairResult, Nothing}`: Analysis result or nothing if analysis impossible

# Description
Performs comprehensive cross-mast analysis:
1. Data coverage analysis
2. Wind speed correlations with missing value handling
3. Wind direction differences with circular math
4. Summary statistics generation
"""
function analyze_mast_pair(target_ts::TimeSeriesData, source_ts::TimeSeriesData, 
                           target_name::String, source_name::String)::Union{AnalyzePairResult, Nothing}
    
    # 1. Data coverage analysis
    coverage = analyze_mast_pair_coverage(target_ts, source_ts)
    
    if isnothing(coverage)
        @warn "  ⚠️  No coverage analysis possible for $(target_name) ← $(source_name)"
        return nothing
    end
    
    if coverage.overlap_days < 1.0
        @warn "  ⚠️  Insufficient overlap for analysis: $(round(coverage.overlap_days, digits=1)) days"
        return nothing
    end
    
    # 2. Wind speed correlation analysis
    speed_correlations = analyze_windspeed_correlations(target_ts, source_ts)
    speed_summary = summarize_correlations(speed_correlations)
    
    # 3. Wind direction analysis
    direction_analysis = analyze_winddirection_differences(target_ts, source_ts)
    direction_summary = summarize_direction_analysis(direction_analysis)
    
    println("    📊 Coverage: $(round(coverage.overlap_days, digits=1)) days")
    println("    🌪️  Speed correlations: $(length(speed_correlations)) pairs, best = $(floor(speed_summary.best_high_elevation_correlation * 1000) / 1000)")
    println("    🧭 Direction analysis: $(length(direction_analysis)) pairs, best std = $(round(direction_summary.best_high_elevation_std, digits=1))°")
    
    return AnalyzePairResult(
        target_name,
        source_name, 
        coverage,
        speed_correlations,
        direction_analysis,
        speed_summary,
        direction_summary
    )
end

"""
    filter_valid_results(results)

Filter out invalid or insufficient analysis results.

# Arguments
- `results::Vector`: Array of AnalyzePairResult or Nothing

# Returns
- `Vector{AnalyzePairResult}`: Filtered valid results

# Description
Removes nothing values and results with insufficient data for meaningful analysis.
"""
function filter_valid_results(results::Vector)::Vector{AnalyzePairResult}
    return filter(!isnothing, results)
end

end # module 