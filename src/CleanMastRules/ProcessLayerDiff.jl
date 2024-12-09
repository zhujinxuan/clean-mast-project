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
using Dates
using ...Types.CleanRules
using ..ProcessTypes
using ...MastTimeSeries

struct LayerComparison
  lower_col::Symbol
  wind_speed_col::Union{Nothing, Symbol}
end

find_wind_speed_column(height::Float64, sensors::Vector{SensorColumn}, 
                       max_height_diff::Float64=10.0)::Union{Symbol, Nothing} = 
  let speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", sensors)
    isempty(speed_sensors) && return nothing
    height_diffs = map(s -> abs(s.height - height), speed_sensors)
    min_diff = minimum(height_diffs)
    min_diff > max_height_diff ? nothing : speed_sensors[argmin(height_diffs)].columnName
  end

find_lower_layer_columns(target_col::SensorColumn, sensors::Vector{SensorColumn}, 
                         height_diff::Float64)::Vector{LayerComparison} = 
  filter(sensors) do s
    s.sensorType == target_col.sensorType &&
    s.statType == target_col.statType &&
    s.height < target_col.height &&
    (target_col.height - s.height) ≤ height_diff
  end |> 
  sensor_list -> map(s -> LayerComparison(
    s.columnName, 
    find_wind_speed_column(s.height, sensors) 
  ), sensor_list) 

function calc_difference(upper_val::Float64, lower_val::Float64, sensor_type::String)::Float64 
  if (sensor_type == "WindDirection")
  return min(abs(upper_val - lower_val), 360 - abs(upper_val - lower_val))
  end
  return abs(upper_val - lower_val)
end

"""
Shall pass if wind speed column is within range
"""
function check_speed_criteria(speed::Union{Missing, Float64}, criteria::RangeCriteria)::Bool
  if (ismissing(speed)) 
    return true
  end

  return (isnothing(criteria.min) || speed >= criteria.min) &&
  (isnothing(criteria.max) || speed <= criteria.max)

end

"""
Shall pass if layer difference is out of range
"""
function check_diff_criteria(diff::Float64, criteria::RangeCriteria)::Bool
  return (!isnothing(criteria.min) && diff < criteria.min) ||
  (!isnothing(criteria.max) && diff > criteria.max)
end

mk_timestamps(rule:: Rule, data:: TimeSeriesData, comparison::LayerComparison, target_sensor:: SensorColumn) :: Vector{DateTime} = filter(collect(enumerate(zip(
        data.df[!, target_sensor.columnName], 
        data.df[!, comparison.lower_col],
      )))) do (index, (upper, lower))
          if any(x -> ismissing(x), (upper, lower))
            return false
          end

          diff = calc_difference(upper, lower, target_sensor.sensorType)

          if !check_diff_criteria(
            diff,
            rule.criteria.abs_diff
          )
            return false
          end

          ws_col = comparison.wind_speed_col
          if (isnothing(ws_col)) 
            return true
          end
          return check_speed_criteria(data.df[index, ws_col], rule.criteria.lower_wind_speed) 
        end |> x -> map(first,x) |> x -> data.df[x,:timestamp] 

function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
  @assert rule.criteria isa LayerDifferenceCriteria
  violations = RuleViolation[]
  for col in (filter_applicable_columns(rule, data.sensors))
    target_sensor = first(filter(s -> s.columnName == col, data.sensors))
    layer_comparisons = find_lower_layer_columns(target_sensor, data.sensors, rule.criteria.lower_layer_height)
    timestamps = map(
      comparison-> mk_timestamps(rule, data, comparison, target_sensor), layer_comparisons
    ) |> Iterators.flatten |> unique |> sort 
      batch_violations =map(x-> RuleViolation(rule, x, col), timestamps)
    append!(violations, batch_violations)
  end
  return violations
end

export apply

end # module
