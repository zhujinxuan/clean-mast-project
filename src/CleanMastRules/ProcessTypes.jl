# src/CleanMastRules/ProcessTypes.jl
module ProcessTypes

using DataFrames
using Dates
using ..Rules
using ...MastTimeSeries

struct RuleViolation
    rule::Rule
    timestamp::DateTime
    column::String
end

function filter_applicable_columns(rule::Rule, sensors::Vector{SensorColumn})::Vector{String}
    return [s.columnName for s in sensors if 
        s.sensorType == rule.sensorType &&
        s.statType == "avg" &&
        (isnothing(rule.height.min) || s.height >= rule.height.min) &&
        (isnothing(rule.height.max) || s.height <= rule.height.max)]
end

function apply_missing!(violations::Vector{RuleViolation}, data :: TimeSeriesData) :: Nothing
  df = data.df
  for violation in violations
    # 找到所有符合timestamp的行
    rows_to_modify = findall(row -> row[data.timestamp_column] == violation.timestamp, df)

    for row in rows_to_modify
      if Symbol(violation.column) in names(df)
        df[row, Symbol(violation.column)] = missing
      else
        @warn "Warning: Column $(violation.column) not found in DataFrame."
      end
    end
  end
  return nothing
end

export RuleViolation, filter_applicable_columns, apply_missing!

end # module

