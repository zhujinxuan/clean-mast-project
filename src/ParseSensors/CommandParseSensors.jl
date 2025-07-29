# src/ParseSensors/CommandParseSensors.jl
"""
Standalone command for parsing sensor data based on a TOML configuration file.
"""
module CommandParseSensors

using DataFrames, CSV
using Dates
using ...Types.Utils: to_dict, from_dict, strip_nothing_values
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration, SensorFormatConfig, ParseSensorsFileConfig,
                                  ParseSensorsConfigurationNormalized, ParseSensorsFileConfigNormalized, InterpolationConfig
using ...Types.MastTimeSeries: TimeSeriesSource, TimeSeriesData, TimeRange
using ...Types.SensorColumns: ParsedSensor, SensorColumn
using ...CleanMastUtils: load_dict
using ..ColumnParser: parse_column_name
using ..FileProcessor: generate_csv_opts
using ..DataFrameProcessor: normalize_timestamp!, rename_and_apply_multipliers!
using ...TimeSeriesProcessing.Regularization: ensure_regular_intervals
using ...TimeSeriesProcessing.Interpolation: interpolate_timeseries
using TOML

export execute

"""
    load_and_normalize_config(config_path::String)

Loads and normalizes the parse-sensors configuration.
- Converts all paths to absolute paths.
- Loads sensor formats from files.
- Calculates default values for missing fields.
"""
function load_and_normalize_config(config_path::String)::ParseSensorsConfigurationNormalized
    config_dict = load_dict(config_path)
    config = from_dict(ParseSensorsConfiguration, config_dict)
    project_dir = dirname(config_path)

    # TODO (don't do it unless i tell you to do) Move this function out of current scope and make it testable;
    function normalize(file_config::ParseSensorsFileConfig)::ParseSensorsFileConfigNormalized
        input_path = abspath(joinpath(project_dir, file_config.input))
        name = something(file_config.name, splitext(basename(input_path))[1])

        sensor_format = if file_config.sensor isa String
            sensor_path = abspath(joinpath(project_dir, file_config.sensor))
            from_dict(SensorFormatConfig, load_dict(sensor_path))
        else
            file_config.sensor
        end

        normalized_output = if file_config.output isa TimeSeriesSource
            file_config.output
        else
            TimeSeriesSource("./raw/$(name).csv", "./raw/$(name).sensors.toml")
        end

        # Create normalized config using from_dict for consistency
        normalized_dict = Dict{String, Any}(
            "input" => input_path,
            "name" => name,
            "sensor" => to_dict(sensor_format),
            "output" => to_dict(normalized_output)
        )

        if !isnothing(file_config.interpolate)
            normalized_dict["interpolate"] = to_dict(file_config.interpolate)
        end

        return from_dict(ParseSensorsFileConfigNormalized, normalized_dict)
    end

    normalized_masts = map(normalize, config.masts)
    normalized_mesos = map(normalize, config.mesos)

    return ParseSensorsConfigurationNormalized(normalized_masts, normalized_mesos)
end

"""
    execute(config_path::String)

Main entry point for the parse-sensors command.
Loads the configuration, iterates through files, and processes them.
"""
function execute(config_path::String)
    println("Executing new Parse Sensors command...")
    
    config = load_and_normalize_config(config_path)

    for file_config in config.masts
        println("Processing mast file: $(file_config.input)...")
        process_single_file(file_config, config_path)
    end

    for file_config in config.mesos
        println("Processing meso file: $(file_config.input)...")
        process_single_file(file_config, config_path)
    end
    
    println("\nSensor processing completed successfully.")
end

