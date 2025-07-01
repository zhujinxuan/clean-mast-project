# src/ParseSensors/CommandParseSensors.jl
"""
Standalone command for parsing sensor data based on a TOML configuration file.
"""
module CommandParseSensors

using DataFrames, CSV
using ...Types.Utils: to_dict, from_dict, strip_nothing_values
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration, SensorFormatConfig, ParseSensorsFileConfig,
                                  ParseSensorsConfigurationNormalized, ParseSensorsFileConfigNormalized
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.SensorColumns: ParsedSensor
using ...CleanMastUtils: load_dict
using ..ColumnParser: parse_column_name
using ..FileProcessor: generate_csv_opts
using ..DataFrameProcessor: normalize_timestamp!, rename_and_apply_multipliers!
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

        return ParseSensorsFileConfigNormalized(input_path, name, sensor_format, normalized_output)
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
        
        # 6. Save outputs
        save_outputs(df_transformed, sensors, file_config, config_path)

    catch e
        @error "Failed to process file $(file_config.input):" exception=(e, catch_backtrace())
    end
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