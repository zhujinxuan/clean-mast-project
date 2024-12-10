# src/CleanMastRules/ProcessTypes.jl
module ProcessTypes

using DataFrames
using Dates
using ...Types.CleanRules
using ...Types.MastTimeSeries: SensorColumn


function filter_applicable_columns(rule::Rule, sensors::Vector{SensorColumn})::Vector{Symbol}
    return [s.columnName for s in sensors if 
        s.sensorType == rule.sensorType &&
        s.statType == "avg" &&
        (isnothing(rule.height.min) || s.height >= rule.height.min) &&
        (isnothing(rule.height.max) || s.height <= rule.height.max)]
end



export filter_applicable_columns

end # module

