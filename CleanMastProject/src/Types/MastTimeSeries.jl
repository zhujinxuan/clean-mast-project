module MastTimeSeries

using DataFrames, Dates, CSV, TOML, JSON, YAML
using Parquet2
using DataAPI
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
    sensors::Union{String, Nothing}
end

function from_dict(::Type{TimeSeriesSource}, dict::Dict{String, Any}) :: TimeSeriesSource
    return TimeSeriesSource(dict["data"], get(dict, "sensors", nothing))
end

function to_dict(source::TimeSeriesSource) :: Dict{String, Any}
    return Dict{String, Any}(
        "data" => source.data,
        "sensors" => source.sensors
    )
end

"""
    adjust_relative_path(path::String, prefix::String)::String

Adjust a relative path by prepending a prefix.
Absolute paths are returned unchanged.

# Arguments
- `path::String`: Original path (relative or absolute)
- `prefix::String`: Prefix to prepend to relative paths (e.g., "../")

# Returns
- `String`: Adjusted path

# Examples
```julia
adjust_relative_path("./data/file.csv", "../")  # → "../data/file.csv"
adjust_relative_path("data/file.csv", "../")    # → "../data/file.csv"
adjust_relative_path("C:/abs/file.csv", "../")  # → "C:/abs/file.csv" (unchanged)
adjust_relative_path("/abs/file.csv", "../")    # → "/abs/file.csv" (unchanged)
```
"""
function adjust_relative_path(path::String, prefix::String)::String
    # Return absolute paths unchanged
    isabspath(path) && return path

    # For relative paths, prepend prefix
    if startswith(path, "./")
        return prefix * path[3:end]
    else
        return prefix * path
    end
end

"""
    adjust_timeseries_source_paths(source::TimeSeriesSource, prefix::String)::TimeSeriesSource

Adjust paths in a TimeSeriesSource by prepending prefix to relative paths.
Absolute paths are preserved.

# Arguments
- `source::TimeSeriesSource`: TimeSeriesSource with data and sensors paths
- `prefix::String`: Prefix to prepend (e.g., "../" for report-masts)

# Returns
- `TimeSeriesSource`: New TimeSeriesSource with adjusted paths

# Examples
```julia
source = TimeSeriesSource("./data/raw.csv", "./data/sensors.toml")
adjusted = adjust_timeseries_source_paths(source, "../")
# adjusted.data == "../data/raw.csv"
# adjusted.sensors == "../data/sensors.toml"
```
"""
function adjust_timeseries_source_paths(source::TimeSeriesSource, prefix::String)::TimeSeriesSource
    return TimeSeriesSource(
        adjust_relative_path(source.data, prefix),
        isnothing(source.sensors) ? nothing : adjust_relative_path(source.sensors, prefix)
    )
end

"""
    convert_csv_to_parquet_path(path::String)::String

Convert a CSV file path to a Parquet file path by replacing the .csv extension.
If the path doesn't end with .csv, returns it unchanged.

# Arguments
- `path::String`: File path that may contain .csv extension

# Returns
- `String`: Path with .csv replaced by .parquet

# Examples
```julia
convert_csv_to_parquet_path("./data/file.csv")  # → "./data/file.parquet"
convert_csv_to_parquet_path("./data/file.parquet")  # → "./data/file.parquet" (unchanged)
```
"""
function convert_csv_to_parquet_path(path::String)::String
    return replace(path, r"\.csv$" => ".parquet")
end

"""
    adjust_timeseries_source_paths_to_parquet(source::TimeSeriesSource, prefix::String)::TimeSeriesSource

Adjust paths in a TimeSeriesSource by prepending prefix and converting CSV to Parquet.
Used for report configurations that read clean output (Parquet format).

# Arguments
- `source::TimeSeriesSource`: TimeSeriesSource with data and sensors paths
- `prefix::String`: Prefix to prepend (e.g., "../" for report-masts)

# Returns
- `TimeSeriesSource`: New TimeSeriesSource with adjusted paths and .parquet extension
"""
function adjust_timeseries_source_paths_to_parquet(source::TimeSeriesSource, prefix::String)::TimeSeriesSource
    return TimeSeriesSource(
        convert_csv_to_parquet_path(adjust_relative_path(source.data, prefix)),
        isnothing(source.sensors) ? nothing : adjust_relative_path(source.sensors, prefix)
    )
end

export TimeSeriesData, TimeRange, TimeSeriesSource, load_timeseries, save_timeseries, slice_timeseries_by_range, adjust_relative_path, adjust_timeseries_source_paths, adjust_timeseries_source_paths_to_parquet, convert_csv_to_parquet_path

"""
    detect_file_format(path::String)::Symbol

Detect the file format from the file extension.

# Arguments
- `path::String`: File path to check

# Returns
- `Symbol`: :csv, :parquet, or :unknown
"""
function detect_file_format(path::String)::Symbol
    ext = lowercase(splitext(path)[2])
    if ext == ".csv"
        return :csv
    elseif ext == ".parquet" || ext == ".parq"
        return :parquet
    else
        return :unknown
    end
end

