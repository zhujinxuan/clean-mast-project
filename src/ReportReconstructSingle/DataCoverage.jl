module DataCoverage

using DataFrames
using CSV
using Statistics
using DataFramesMeta
import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.ReportReconstructSingleConfiguration: ProcessedMastReconstructConfig

"""
    CoverageStats

Statistics for data coverage analysis.
"""
struct CoverageStats
    sensorName::Symbol
    height::Float64
    sensorType::String
    statType::String
    missingBefore::Int
    missingAfter::Int
    totalPoints::Int
    reconstructedPoints::Int
    reconstructionRate::Float64
    coverageRatioAfter::Float64
end

"""
    calculate_coverage_stats(before_data::TimeSeriesData, after_data::TimeSeriesData) -> Vector{CoverageStats}

Calculate data coverage statistics for all sensors using functional programming patterns.
"""
function calculate_coverage_stats(before_data::TimeSeriesData, after_data::TimeSeriesData)::Vector{CoverageStats}
    # Filter sensors that exist in both datasets
    valid_sensors = filter(sensor -> sensor.columnName ∈ propertynames(after_data.df), before_data.sensors)
    
    # Log warnings for missing sensors
    missing_sensors = filter(sensor -> sensor.columnName ∉ propertynames(after_data.df), before_data.sensors)
    foreach(sensor -> @warn("Sensor $(sensor.columnName) not found in after_data, skipping"), missing_sensors)
    
    # Calculate statistics for each valid sensor using map
    stats = map(valid_sensors) do sensor
        before_col = before_data.df[:, sensor.columnName]
        after_col = after_data.df[:, sensor.columnName]
        
        # Calculate basic statistics
        total_points = length(before_col)
        missing_before = count(ismissing, before_col)
        missing_after = count(ismissing, after_col)
        
        # Points that were missing before but have data after
        reconstructed_points = count(zip(before_col, after_col)) do (before_val, after_val)
            ismissing(before_val) && !ismissing(after_val)
        end
        
        # Calculate rates
        reconstruction_rate = missing_before > 0 ? reconstructed_points / missing_before * 100 : 0.0
        coverage_ratio_after = (total_points - missing_after) / total_points * 100
        
        CoverageStats(
            sensor.columnName,
            sensor.height,
            sensor.sensorType,
            sensor.statType,
            missing_before,
            missing_after,
            total_points,
            reconstructed_points,
            reconstruction_rate,
            coverage_ratio_after
        )
    end
    
    return stats
end

"""
    save_coverage_stats(stats::Vector{CoverageStats}, output_dir::String)

Save coverage statistics to CSV file.
"""
function save_coverage_stats(stats::Vector{CoverageStats}, output_dir::String)
    # Convert to DataFrame
    df = DataFrame(
        sensor_name = [s.sensorName for s in stats],
        height_m = [s.height for s in stats],
        sensor_type = [s.sensorType for s in stats],
        stat_type = [s.statType for s in stats],
        missing_before = [s.missingBefore for s in stats],
        missing_after = [s.missingAfter for s in stats],
        total_points = [s.totalPoints for s in stats],
        reconstructed_points = [s.reconstructedPoints for s in stats],
        reconstruction_rate_percent = [s.reconstructionRate for s in stats],
        coverage_ratio_after_percent = [s.coverageRatioAfter for s in stats]
    )
    
    # Save to CSV
    csv_path = joinpath(output_dir, "data_coverage_stats.csv")
    CSV.write(csv_path, df)
    
    return df
end

"""
    analyze_data_coverage(mast::ProcessedMastReconstructConfig, output_dir::String)

Analyze data coverage and reconstruction rates for a mast.

# Returns
- Dict with coverage statistics
"""
function analyze_data_coverage(mast::ProcessedMastReconstructConfig, output_dir::String)
    @info "Calculating data coverage statistics for mast: $(mast.name)"
    
    # Calculate coverage statistics
    stats = calculate_coverage_stats(mast.beforeData, mast.afterData)
    
    # Save statistics to CSV
    stats_df = save_coverage_stats(stats, output_dir)
    
    # Create summary by sensor type
    wind_speed_stats = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", stats)
    wind_dir_stats = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", stats)
    
    results = Dict{String, Any}(
        "all_stats" => stats,
        "stats_df" => stats_df,
        "wind_speed_stats" => wind_speed_stats,
        "wind_direction_stats" => wind_dir_stats,
        "summary" => Dict(
            "total_sensors" => length(stats),
            "avg_reconstruction_rate" => mean([s.reconstructionRate for s in stats]),
            "avg_coverage_after" => mean([s.coverageRatioAfter for s in stats])
        )
    )
    
    return results
end

export analyze_data_coverage, CoverageStats

end # module 