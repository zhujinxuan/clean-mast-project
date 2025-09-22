# src/DataClean/Rules/ProcessAvailability.jl
"""
Availability Rule Processing:
Monitors availability sensors and invalidates all data at the same height when availability falls below threshold:
- Finds Availability sensors matching height criteria
- For each availability sensor below threshold, marks ALL sensors at same height as violations
- Height matching is exact - sensors must have identical height values
- Supports configurable low_threshold parameter
"""
module ProcessAvailability

using DataFrames
using ....Types.CleanRules: Rule, RuleViolation, AvailabilityCriteria
using ..ProcessTypes: filter_applicable_columns
using ....Types.MastTimeSeries: TimeSeriesData
using ....Types.SensorColumns: SensorColumn

function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    @assert rule.criteria isa AvailabilityCriteria
    @assert rule.sensorType == "Availability"
    
    # Find availability sensors that match the rule criteria
    availability_columns = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria
    
    violations = RuleViolation[]
    
    for avail_col in availability_columns
        # Get the availability sensor metadata to find its height
        avail_sensor = first(filter(s -> s.columnName == avail_col, data.sensors))
        target_height = avail_sensor.height
        
        # Find all sensors at the same height (not just availability sensors)
        sensors_at_height = filter(s -> s.height == target_height, data.sensors)
        
        # Find timestamps where availability is below threshold OR missing
        availability_values = data.df[!, avail_col]
        low_availability_indices = findall(x -> ismissing(x) || x < criteria.low_threshold, availability_values)
        violation_timestamps = data.df[low_availability_indices, :timestamp]
        
        # For each sensor at this height, create violations for all low availability timestamps
        for sensor in sensors_at_height
            for timestamp in violation_timestamps
                push!(violations, RuleViolation(rule, timestamp, sensor.columnName))
            end
        end
    end
    
    return violations
end

export apply

end # module