"""
    extract_sensors_from_parquet(ds::Parquet2.Dataset)::Vector{SensorColumn}

Extract sensor metadata from Parquet column metadata.

# Arguments
- `ds::Parquet2.Dataset`: Parquet dataset

# Returns
- `Vector{SensorColumn}`: List of sensors extracted from column metadata
"""
function extract_sensors_from_parquet(ds::Parquet2.Dataset)::Vector{SensorColumn}
    sensors = SensorColumn[]
    
    # Access the first row group to get columns
    if length(ds) == 0
        return sensors
    end
    
    rg = ds[1]
    for col in rg
        col_name = Parquet2.name(col)
        # Skip timestamp column
        if col_name == "timestamp"
            continue
        end
        
        # Extract sensor metadata from column metadata
        col_meta = DataAPI.metadata(col)
        
        # Clean column name - remove null bytes that can come from Parquet metadata
        clean_col_name = replace(col_name, "\0" => "")
        
        if !isnothing(col_meta) && haskey(col_meta, "sensorType")
            sensor = SensorColumn(
                Symbol(clean_col_name),
                col_meta["sensorType"],
                get(col_meta, "sensorDirection", "N/A"),
                parse(Float64, get(col_meta, "height", "0.0")),
                get(col_meta, "statType", "avg"),
                get(col_meta, "unit", "")
            )
            push!(sensors, sensor)
        else
            # If no metadata, create a basic sensor column
            sensor = SensorColumn(
                Symbol(clean_col_name),
                "Unknown",
                "N/A",
                0.0,
                "avg",
                ""
            )
            push!(sensors, sensor)
        end
    end
    
    return sensors
end

"""
    sensors_to_column_metadata(sensors::Vector{SensorColumn})::Dict{String, Dict{String, String}}

Convert sensor definitions to Parquet column metadata format.

# Arguments
- `sensors::Vector{SensorColumn}`: List of sensors

# Returns
- `Dict{String, Dict{String, String}}`: Column metadata dictionary for Parquet2.writefile
"""
function sensors_to_column_metadata(sensors::Vector{SensorColumn})::Dict{String, Dict{String, String}}
    metadata = Dict{String, Dict{String, String}}()
    
    for sensor in sensors
        col_name = String(sensor.columnName)
        metadata[col_name] = Dict{String, String}(
            "sensorType" => sensor.sensorType,
            "sensorDirection" => sensor.sensorDirection,
            "height" => string(sensor.height),
            "statType" => sensor.statType,
            "unit" => sensor.unit
        )
    end
    
    return metadata
end

function resolve_absolute_path(source::TimeSeriesSource, base_dir::String) :: TimeSeriesSource
    data_path = joinpath(base_dir, source.data)
    sensors_path = isnothing(source.sensors) ? nothing : joinpath(base_dir, source.sensors)
    return TimeSeriesSource(data_path, sensors_path)
end

function load_timeseries(config_source::TimeSeriesSource, base_dir::String)::TimeSeriesData
    source = resolve_absolute_path(config_source, base_dir)

    if !isfile(source.data)
        error("Time series data file not found: $source.data")
    end

    format = detect_file_format(source.data)
    
    if format == :parquet
        return load_timeseries_parquet(source)
    elseif format == :csv
        return load_timeseries_csv(source)
    else
        # Default to CSV for unknown formats, but require sensors file
        if isnothing(source.sensors)
            error("Sensors metadata file path is required for CSV format")
        end
        return load_timeseries_csv(source)
    end
end

"""
    load_timeseries_csv(source::TimeSeriesSource)::TimeSeriesData

Load time series data from CSV format with separate sensors metadata file.
"""
function load_timeseries_csv(source::TimeSeriesSource)::TimeSeriesData
    if isnothing(source.sensors)
        error("Sensors metadata file not specified")
    end
    if !isfile(source.sensors)
        error("Sensors metadata file not found: $(source.sensors)")
    end

    sensors_dict = load_dict(source.sensors)
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_dict["sensors"]]

    df = CSV.read(
        source.data,
        DataFrame;
        ntasks=1,
        copycols=true,
        types=Dict(
            :timestamp => DateTime,
            [col => Union{Float64, Missing} for col in map(s -> s.columnName, sensors) if col != :timestamp]...
        )
    )

    return TimeSeriesData(df, sensors)
end

"""
    load_timeseries_parquet(source::TimeSeriesSource)::TimeSeriesData

Load time series data from Parquet format with embedded sensor metadata.
"""
function load_timeseries_parquet(source::TimeSeriesSource)::TimeSeriesData
    ds = Parquet2.readfile(source.data)
    df = DataFrame(ds)
    
    # Clean column names - remove null bytes that can come from Parquet metadata
    clean_names = Dict{String, String}()
    for name in names(df)
        clean_name = replace(name, "\0" => "")
        if name != clean_name
            clean_names[name] = clean_name
        end
    end
    if !isempty(clean_names)
        rename!(df, clean_names)
    end
    
    # Extract sensors from column metadata
    sensors = extract_sensors_from_parquet(ds)
    
    return TimeSeriesData(df, sensors)
end

function save_timeseries(config_source::TimeSeriesSource, base_dir::Union{String, Nothing}, data::TimeSeriesData)
    source = resolve_absolute_path(config_source, base_dir)
    output_data_path = source.data
    output_sensors_path = source.sensors

    format = detect_file_format(output_data_path)
    mkpath(dirname(output_data_path))
    
    if format == :parquet
        save_timeseries_parquet(output_data_path, data)
    else
        save_timeseries_csv(output_data_path, output_sensors_path, data)
    end
end

"""
    save_timeseries_csv(output_data_path::String, output_sensors_path::Union{String, Nothing}, data::TimeSeriesData)

Save time series data to CSV format with separate sensors metadata file.
"""
function save_timeseries_csv(output_data_path::String, output_sensors_path::Union{String, Nothing}, data::TimeSeriesData)
    CSV.write(output_data_path, data.df)
    
    if isnothing(output_sensors_path)
        return
    end
    
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
    save_timeseries_parquet(output_path::String, data::TimeSeriesData)

Save time series data to Parquet format with embedded sensor metadata.
"""
function save_timeseries_parquet(output_path::String, data::TimeSeriesData)
    column_metadata = sensors_to_column_metadata(data.sensors)
    
    Parquet2.writefile(
        output_path,
        data.df;
        column_metadata=column_metadata
    )
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