"""
    process_single_file(file_config::ParseSensorsFileConfigNormalized)

Processes a single data file according to its normalized configuration.
"""
function process_single_file(file_config::ParseSensorsFileConfigNormalized, config_path::String)
    try
        # 1. Generate CSV options
        csv_opts = generate_csv_opts(file_config.sensor, file_config.input)
        
        # 2. Read data into DataFrame
        df = CSV.read(file_config.input, DataFrame; csv_opts...)
        
        # 3. Normalize timestamp
        normalize_timestamp!(df, file_config.sensor.timestamp_column)
        
        # 4. Parse column metadata
        sensors = [
            s for s in (parse_column_name(String(col), file_config.sensor.columns, file_config.sensor.mappings) for col in names(df)) 
            if !isnothing(s)
        ]
        
        # 5. Transform DataFrame
        df_transformed = rename_and_apply_multipliers!(df, sensors)

        # 6. Apply interpolation if configured
        if !isnothing(file_config.interpolate)
            df_transformed = apply_interpolation(df_transformed, sensors, file_config.interpolate)
        end

        # 7. Save outputs
        save_outputs(df_transformed, sensors, file_config, config_path)

    catch e
        @error "Failed to process file $(file_config.input):" exception=(e, catch_backtrace())
    end
end

"""
    apply_interpolation(df::DataFrame, sensors::Vector{ParsedSensor}, interpolate_config::InterpolationConfig)::DataFrame

Applies interpolation to the DataFrame based on the interpolation configuration.
First ensures regular intervals at from_minutes, then interpolates to to_minutes.
"""
function apply_interpolation(df::DataFrame, sensors::Vector{ParsedSensor}, interpolate_config::InterpolationConfig)::DataFrame
    println("Applying interpolation: $(interpolate_config.from_minutes) min → $(interpolate_config.to_minutes) min")

    # Convert ParsedSensor to SensorColumn for TimeSeriesData
    sensor_columns = [
        SensorColumn(
            Symbol(sensor.columnName),
            sensor.sensorType,
            sensor.sensorDirection,
            sensor.height,
            sensor.statType,
            sensor.unit
        ) for sensor in sensors
    ]

    # Create TimeSeriesData
    ts = TimeSeriesData(df, sensor_columns)

    # Get time range from data
    timestamps = sort(unique(df.timestamp))
    time_range = TimeRange(minimum(timestamps), maximum(timestamps))

    # Step 1: Ensure regular intervals at from_minutes
    from_interval = Minute(interpolate_config.from_minutes)
    ts_regular = ensure_regular_intervals(ts, time_range, from_interval)
    println("✓ Ensured regular $(interpolate_config.from_minutes)-minute intervals")

    # Step 2: Interpolate to to_minutes intervals
    to_interval = Minute(interpolate_config.to_minutes)
    start_time = minimum(timestamps)
    end_time = maximum(timestamps)
    target_timestamps = collect(start_time:to_interval:end_time)

    ts_interpolated = interpolate_timeseries(ts_regular, target_timestamps)
    println("✓ Interpolated to $(interpolate_config.to_minutes)-minute intervals")

    return ts_interpolated.df
end

"""
    save_outputs(df::DataFrame, sensors::Vector{ParsedSensor}, file_config::ParseSensorsFileConfigNormalized)

Saves the processed DataFrame and sensor metadata to their destination files.
"""
function save_outputs(df::DataFrame, sensors::Vector{ParsedSensor}, file_config::ParseSensorsFileConfigNormalized, config_path::String)
    project_dir = dirname(config_path)
    output_data_path = joinpath(project_dir, file_config.output.data)
    output_sensor_path = joinpath(project_dir, file_config.output.sensors)
    
    # Ensure output directories exist
    mkpath(dirname(output_data_path))
    mkpath(dirname(output_sensor_path))
    
    # Save data
    CSV.write(output_data_path, df)
    println("✓ Saved processed data to: $output_data_path")
    
    # Save sensor metadata, stripping nothing values for TOML compatibility
    # TOML does not support null values, so we must remove them before writing.
    open(output_sensor_path, "w") do io
        cleaned_sensors = map(s -> strip_nothing_values(to_dict(s)), sensors)
        TOML.print(io, Dict("sensors" => cleaned_sensors))
    end
    println("✓ Saved sensor metadata to: $output_sensor_path")
end

end # end module 