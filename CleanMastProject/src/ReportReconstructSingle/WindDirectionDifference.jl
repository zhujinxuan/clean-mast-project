module WindDirectionDifference

using DataFrames
using CSV
using Statistics
using DataFramesMeta
import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.ReportReconstructSingleConfiguration: ProcessedMastReconstructConfig

"""
    normalize_angle_difference(diff::Float64) -> Float64

Normalize angle difference to [-180, 180] range.
"""
function normalize_angle_difference(diff::Float64)::Float64
    # Use modular arithmetic for more efficient normalization
    normalized = mod(diff + 180, 360) - 180
    return normalized
end

"""
    circular_mean_difference(angles1::Vector{Float64}, angles2::Vector{Float64}) -> Float64

Calculate the mean circular difference between two sets of angles in degrees using functional programming.
Handles the circular nature of angles (e.g., 359° and 1° are 2° apart).
"""
function circular_mean_difference(angles1::Vector{Float64}, angles2::Vector{Float64})
    if length(angles1) != length(angles2)
        error("Angle vectors must have the same length")
    end
    
    # Calculate normalized differences using map and functional composition
    differences = zip(angles1, angles2) |>
                 (pairs -> map(pair -> pair[2] - pair[1], pairs)) |>
                 (diffs -> map(normalize_angle_difference, diffs))
    
    return mean(differences)
end

"""
    circular_std_difference(angles1::Vector{Float64}, angles2::Vector{Float64}) -> Float64

Calculate the standard deviation of circular differences between two sets of angles in degrees using functional programming.
"""
function circular_std_difference(angles1::Vector{Float64}, angles2::Vector{Float64})
    if length(angles1) != length(angles2)
        error("Angle vectors must have the same length")
    end
    
    # Calculate normalized differences using map and functional composition
    differences = zip(angles1, angles2) |>
                 (pairs -> map(pair -> pair[2] - pair[1], pairs)) |>
                 (diffs -> map(normalize_angle_difference, diffs))
    
    return std(differences)
end

"""
    DirectionDifferenceStats

Statistics for wind direction differences between two heights.
"""
struct DirectionDifferenceStats
    height1::Float64
    height2::Float64
    mean_difference::Float64
    std_difference::Float64
    n_valid_pairs::Int
end

"""
    calculate_direction_differences(data::TimeSeriesData) -> Matrix{DirectionDifferenceStats}

Calculate mean and std of wind direction differences between all height pairs using functional programming.
"""
function calculate_direction_differences(data::TimeSeriesData)
    # Get wind direction sensors (avg only) and sort by height (high to low)
    dir_sensors = data.sensors |>
                 (sensors -> filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", sensors)) |>
                 (sensors -> sort(sensors, by = s -> s.height, rev=true))
    
    n_heights = length(dir_sensors)
    heights = map(s -> s.height, dir_sensors)
    
    # Calculate statistics for each pair using map over Cartesian product
    height_pairs = Iterators.product(1:n_heights, 1:n_heights)
    stats_values = map(height_pairs) do (i, j)
        if i == j
            # Same height, zero difference
            return DirectionDifferenceStats(heights[i], heights[j], 0.0, 0.0, 0)
        else
            return calculate_direction_pair_stats(data.df, dir_sensors[i], dir_sensors[j])
        end
    end
    
    # Reshape into matrix
    stats_matrix = reshape(collect(stats_values), n_heights, n_heights)
    
    return stats_matrix, heights
end

"""
    calculate_direction_pair_stats(df::DataFrame, sensor1::SensorColumn, sensor2::SensorColumn) -> Union{DirectionDifferenceStats, Nothing}

Calculate direction difference statistics for a pair of sensors.
"""
function calculate_direction_pair_stats(df::DataFrame, sensor1::SensorColumn, sensor2::SensorColumn)
    col_i = df[:, sensor1.columnName]
    col_j = df[:, sensor2.columnName]
    
    # Find valid (non-missing) pairs using functional composition
    valid_pairs = collect(zip(col_i, col_j)) |>
                 (pairs -> filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), pairs))
    
    n_valid = length(valid_pairs)
    
    if n_valid <= 10
        return nothing  # Not enough data
    end
    
    # Extract angles
    angles_i = map(pair -> Float64(pair[1]), valid_pairs)
    angles_j = map(pair -> Float64(pair[2]), valid_pairs)
    
    # Calculate circular statistics
    mean_diff = circular_mean_difference(angles_i, angles_j)
    std_diff = circular_std_difference(angles_i, angles_j)
    
    return DirectionDifferenceStats(
        sensor1.height, sensor2.height, mean_diff, std_diff, n_valid
    )
end

"""
    create_direction_difference_tables(stats_matrix::Matrix, heights::Vector{Float64}) -> (DataFrame, DataFrame)

Create DataFrames for mean and std differences from the stats matrix using functional programming.
"""
function create_direction_difference_tables(stats_matrix::Matrix, heights::Vector{Float64})
    n_heights = length(heights)
    
    # Extract values using map and functional composition
    indices = Iterators.product(1:n_heights, 1:n_heights)
    
    mean_values = map(indices) do (i, j)
        stats = stats_matrix[i, j]
        return isnothing(stats) ? NaN : stats.mean_difference
    end
    
    std_values = map(indices) do (i, j)
        stats = stats_matrix[i, j]
        return isnothing(stats) ? NaN : stats.std_difference
    end
    
    # Reshape into matrices
    mean_matrix = reshape(collect(mean_values), n_heights, n_heights)
    std_matrix = reshape(collect(std_values), n_heights, n_heights)
    
    # Create DataFrames with functional column creation
    column_names = map(h -> Symbol("$(h)m"), heights)
    
    mean_df = DataFrame(mean_matrix, column_names)
    insertcols!(mean_df, 1, :from_height => heights)
    
    std_df = DataFrame(std_matrix, column_names)
    insertcols!(std_df, 1, :from_height => heights)
    
    return mean_df, std_df
end

"""
    analyze_wind_direction_difference(mast::ProcessedMastReconstructConfig, output_dir::String)

Analyze wind direction differences between different heights.
"""
function analyze_wind_direction_difference(mast::ProcessedMastReconstructConfig, output_dir::String)
    @info "Analyzing wind direction differences for mast: $(mast.name)"
    
    # Calculate direction differences for after reconstruction data
    stats_matrix, heights = calculate_direction_differences(mast.afterData)
    
    # Create tables
    mean_df, std_df = create_direction_difference_tables(stats_matrix, heights)
    
    # Save to CSV
    CSV.write(joinpath(output_dir, "wind_direction_mean_difference.csv"), mean_df)
    CSV.write(joinpath(output_dir, "wind_direction_std_difference.csv"), std_df)
    
    # Calculate summary statistics
    all_stats = filter(!isnothing, vec(stats_matrix))
    valid_pairs = filter(s -> s.height1 != s.height2, all_stats)
    
    summary = Dict(
        "avg_mean_difference" => mean([abs(s.mean_difference) for s in valid_pairs]),
        "avg_std_difference" => mean([s.std_difference for s in valid_pairs]),
        "max_mean_difference" => maximum([abs(s.mean_difference) for s in valid_pairs]),
        "max_std_difference" => maximum([s.std_difference for s in valid_pairs])
    )
    
    results = Dict{String, Any}(
        "stats_matrix" => stats_matrix,
        "heights" => heights,
        "mean_df" => mean_df,
        "std_df" => std_df,
        "summary" => summary
    )
    
    return results
end

export analyze_wind_direction_difference, DirectionDifferenceStats

end # module 