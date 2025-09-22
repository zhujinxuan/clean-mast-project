"""
    CrossMastSpeedCorrelation.jl

Wind speed correlation analysis for cross-mast reconstruction.
Analyzes correlations and linear relationships between wind speed sensors on different masts.
"""
module CrossMastSpeedCorrelation

using DataFrames
using Statistics
using DataFramesMeta
using GLM
using LinearAlgebra

import ...Types.MastTimeSeries: TimeSeriesData
import ...Types.SensorColumns: SensorColumn
import ...Types.CrossMastAnalysisResults: CorrelationSummary
import ...Types.CrossMastSpeedModels: CrossMastSpeedModel, CrossMastSpeedPair
import ...Types.CrossMastTrainParams: CrossMastSpeedTrainParams
import ...Types.MastReferenceModel: train, reconstruct

export analyze_windspeed_correlations, train, reconstruct

"""
    analyze_windspeed_correlations(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Vector{CrossMastSpeedPair}

Analyze wind speed correlations between all sensor pairs on different masts.

# Arguments
- `target_ts::TimeSeriesData`: Target mast time series data
- `source_ts::TimeSeriesData`: Source mast time series data

# Returns
- `Vector{CrossMastSpeedPair}`: Results for all wind speed sensor pairs

# Description
This function performs comprehensive correlation analysis between wind speed sensors:
1. Finds all wind speed sensor pairs between the two masts
2. For each pair, extracts concurrent data points
3. Calculates Pearson correlation coefficient
4. Fits linear regression: target = slope * source + intercept
5. Filters out pairs with insufficient data (< 100 points)

# Example
```julia
correlations = analyze_windspeed_correlations(target_mast, source_mast)
best_corr = get_best_high_elevation_correlation(correlations)
println("Best high-elevation correlation: \$(round(best_corr, digits=3))")
```
"""
function analyze_windspeed_correlations(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Vector{CrossMastSpeedPair}
    # Get wind speed sensors from both masts (avg statType only)
    target_speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", target_ts.sensors)
    source_speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", source_ts.sensors)
    
    if isempty(target_speed_sensors) || isempty(source_speed_sensors)
        @warn "No wind speed sensors found for correlation analysis"
        return CrossMastSpeedPair[]
    end
    
    # Analyze all sensor pairs using functional approach (no merging to avoid column name conflicts)
    results = filter(!isnothing, 
        [analyze_sensor_pair_correlation(target_ts, source_ts, target_sensor, source_sensor)
         for target_sensor in target_speed_sensors
         for source_sensor in source_speed_sensors])
    
    return results
end

"""
    analyze_sensor_pair_correlation(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                   target_sensor::SensorColumn, source_sensor::SensorColumn)::Union{CrossMastSpeedPair, Nothing}

Analyze correlation between a single pair of wind speed sensors on different masts.
"""
function analyze_sensor_pair_correlation(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                       target_sensor::SensorColumn, source_sensor::SensorColumn)::Union{CrossMastSpeedPair, Nothing}
    target_col = target_sensor.columnName
    source_col = source_sensor.columnName
    
    # Check if columns exist in respective dataframes
    if !(target_col in propertynames(target_ts.df)) || !(source_col in propertynames(source_ts.df))
        @debug "Columns not found: $target_col in target or $source_col in source"
        return nothing
    end
    
    # Create merged DataFrame with standardized column names to avoid conflicts
    target_df_subset = select(target_ts.df, :timestamp, target_col => :target)
    source_df_subset = select(source_ts.df, :timestamp, source_col => :source)
    merged_df = innerjoin(target_df_subset, source_df_subset, on = :timestamp)
    
    if nrow(merged_df) < 100  # Minimum data requirement
        @debug "Insufficient concurrent data points: $(nrow(merged_df)) for $target_col vs $source_col"
        return nothing
    end
    
    # Remove missing values
    clean_df = dropmissing(merged_df)
    
    if nrow(clean_df) < 100  # Minimum data requirement after removing missing values
        @debug "Insufficient valid data points for correlation: $(nrow(clean_df)) points for $target_col vs $source_col"
        return nothing
    end
    
    # Extract clean data points
    valid_target = Float64.(clean_df.target)
    valid_source = Float64.(clean_df.source)
    
    # Check for variance in both datasets
    if var(valid_target) == 0.0 || var(valid_source) == 0.0
        @debug "No variance in data for correlation: $target_col vs $source_col"
        return nothing
    end
    
    # Calculate Pearson correlation
    correlation = cor(valid_target, valid_source)
    
    # Fit linear regression: target = slope * source + intercept
    regression_df = DataFrame(target = valid_target, source = valid_source)
    model = lm(@formula(target ~ source), regression_df)

    # Extract regression parameters
    coeffs = coef(model)
    intercept = coeffs[1]
    slope = coeffs[2]

    return CrossMastSpeedPair(
        target_sensor = target_sensor,
        source_sensor = source_sensor,
        correlation = correlation,
        slope = slope,
        intercept = intercept,
        data_points = nrow(clean_df)
    )
end



"""
    train(::Type{CrossMastSpeedModel}, params::CrossMastSpeedTrainParams, 
          target_ts::TimeSeriesData, source_ts::TimeSeriesData)::CrossMastSpeedModel

Train a CrossMastSpeedModel using correlation analysis and configurable filtering.

# Arguments
- `params::CrossMastSpeedTrainParams`: Training parameters with filtering criteria
- `target_ts::TimeSeriesData`: Target mast time series data
- `source_ts::TimeSeriesData`: Source mast time series data

# Returns
- `CrossMastSpeedModel`: Trained model with qualified sensor pairs

# Description
This function trains a wind speed reconstruction model by:
1. Analyzing correlations between all sensor pairs using existing analysis function
2. Applying filtering criteria from params (min_correlation, etc.)
3. Creating complete model ready for reconstruction
"""
function train(::Type{CrossMastSpeedModel}, params::CrossMastSpeedTrainParams, 
               target_ts::TimeSeriesData, source_ts::TimeSeriesData)::CrossMastSpeedModel
    # Use existing analysis function to get all correlations
    correlations = analyze_windspeed_correlations(target_ts, source_ts)
    
    if isempty(correlations)
        @warn "No correlation results found for speed model training"
        return CrossMastSpeedModel(
            target_mast_name = params.target_name,
            source_mast_name = params.source_name,
            pairs = CrossMastSpeedPair[]
        )
    end
    
    # Apply filtering based on parameters
    qualified_correlations = filter(correlations) do corr
        # Basic data quality checks
        if params.exclude_nan_results
            if isnan(corr.correlation)
                return false
            end
        end
        
        # Apply threshold filters
        return (corr.data_points >= params.min_data_points &&
                corr.correlation >= params.min_correlation)
    end
    
    if isempty(qualified_correlations)
        @info "No correlations met filtering criteria for $(params.target_name) <- $(params.source_name)"
        return CrossMastSpeedModel(
            target_mast_name = params.target_name,
            source_mast_name = params.source_name,
            pairs = CrossMastSpeedPair[]
        )
    end
    sort!(qualified_correlations, by = r -> r.correlation, rev = true)
    
    @info "Trained speed model with $(length(qualified_correlations)) qualified pairs: $(params.target_name) <- $(params.source_name)"
    
    # Create the complete model - no conversion needed since analyze_windspeed_correlations returns CrossMastSpeedPair directly
    return CrossMastSpeedModel(
        target_mast_name = params.target_name,
        source_mast_name = params.source_name,
        pairs = qualified_correlations
    )
end

"""
    reconstruct(model::CrossMastSpeedModel, source_ts::TimeSeriesData)::TimeSeriesData

Reconstruct target wind speeds from source mast data using a trained model.

# Arguments
- `model::CrossMastSpeedModel`: Trained speed model
- `source_ts::TimeSeriesData`: Source mast time series data

# Returns
- `TimeSeriesData`: Reconstructed target mast wind speeds

# Description
This function reconstructs wind speeds by:
1. For each sensor pair in the model, applying linear regression
2. Using formula: target = slope * source + intercept
3. **Only filling missing values - does not override already reconstructed values**
4. Applying reasonable bounds (0-50 m/s) for wind speed validation
5. Returning complete TimeSeriesData for target sensors

# Reconstruction Strategy
The function prioritizes sensor pairs by correlation strength (highest first) and only
fills missing values, allowing multiple sensor pairs to contribute without overriding
previously reconstructed data points.
"""
function reconstruct(model::CrossMastSpeedModel, source_ts::TimeSeriesData)::TimeSeriesData
    if isempty(model.pairs)
        @warn "No sensor pairs in model for reconstruction"
        return TimeSeriesData(
            DataFrame(timestamp = source_ts.df.timestamp),
            SensorColumn[]
        )
    end
    
    # Create output DataFrame with same timestamps
    reconstructed_sensors = unique([pair.target_sensor for pair in model.pairs])
    sort!(reconstructed_sensors, by = x -> x.height, rev = true)

    result_df = DataFrame(:timestamp => source_ts.df.timestamp, [x.columnName => missings(Float64,  length(source_ts.df.timestamp)) for x in reconstructed_sensors]...);
    
    # Process each sensor pair
    for pair in model.pairs
        source_col = pair.source_sensor.columnName
        target_col = pair.target_sensor.columnName
        
        # Get source data
        missing_mask = ismissing.(result_df[!, target_col])
        source_data = source_ts.df[missing_mask, source_col];
        reconstruction = pair.slope .* source_data .+ pair.intercept;
        reconstruction = clamp.(reconstruction, 0.0, 50.0);
        result_df[missing_mask, target_col] .= reconstruction
    end
    
    @info "Reconstructed $(length(reconstructed_sensors)) wind speed sensors for $(model.target_mast_name)"
    return TimeSeriesData(result_df, reconstructed_sensors)
end

end # module 