module ParseSensors

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: SensorColumn, ParsedSensor
using ...SensorParser: parse_column_metadata, normalize_timestamp!, generate_csv_opts, rename_and_apply_multipliers!
using ...Types.Utils: to_dict

export execute

"""
Process sensors for both mast and meso data.
Creates raw.{data_path}.csv and raw.{data_path}.sensors.yaml files.
"""
function execute(dir::String)
    # Parse config
    config = parse_config(dir)
    
    # Process mast data
    println("Processing mast data sensors...")
    process_data_sensors(dir, config.mast.data_path, config.mast.sensor)
    
    # Process meso data
    println("Processing meso data sensors...")
    process_data_sensors(dir, config.meso.data_path, config.meso.sensor)
    
    println("\nSensor processing completed:")
    println("- Saved raw mast data and sensors")
    println("- Saved raw meso data and sensors")
end

"""
Process sensors for a single data source.
"""
function process_data_sensors(dir::String, data_path::String, sensor_config::SensorConfig)
    # Get full data path
    data_file = joinpath(dir, data_path)
    if !isfile(data_file)
        error("Data file not found: $data_file")
    end
    
    # Generate CSV options
    csv_opts = generate_csv_opts(sensor_config, data_file)
    
    # Read the CSV with all options
    df = CSV.read(data_file, DataFrame; csv_opts...)
    normalize_timestamp!(df, sensor_config.timestamp_column)
    sensors = parse_column_metadata(df, sensor_config)
    df_transformed = rename_and_apply_multipliers!(df, sensors)
    
    # Save raw data
    output_data = "raw.$(data_path).csv"
    CSV.write(joinpath(dir, output_data), df_transformed)
    
    # Save sensors to YAML
    output_sensors = "raw.$(data_path).sensors.yaml"
    sensors_yaml = Dict(
        "sensors" => map(to_dict, sensors)
    )
    open(joinpath(dir, output_sensors), "w") do io
        YAML.write(io, sensors_yaml)
    end
end

end 