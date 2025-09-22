"""
    CrossMastAnalysisResults.jl

Result types for cross-mast analysis operations.
These types store the results of analyzing relationships between different masts.
"""
module CrossMastAnalysisResults

using Dates
using ..SensorColumns: SensorColumn
using ..CrossMastSpeedModels: CrossMastSpeedPair
using ..CrossMastDirectionModels: CrossMastDirectionPair
import ..Utils: from_dict, to_dict
using Parameters

export MastPairCoverage, CorrelationSummary, DirectionSummary, MastPairAnalysisResult

"""
    MastPairCoverage

Results from analyzing time series overlap between two masts.

# Fields
- `overlap_start::DateTime`: Start of concurrent data period
- `overlap_end::DateTime`: End of concurrent data period
- `overlap_days::Float64`: Duration of overlap in days
- `concurrent_records::Int`: Number of concurrent valid data points
- `coverage_percentage::Float64`: Percentage of time with concurrent valid data
"""
@with_kw struct MastPairCoverage
    overlap_start::DateTime
    overlap_end::DateTime
    overlap_days::Float64
    concurrent_records::Int
    coverage_percentage::Float64
end





"""
    CorrelationSummary

Summary statistics from wind speed correlation analysis between two masts.

# Fields
- `total_pairs::Int`: Total number of sensor pairs analyzed
- `high_elevation_pairs::Int`: Number of pairs where both sensors ≥120m
- `best_correlation::Float64`: Maximum correlation among all pairs
- `best_high_elevation_correlation::Float64`: Maximum correlation among high-elevation pairs
- `average_high_elevation_correlation::Float64`: Average correlation among high-elevation pairs
"""
@with_kw struct CorrelationSummary
    total_pairs::Int
    high_elevation_pairs::Int
    best_correlation::Float64
    best_high_elevation_correlation::Float64
    average_high_elevation_correlation::Float64
end

"""
    DirectionSummary

Summary statistics from wind direction analysis between two masts.

# Fields
- `total_pairs::Int`: Total number of sensor pairs analyzed
- `high_elevation_pairs::Int`: Number of pairs where both sensors ≥120m
- `best_std_deviation::Float64`: Minimum standard deviation among all pairs
- `best_high_elevation_std::Float64`: Minimum standard deviation among high-elevation pairs
"""
@with_kw struct DirectionSummary
    total_pairs::Int
    high_elevation_pairs::Int
    best_std_deviation::Float64
    best_high_elevation_std::Float64
end

"""
    MastPairAnalysisResult

Complete analysis results for a single mast pair, including all correlations,
direction analyses, summary statistics, and trained model file paths.

# Fields
- `target_mast::String`: Name of target mast
- `source_mast::String`: Name of source mast
- `coverage::MastPairCoverage`: Time series coverage analysis
- `windspeed_correlations::Vector{CrossMastSpeedPair}`: All wind speed correlations
- `winddirection_analysis::Vector{CrossMastDirectionPair}`: All wind direction analyses
- `windspeed_summary::CorrelationSummary`: Summary statistics for wind speed correlations
- `winddirection_summary::DirectionSummary`: Summary statistics for wind direction analysis
- `windspeed_model_file::Union{String, Nothing}`: Path to saved speed model file
- `winddirection_model_file::Union{String, Nothing}`: Path to saved direction model file
"""
@with_kw struct MastPairAnalysisResult
    target_mast::String
    source_mast::String
    coverage::MastPairCoverage
    windspeed_correlations::Vector{CrossMastSpeedPair}
    winddirection_analysis::Vector{CrossMastDirectionPair}
    windspeed_summary::CorrelationSummary
    winddirection_summary::DirectionSummary
    windspeed_model_file::Union{String, Nothing}
    winddirection_model_file::Union{String, Nothing}
end

# from_dict implementations
function from_dict(::Type{MastPairCoverage}, dict::Dict{String, Any})::MastPairCoverage
    overlap_start = DateTime(dict["overlap_start"])
    overlap_end = DateTime(dict["overlap_end"])
    overlap_days = dict["overlap_days"]
    concurrent_records = dict["concurrent_records"]
    coverage_percentage = dict["coverage_percentage"]

    return MastPairCoverage(
        overlap_start, overlap_end, overlap_days,
        concurrent_records, coverage_percentage
    )
