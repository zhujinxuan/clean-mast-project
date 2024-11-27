# src/CleanMastRules/ProcessLayerDiff.jl
"""
Layer Difference Rule Processing:
Compares measurements between different heights:
- For wind speed: flags if difference between layers exceeds threshold
- For wind direction: handles circular difference (e.g. 350° vs 10°)
- Uses closest available wind speed measurement within 10m for validation
- Supports configurable height differences and thresholds
- Can require specific wind speed ranges at lower height
"""
module ProcessLayerDiff

using DataFrames
using ..Rules
using ..ProcessTypes
using ...MastTimeSeries

struct LayerComparison
    lower_col::String
    wind_speed_col::String
end

find_wind_speed_column(height::Float64, sensors::Vector{SensorColumn}, 
                      max_height_diff::Float64=10.0)::Union{String, Nothing} = 
    let speed_sensors = filter(s -> s.sensorType == "WindSpeed", sensors)
        isempty(speed_sensors) && return nothing
        height_diffs = map(s -> abs(s.height - height), speed_sensors)
        min_diff = minimum(height_diffs)
        min_diff > max_height_diff ? nothing : speed_sensors[argmin(height_diffs)].columnName
    end

find_lower_layer_columns(target_col::SensorColumn, sensors::Vector{SensorColumn}, 
                        height_diff::Float64)::Vector{LayerComparison} = 
    filter(sensors) do s
        s.sensorType == target_col.sensorType &&
        s.height < target_col.height &&
        (target_col.height - s.height) ≤ height_diff
    end |> 
    sensor_list -> map(s -> LayerComparison(
        s.columnName, 
        find_wind_speed_column(s.height, sensors) 
    ), sensor_list) |>
    comparisons -> filter(c -> !isnothing(c.wind_speed_col), comparisons)

calc_difference(upper_val::Float64, lower_val::Float64, sensor_type::String)::Float64 = 
    sensor_type == "WindDirection" ? 
        min(abs(upper_val - lower_val), 360 - abs(upper_val - lower_val)) :
        abs(upper_val - lower_val)

check_speed_criteria(speed::Float64, criteria::RangeCriteria)::Bool = 
    (isnothing(criteria.min) || speed ≥ criteria.min) &&
    (isnothing(criteria.max) || speed ≤ criteria.max)

check_diff_criteria(diff::Float64, criteria::RangeCriteria)::Bool = 
    (!isnothing(criteria.min) && diff < criteria.min) ||
    (!isnothing(criteria.max) && diff > criteria.max)

function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    @assert rule.criteria isa LayerDifferenceCriteria
    violations = RuleViolation[]
    for col in filter_applicable_columns(rule, data.sensors)
      target_sensor = first(filter(s -> s.columnName == col, data.sensors))
      layer_comparisons = find_lower_layer_columns(target_sensor, data.sensors, rule.criteria.lower_layer_height)
      
      timestamps = map(layer_comparisons) do comparison
        filter(zip(data.df[!, data.timestamp_column],
                    data.df[!, col], 
                    data.df[!, comparison.lower_col],
                    data.df[!, comparison.wind_speed_col])) do (ts, upper, lower, speed)
              !any(ismissing, (upper, lower, speed)) &&
              check_speed_criteria(speed, rule.criteria.lower_wind_speed) &&
              check_diff_criteria(
                  calc_difference(upper, lower, target_sensor.sensorType),
                  rule.criteria.abs_diff
              )
        end |> x -> map(first, x)  # extract timestamps from filtered tuples
      end |> Iterators.flatten |> unique |> sort

      batch_violations = map(x-> RuleViolation(rule, x, col), timestamps)
      apply_missing!(batch_violations, data)
      append!(violations, batch_violations)
    end
    return violations
end

export apply

end # module
