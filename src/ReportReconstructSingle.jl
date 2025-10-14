module ReportReconstructSingle
using Dates

import ..Types.MastTimeSeries: TimeSeriesData, SensorColumn, TimeRange
import ..Types.ReportReconstructSingleConfiguration: ReportReconstructSingleConfig, ProcessedMastReconstructConfig
import ..TimeSeriesProcessing.Regularization: ensure_regular_intervals
import ..TimeSeriesProcessing.IntervalDetection: detect_representative_interval

# Include sub-modules for different analysis types
include("./ReportReconstructSingle/DataCoverage.jl")
include("./ReportReconstructSingle/WindSpeedCorrelation.jl")
include("./ReportReconstructSingle/WindDirectionDifference.jl")
include("./ReportReconstructSingle/ReportGeneration.jl")
include("./ReportReconstructSingle/RecommendReportReconstructSingleCommand.jl")

# Import specific functions from sub-modules
import .DataCoverage: analyze_data_coverage
import .WindSpeedCorrelation: analyze_wind_speed_correlation
import .WindDirectionDifference: analyze_wind_direction_difference
import .ReportGeneration: generate_reconstruction_report
import .RecommendReportReconstructSingleCommand

"""
    regularize_and_merge_data(before_data::TimeSeriesData, after_data::TimeSeriesData) -> (TimeSeriesData, TimeSeriesData)

Regularize both before and after data to ensure they have the same timestamps with 10-minute intervals.
Missing timestamps will be filled with missing values.
"""
function regularize_and_merge_data(before_data::TimeSeriesData, after_data::TimeSeriesData)
    # Find the common time range
    before_range = TimeRange(
        minimum(before_data.df.timestamp),
        maximum(before_data.df.timestamp)
    )
    after_range = TimeRange(
        minimum(after_data.df.timestamp),
        maximum(after_data.df.timestamp)
    )
    
    # Use the intersection of both time ranges
    common_min = max(before_range.min, after_range.min)
    common_max = min(before_range.max, after_range.max)
    common_range = TimeRange(common_min, common_max)
    
    # Detect representative interval from the after_data (reconstructed data)
    representative_interval = detect_representative_interval(after_data)

    # Regularize both datasets to the representative interval
    before_regular = ensure_regular_intervals(before_data, common_range, representative_interval)
    after_regular = ensure_regular_intervals(after_data, common_range, representative_interval)
    
    return (before_regular, after_regular)
end

"""
    analyze_reconstruction_comparison(config::ReportReconstructSingleConfig)

Run all analyses for reconstruction comparison.

# Arguments
- `config::ReportReconstructSingleConfig`: Configuration with multiple masts

# Returns
- `Dict{String, Any}`: Dictionary with results from all analyses
"""
function analyze_reconstruction_comparison(config::ReportReconstructSingleConfig)
    results = Dict{String, Any}()
    
    @info "Starting reconstruction comparison analysis for $(length(config.masts)) mast(s)"
    
    # Create output directory
    mkpath(config.outputDir)
    
    # Process each mast
    for mast in config.masts
        @info "Processing mast: $(mast.name)"
        
        # Create mast-specific output directory
        mast_dir = joinpath(config.outputDir, mast.name)
        mkpath(mast_dir)
        
        # Regularize and merge data
        @info "Regularizing time series data for consistent timestamps..."
        before_regular, after_regular = regularize_and_merge_data(mast.beforeData, mast.afterData)
        
        # Create a regularized mast config
        regularized_mast = ProcessedMastReconstructConfig(
            mast.name,
            before_regular,
            after_regular
        )
        
        # Data coverage analysis
        @info "Analyzing data coverage and reconstruction rates..."
        coverage_results = analyze_data_coverage(regularized_mast, mast_dir)
        
        # Wind speed correlation analysis
        @info "Analyzing wind speed correlations between heights..."
        speed_correlation_results = analyze_wind_speed_correlation(regularized_mast, mast_dir)
        
        # Wind direction difference analysis
        @info "Analyzing wind direction differences between heights..."
        direction_results = analyze_wind_direction_difference(regularized_mast, mast_dir)
        
        # Store results for this mast
        results[mast.name] = Dict{String, Any}(
            "coverage" => coverage_results,
            "speed_correlation" => speed_correlation_results,
            "direction_difference" => direction_results
        )
    end
    
    # Generate comprehensive Typst report
    @info "Generating comprehensive Typst report..."
    report_path = generate_reconstruction_report(config, results)
    results["report_path"] = report_path
    
    @info "Reconstruction comparison analysis complete"
    
    return results
end

# Export main functions
export analyze_reconstruction_comparison

end # module 