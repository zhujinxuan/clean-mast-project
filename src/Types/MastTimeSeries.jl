module MastTimeSeries

using DataFrames
using Dates
using ..SensorColumns: ParsedSensor, SensorColumn, find_nearest_height_sensor

struct TimeSeriesData
    df::DataFrame
    sensors::Vector{SensorColumn}
end

struct TimeRange
    min::DateTime
    max::DateTime
end

export TimeSeriesData, TimeRange

end # module 