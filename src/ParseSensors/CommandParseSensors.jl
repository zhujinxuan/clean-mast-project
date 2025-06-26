# src/ParseSensors/CommandParseSensors.jl
"""
Standalone command for parsing sensor data based on a TOML configuration file.
"""
module CommandParseSensors

using DataFrames, CSV
using ...Types.Utils: to_dict, from_dict, strip_nothing_values
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration, SensorFormatConfig, ParseSensorsFileConfig,
                                  ParseSensorsConfigurationNormalized, ParseSensorsFileConfigNormalized,
                                  ParseSensorsOutputConfigNormalized
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

    normalized_files = ParseSensorsFileConfigNormalized[]

    for file_config in config.files
        # Normalize paths
        input_path = abspath(joinpath(project_dir, file_config.input))

        # Calculate default name
        name = something(file_config.name, splitext(basename(input_path))[1])

        # Load sensor format
        sensor_format = if file_config.sensor isa String
            sensor_path = abspath(joinpath(project_dir, file_config.sensor))
            sensor_dict = load_dict(sensor_path)
            # The config is at the top level of the sensor format file
            from_dict(SensorFormatConfig, sensor_dict)
        else
            file_config.sensor
        end

        # Normalize output paths
        output_data = abspath(joinpath(project_dir, something(file_config.output.output_data, "raw/$(name).csv")))
        output_sensor = abspath(joinpath(project_dir, something(file_config.output.output_sensor, "raw/$(name).sensors.toml")))
        
        normalized_output = ParseSensorsOutputConfigNormalized(output_data, output_sensor)

        push!(normalized_files, ParseSensorsFileConfigNormalized(
            input_path,
            name,
            sensor_format,
            normalized_output
        ))
    end

    return ParseSensorsConfigurationNormalized(normalized_files)
end

"""
    execute(config_path::String)

Main entry point for the parse-sensors command.
Loads the configuration, iterates through files, and processes them.
"""
function execute(config_path::String)
    println("Executing new Parse Sensors command...")
    
    config = load_and_normalize_config(config_path)

    for file_config in config.files
        println("Processing input file: $(file_config.input)...")
        process_single_file(file_config)
    end
    
    println("\nSensor processing completed successfully.")
end

"""
    process_single_file(file_config::ParseSensorsFileConfigNormalized)

Processes a single data file according to its normalized configuration.
"""
function process_single_file(file_config::ParseSensorsFileConfigNormalized)
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
        save_outputs(df_transformed, sensors, file_config)

    catch e
        @error "Failed to process file $(file_config.input):" exception=(e, catch_backtrace())
    end
end

"""
    save_outputs(df::DataFrame, sensors::Vector{ParsedSensor}, file_config::ParseSensorsFileConfigNormalized)

Saves the processed DataFrame and sensor metadata to their destination files.
"""
function save_outputs(df::DataFrame, sensors::Vector{ParsedSensor}, file_config::ParseSensorsFileConfigNormalized)
    # Ensure output directories exist
    mkpath(dirname(file_config.output.output_data))
    mkpath(dirname(file_config.output.output_sensor))
    
    # Save data
    CSV.write(file_config.output.output_data, df)
    println("✓ Saved processed data to: $(file_config.output.output_data)")
    
    # Save sensor metadata, stripping nothing values for TOML compatibility
    # TOML does not support null values, so we must remove them before writing.
    open(file_config.output.output_sensor, "w") do io
        cleaned_sensors = map(s -> strip_nothing_values(to_dict(s)), sensors)
        TOML.print(io, Dict("sensors" => cleaned_sensors))
    end
    println("✓ Saved sensor metadata to: $(file_config.output.output_sensor)")
end

end # end module 