end






function from_dict(::Type{CorrelationSummary}, dict::Dict{String, Any})::CorrelationSummary
    total_pairs = dict["total_pairs"]
    high_elevation_pairs = dict["high_elevation_pairs"]
    best_correlation = dict["best_correlation"]
    best_high_elevation_correlation = dict["best_high_elevation_correlation"]
    average_high_elevation_correlation = dict["average_high_elevation_correlation"]

    return CorrelationSummary(
        total_pairs, high_elevation_pairs, best_correlation,
        best_high_elevation_correlation, average_high_elevation_correlation
    )
end


function from_dict(::Type{DirectionSummary}, dict::Dict{String, Any})::DirectionSummary
    total_pairs = dict["total_pairs"]
    high_elevation_pairs = dict["high_elevation_pairs"]
    best_std_deviation = dict["best_std_deviation"]
    best_high_elevation_std = dict["best_high_elevation_std"]

    return DirectionSummary(
        total_pairs, high_elevation_pairs, best_std_deviation, best_high_elevation_std
    )
end


function from_dict(::Type{MastPairAnalysisResult}, dict::Dict{String, Any})::MastPairAnalysisResult
    target_mast = dict["target_mast"]
    source_mast = dict["source_mast"]
    coverage = from_dict(MastPairCoverage, dict["coverage"])
    windspeed_correlations = [from_dict(CrossMastSpeedPair, Dict{String, Any}(r)) for r in dict["windspeed_correlations"]]
    winddirection_analysis = [from_dict(CrossMastDirectionPair, Dict{String, Any}(r)) for r in dict["winddirection_analysis"]]
    windspeed_summary = from_dict(CorrelationSummary, dict["windspeed_summary"])
    winddirection_summary = from_dict(DirectionSummary, dict["winddirection_summary"])
    windspeed_model_file = get(dict, "windspeed_model_file", nothing)
    winddirection_model_file = get(dict, "winddirection_model_file", nothing)
    
    return MastPairAnalysisResult(
        target_mast, source_mast, coverage, windspeed_correlations, 
        winddirection_analysis, windspeed_summary, winddirection_summary,
        windspeed_model_file, winddirection_model_file
    )
end

# to_dict implementations
function to_dict(coverage::MastPairCoverage)::Dict{String, Any}
    return Dict{String, Any}(
        "overlap_start" => string(coverage.overlap_start),
        "overlap_end" => string(coverage.overlap_end),
        "overlap_days" => coverage.overlap_days,
        "concurrent_records" => coverage.concurrent_records,
        "coverage_percentage" => coverage.coverage_percentage
    )
end





function to_dict(summary::CorrelationSummary)::Dict{String, Any}
    return Dict{String, Any}(
        "total_pairs" => summary.total_pairs,
        "high_elevation_pairs" => summary.high_elevation_pairs,
        "best_correlation" => summary.best_correlation,
        "best_high_elevation_correlation" => summary.best_high_elevation_correlation,
        "average_high_elevation_correlation" => summary.average_high_elevation_correlation
    )
end

function to_dict(summary::DirectionSummary)::Dict{String, Any}
    return Dict{String, Any}(
        "total_pairs" => summary.total_pairs,
        "high_elevation_pairs" => summary.high_elevation_pairs,
        "best_std_deviation" => summary.best_std_deviation,
        "best_high_elevation_std" => summary.best_high_elevation_std
    )
end

function to_dict(result::MastPairAnalysisResult)::Dict{String, Any}
    return Dict{String, Any}(
        "target_mast" => result.target_mast,
        "source_mast" => result.source_mast,
        "coverage" => to_dict(result.coverage),
        "windspeed_correlations" => [to_dict(r) for r in result.windspeed_correlations],
        "winddirection_analysis" => [to_dict(r) for r in result.winddirection_analysis],
        "windspeed_summary" => to_dict(result.windspeed_summary),
        "winddirection_summary" => to_dict(result.winddirection_summary),
        "windspeed_model_file" => result.windspeed_model_file,
        "winddirection_model_file" => result.winddirection_model_file
    )
end

end # module 