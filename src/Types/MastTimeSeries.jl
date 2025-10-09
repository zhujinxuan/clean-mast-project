module MastTimeSeries

using DataFrames, Dates, CSV, TOML, JSON, YAML
using ..SensorColumns: ParsedSensor, SensorColumn, find_nearest_height_sensor
using ...CleanMastUtils: load_dict
import ..Utils: from_dict, to_dict, strip_nothing_values

struct TimeSeriesData
    df::DataFrame
    sensors::Vector{SensorColumn}
end

struct TimeRange
    min::DateTime
    max::DateTime
end

function to_dict(range::TimeRange) :: Dict{String, Any}
    return Dict{String, Any}(
        "min" => range.min,
        "max" => range.max
    )
end

function from_dict(::Type{TimeRange}, dict::Dict{String, Any}) :: TimeRange
    min_time = DateTime(dict["min"])
    max_time = DateTime(dict["max"])
    return TimeRange(min_time, max_time)
end

struct TimeSeriesSource
    data::String
    sensors::String
end

function from_dict(::Type{TimeSeriesSource}, dict::Dict{String, Any}) :: TimeSeriesSource
    return TimeSeriesSource(dict["data"], dict["sensors"])
end

function to_dict(source::TimeSeriesSource) :: Dict{String, Any}
    return Dict{String, Any}(
        "data" => source.data,
        "sensors" => source.sensors
    )
end

export TimeSeriesData, TimeRange, TimeSeriesSource, load_timeseries, save_timeseries, slice_timeseries_by_range

function resolve_absolute_path(source::TimeSeriesSource, base_dir::String) :: TimeSeriesSource
    return TimeSeriesSource(joinpath(base_dir, source.data), joinpath(base_dir, source.sensors))
end

function load_timeseries(config_source::TimeSeriesSource, base_dir::String)::TimeSeriesData
    source = resolve_absolute_path(config_source, base_dir)

    if !isfile(source.data)
        error("Time series data file not found: $source.data")
    end
    if !isfile(source.sensors)
        error("Sensors metadata file not found: $source.sensors")
    end

    sensors_dict = load_dict(source.sensors)
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_dict["sensors"]]

    df = CSV.read(
        source.data,
        DataFrame;
        types=Dict(
            :timestamp => DateTime,
            [col => Union{Float64, Missing} for col in map(s -> s.columnName, sensors) if col != :timestamp]...
        )
    )

    return TimeSeriesData(df, sensors)
end

function save_timeseries(config_source::TimeSeriesSource, base_dir::Union{String, Nothing}, data::TimeSeriesData)
    source = resolve_absolute_path(config_source, base_dir)
    output_data_path = source.data
    output_sensors_path = source.sensors

    mkpath(dirname(output_data_path))
    CSV.write(output_data_path, data.df)
    
    sensors_dict = Dict{String, Any}("sensors" => [to_dict(s) for s in data.sensors])
    
    ext = splitext(output_sensors_path)[2]

    open(output_sensors_path, "w") do io
        if ext == ".yaml" || ext == ".yml"
            YAML.write(io, sensors_dict)
        elseif ext == ".json"
            JSON.print(io, sensors_dict)
        else # Default to TOML
            TOML.print(io, strip_nothing_values(sensors_dict))
        end
    end
end

"""
    slice_timeseries_by_range(ts::TimeSeriesData, time_range::TimeRange)::TimeSeriesData

Slice time series data to only include timestamps within the specified time range.

# Arguments
- `ts::TimeSeriesData`: Input time series data
- `time_range::TimeRange`: Time range to filter by (inclusive)

# Returns
- `TimeSeriesData`: Sliced time series containing only timestamps within the range
"""
function slice_timeseries_by_range(ts::TimeSeriesData, time_range::TimeRange)::TimeSeriesData
    sliced_df = filter(
        row -> time_range.min <= row.timestamp <= time_range.max,
        ts.df
    )
    return TimeSeriesData(sliced_df, ts.sensors)
end

end # module 