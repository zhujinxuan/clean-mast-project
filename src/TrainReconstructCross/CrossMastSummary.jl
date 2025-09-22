"""
    CrossMastSummary.jl

Summary and statistics functions for cross-mast analysis results.
Provides high-level summary statistics for both wind speed correlations and direction analyses.
"""
module CrossMastSummary

using Statistics

import ...Types.CrossMastSpeedModels: CrossMastSpeedPair
import ...Types.CrossMastDirectionModels: CrossMastDirectionPair
import ...Types.CrossMastAnalysisResults: CorrelationSummary, DirectionSummary

export summarize_correlations, summarize_direction_analysis, get_best_high_elevation_correlation, get_best_high_elevation_direction_std

"""
    summarize_correlations(results::Vector{CrossMastSpeedPair})::CorrelationSummary

Create a summary of correlation analysis results.

# Arguments
- `results::Vector{CrossMastSpeedPair}`: Correlation analysis results

# Returns
- `CorrelationSummary`: Summary statistics including counts, best correlations, and high-elevation averages

# Description
This function creates summary statistics for wind speed correlation analysis:
- Counts total and high-elevation sensor pairs (≥120m)
- Identifies best correlations overall and for high-elevation pairs
- Calculates average correlation for high-elevation pairs (most relevant for wind energy)
"""
function summarize_correlations(results::Vector{CrossMastSpeedPair})::CorrelationSummary
    if isempty(results)
        return CorrelationSummary(
            total_pairs = 0,
            high_elevation_pairs = 0,
            best_correlation = 0.0,
            best_high_elevation_correlation = 0.0,
            average_high_elevation_correlation = 0.0
        )
    end

    high_elevation_results = get_high_elevation_correlations(results)

    return CorrelationSummary(
        total_pairs = length(results),
        high_elevation_pairs = length(high_elevation_results),
        best_correlation = maximum(r -> r.correlation, results),
        best_high_elevation_correlation = get_best_high_elevation_correlation(results),
        average_high_elevation_correlation = isempty(high_elevation_results) ? 0.0 :
                                           mean(r -> r.correlation, high_elevation_results)
    )
end

"""
    summarize_direction_analysis(results::Vector{CrossMastDirectionPair})::DirectionSummary

Create a summary of direction analysis results.

# Arguments
- `results::Vector{CrossMastDirectionPair}`: Direction analysis results

# Returns
- `DirectionSummary`: Summary statistics including counts and best std deviations

# Description
This function creates summary statistics for wind direction analysis:
- Counts total and high-elevation sensor pairs (≥120m)
- Identifies best (minimum) standard deviations overall and for high-elevation pairs
"""
function summarize_direction_analysis(results::Vector{CrossMastDirectionPair})::DirectionSummary
    if isempty(results)
        return DirectionSummary(
            total_pairs = 0,
            high_elevation_pairs = 0,
            best_std_deviation = Inf,
            best_high_elevation_std = Inf
        )
    end

    high_elevation_results = get_high_elevation_direction_results(results)

    return DirectionSummary(
        total_pairs = length(results),
        high_elevation_pairs = length(high_elevation_results),
        best_std_deviation = minimum(r -> r.std_deviation, results),
        best_high_elevation_std = get_best_high_elevation_direction_std(results)
    )
end

"""
    get_best_high_elevation_correlation(results::Vector{CrossMastSpeedPair})::Float64

Get the maximum correlation among sensor pairs where both sensors are ≥120m height.

# Arguments
- `results::Vector{CrossMastSpeedPair}`: Correlation analysis results

# Returns
- `Float64`: Maximum correlation among high-elevation pairs, or 0.0 if none found

# Description
This function filters correlation results for high-elevation sensors (≥120m) and returns
the best (maximum) correlation coefficient. This is used for model selection criteria
in cross-mast reconstruction.
"""
function get_best_high_elevation_correlation(results::Vector{CrossMastSpeedPair})::Float64
    if isempty(results)
        return 0.0
    end
    
    # Filter for high-elevation pairs (both sensors ≥120m)
    high_elevation_results = filter(r -> r.target_sensor.height >= 120.0 && 
                                         r.source_sensor.height >= 120.0, results)
    
    if isempty(high_elevation_results)
        @debug "No high-elevation (≥120m) sensor pairs found"
        return 0.0
    end
    
    # Return maximum correlation
    return maximum(r -> r.correlation, high_elevation_results)
end

"""
    get_best_high_elevation_direction_std(results::Vector{CrossMastDirectionPair})::Float64

Get the minimum standard deviation among sensor pairs where both sensors are ≥120m height.

# Arguments
- `results::Vector{CrossMastDirectionPair}`: Direction analysis results

# Returns
- `Float64`: Minimum standard deviation among high-elevation pairs, or Inf if none found

# Description
This function filters direction analysis results for high-elevation sensors (≥120m) and returns
the best (minimum) standard deviation. Lower standard deviation indicates more consistent 
direction relationship, which is better for reconstruction. This is used for model selection 
criteria in cross-mast reconstruction.
"""
function get_best_high_elevation_direction_std(results::Vector{CrossMastDirectionPair})::Float64
    if isempty(results)
        return Inf
    end
    
    # Filter for high-elevation pairs (both sensors ≥120m)
    high_elevation_results = filter(r -> r.target_sensor.height >= 120.0 && 
                                         r.source_sensor.height >= 120.0, results)
    
    if isempty(high_elevation_results)
        @debug "No high-elevation (≥120m) sensor pairs found"
        return Inf
    end
    
    # Return minimum standard deviation (best consistency)
    return minimum(r -> r.std_deviation, high_elevation_results)
end

"""
    get_high_elevation_correlations(results::Vector{CrossMastSpeedPair})::Vector{CrossMastSpeedPair}

Get all correlation results for high-elevation sensor pairs (≥120m).

# Arguments
- `results::Vector{CrossMastSpeedPair}`: All correlation analysis results

# Returns
- `Vector{CrossMastSpeedPair}`: Filtered results for high-elevation pairs only
"""
function get_high_elevation_correlations(results::Vector{CrossMastSpeedPair})::Vector{CrossMastSpeedPair}
    return filter(r -> r.target_sensor.height >= 120.0 && r.source_sensor.height >= 120.0, results)
end

"""
    get_high_elevation_direction_results(results::Vector{CrossMastDirectionPair})::Vector{CrossMastDirectionPair}

Get all direction analysis results for high-elevation sensor pairs (≥120m).

# Arguments
- `results::Vector{CrossMastDirectionPair}`: All direction analysis results

# Returns
- `Vector{CrossMastDirectionPair}`: Filtered results for high-elevation pairs only
"""
function get_high_elevation_direction_results(results::Vector{CrossMastDirectionPair})::Vector{CrossMastDirectionPair}
    return filter(r -> r.target_sensor.height >= 120.0 && r.source_sensor.height >= 120.0, results)
end

end # module 