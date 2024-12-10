module MastTimeSeries

using DataFrames
export SensorColumn, TimeSeriesData

struct SensorColumn
    columnName::Symbol
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String # Could be converted to Float64 later if needed
    height::Float64
    statType::String       # "avg" | "max" | "min" | "sd"
    unit::String
end

struct TimeSeriesData
    df::DataFrame
    sensors::Vector{SensorColumn}
end

end # module 