"""
    CrossMastDirectionAnalysis.jl

Wind direction analysis for cross-mast reconstruction.
Analyzes direction differences and offsets between wind direction sensors on different masts.
"""
module CrossMastDirectionAnalysis

using DataFrames
using Statistics
using DataFramesMeta

import ...Types.MastTimeSeries: TimeSeriesData
import ...Types.SensorColumns: SensorColumn
import ...Types.CrossMastAnalysisResults: DirectionSummary
import ...Types.CrossMastDirectionModels: CrossMastDirectionModel, CrossMastDirectionPair
import ...Types.CrossMastTrainParams: CrossMastDirectionTrainParams
import ...Types.MastReferenceModel: train, reconstruct

export analyze_winddirection_differences, normalize_direction, circular_difference

"""
    analyze_winddirection_differences(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Vector{CrossMastDirectionPair}

Analyze wind direction differences between all sensor pairs on different masts.

# Arguments
- `target_ts::TimeSeriesData`: Target mast time series data
- `source_ts::TimeSeriesData`: Source mast time series data

# Returns
- `Vector{CrossMastDirectionPair}`: Results for all wind direction sensor pairs

# Description
This function performs comprehensive direction analysis between wind direction sensors:
1. Finds all wind direction sensor pairs between the two masts
2. For each pair, extracts concurrent data points
3. Calculates direction differences (handling circular nature of angles)
4. Calculates mean offset and standard deviation
5. Filters out pairs with insufficient data (< 100 points)

The circular nature of wind direction is properly handled (e.g., 359° vs 1° difference is 2°, not 358°).

# Example
```julia
direction_results = analyze_winddirection_differences(target_mast, source_mast)
best_std = get_best_high_elevation_direction_std(direction_results)
println("Best high-elevation direction std: \$(round(best_std, digits=1))°")
```
"""
function analyze_winddirection_differences(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Vector{CrossMastDirectionPair}
    # Get wind direction sensors from both masts (avg statType only)
    target_dir_sensors = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", target_ts.sensors)
    source_dir_sensors = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", source_ts.sensors)
    if isempty(target_dir_sensors)
        @warn "No wind direction sensors found for direction analysis"
        return CrossMastDirectionPair[]
    end
    if isempty(source_dir_sensors)
        @warn "No wind direction sensors found for direction analysis"
        return CrossMastDirectionPair[]
    end
    
    
    results = filter(!isnothing, 
        [analyze_direction_sensor_pair(target_ts, source_ts, target_sensor, source_sensor)
         for target_sensor in target_dir_sensors
         for source_sensor in source_dir_sensors])
    
    return results
end

"""
    analyze_direction_sensor_pair(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                 target_sensor::SensorColumn, source_sensor::SensorColumn)::Union{CrossMastDirectionPair, Nothing}

Analyze direction differences between a single pair of wind direction sensors on different masts.
"""
function analyze_direction_sensor_pair(target_ts::TimeSeriesData, source_ts::TimeSeriesData,
                                      target_sensor::SensorColumn, source_sensor::SensorColumn)::Union{CrossMastDirectionPair, Nothing}
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
    
    if nrow(clean_df) < 100  # Minimum data requirement
        @debug "Insufficient data points for direction analysis: $(nrow(clean_df)) points for $target_col vs $source_col"
        return nothing
    end
    
    valid_target = normalize_direction.(Float64.(clean_df.target))
    valid_source = normalize_direction.(Float64.(clean_df.source))
    
    direction_differences = circular_difference.(valid_target, valid_source) 
    
    # Calculate statistics
    mean_offset = mean(direction_differences)
    std_deviation = std(direction_differences)
    
    return CrossMastDirectionPair(
        target_sensor = target_sensor,
        source_sensor = source_sensor,
        offset = mean_offset,
        std_deviation = std_deviation,
        data_points = nrow(clean_df)
    )
end

"""
    normalize_direction(angle::Float64)::Float64

Normalize a direction angle to [0, 360) range.
"""
function normalize_direction(angle::Float64)::Float64
    return mod(angle, 360.0)
end

"""
    circular_difference(target::Float64, source::Float64)::Float64

Calculate the circular difference between two direction angles.

# Arguments
- `target::Float64`: Target direction in degrees [0, 360)
- `source::Float64`: Source direction in degrees [0, 360)

# Returns
- `Float64`: Direction difference in degrees [-180, 180]

# Description
Calculates the shortest angular difference between two directions, properly handling
the circular nature of angles. The result is signed: positive means target is 
clockwise from source, negative means counter-clockwise.

# Examples
```julia
circular_difference(10.0, 350.0)   # Returns 20.0 (not 340.0)
circular_difference(350.0, 10.0)   # Returns -20.0 (not -340.0)
circular_difference(180.0, 0.0)    # Returns 180.0
circular_difference(0.0, 180.0)    # Returns -180.0
```
"""
function circular_difference(target::Float64, source::Float64)::Float64
    return mod(target - source + 180.0, 360.0) - 180.0
end



"""
    train(::Type{CrossMastDirectionModel}, params::CrossMastDirectionTrainParams,
          target_ts::TimeSeriesData, source_ts::TimeSeriesData)::CrossMastDirectionModel

Train a CrossMastDirectionModel using direction analysis and configurable filtering.

# Arguments
- `params::CrossMastDirectionTrainParams`: Training parameters with filtering criteria
- `target_ts::TimeSeriesData`: Target mast time series data
- `source_ts::TimeSeriesData`: Source mast time series data

# Returns
- `CrossMastDirectionModel`: Trained model with qualified sensor pairs

# Description
This function trains a wind direction reconstruction model by:
1. Analyzing direction differences between all sensor pairs using existing analysis function
2. Applying filtering criteria from params (max_std_deviation, max_abs_offset, etc.)
3. Converting qualified results to CrossMastDirectionPair objects
4. Creating complete model ready for reconstruction
"""
function train(::Type{CrossMastDirectionModel}, params::CrossMastDirectionTrainParams,
               target_ts::TimeSeriesData, source_ts::TimeSeriesData)::CrossMastDirectionModel
    # Use existing analysis function to get all direction analyses
    direction_results = analyze_winddirection_differences(target_ts, source_ts)
    
    if isempty(direction_results)
        @warn "No direction analysis results found for direction model training"
        return CrossMastDirectionModel(
            target_mast_name = params.target_name,
            source_mast_name = params.source_name,
            pairs = CrossMastDirectionPair[]
        )
    end
    
    # Apply filtering based on parameters
    qualified_results = filter(direction_results) do result
        # Basic data quality checks
        if params.exclude_nan_results
            if isnan(result.offset) || isnan(result.std_deviation)
                return false
            end
        end
        
        # Apply threshold filters
        return (result.data_points >= params.min_data_points &&
                result.std_deviation <= params.max_std_deviation &&
                abs(result.offset) <= params.max_abs_offset)
    end
    
    if isempty(qualified_results)
        @info "No direction results met filtering criteria for $(params.target_name) <- $(params.source_name)"
        return CrossMastDirectionModel(
            target_mast_name = params.target_name,
            source_mast_name = params.source_name,
            pairs = CrossMastDirectionPair[]
        )
    end
    
    # Sort by std_deviation (best first)
    sort!(qualified_results, by = x -> x.std_deviation)
    
    @info "Trained direction model with $(length(qualified_results)) qualified pairs: $(params.target_name) <- $(params.source_name)"
    
    # Create the complete model - no conversion needed since analyze_winddirection_differences returns CrossMastDirectionPair directly
    return CrossMastDirectionModel(
        target_mast_name = params.target_name,
        source_mast_name = params.source_name,
        pairs = qualified_results
    )
end

"""
    reconstruct(model::CrossMastDirectionModel, source_ts::TimeSeriesData)::TimeSeriesData

Reconstruct target wind directions from source mast data using a trained model.

# Arguments
- `model::CrossMastDirectionModel`: Trained direction model
- `source_ts::TimeSeriesData`: Source mast time series data

# Returns
- `TimeSeriesData`: Reconstructed target mast wind directions

# Description
This function reconstructs wind directions by:
1. For each sensor pair in the model, applying offset correction
2. Using formula: target = source + offset (with circular wrapping)
3. **Only filling missing values - does not override already reconstructed values**
4. Applying circular normalization to [0, 360) range
5. Returning complete TimeSeriesData for target sensors

# Reconstruction Strategy
The function prioritizes sensor pairs by standard deviation (lowest first) and only
fills missing values, allowing multiple sensor pairs to contribute without overriding
previously reconstructed data points.
"""
function reconstruct(model::CrossMastDirectionModel, source_ts::TimeSeriesData)::TimeSeriesData
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

    result_df = DataFrame(:timestamp => source_ts.df.timestamp, [x.columnName => missings(Float64,  length(source_ts.df.timestamp)) for x in reconstructed_sensors]...)
    
    # Process each sensor pair
    for pair in model.pairs
        source_col = pair.source_sensor.columnName
        target_col = pair.target_sensor.columnName
        
        # Get source data
        missing_mask = ismissing.(result_df[!, target_col])
        source_data = source_ts.df[missing_mask, source_col]
        reconstruction = normalize_direction.(source_data .+ pair.offset)
        result_df[missing_mask, target_col] = reconstruction
    end
    
    @info "Reconstructed $(length(reconstructed_sensors)) wind direction sensors for $(model.target_mast_name)"
    
    return TimeSeriesData(result_df, reconstructed_sensors)
end

end # module 