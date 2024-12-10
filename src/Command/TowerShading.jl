module TowerShading

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData
using ...TowerShading: process_tower_shading!

export execute

function execute(dir::String)
    config = parse_config(dir)
    
    # Read clean data file
    original_filename = config.mast.data_path
    clean_filename = "clean_data.$(original_filename).csv"
    clean_filepath = joinpath(dir, clean_filename)
    
    if !isfile(clean_filepath)
        error("Clean data file not found: $clean_filepath")
    end
    
    # Read sensors from YAML
    sensors_filepath = joinpath(dir, "sensors.yaml")
    if !isfile(sensors_filepath)
        error("Sensors file not found: $sensors_filepath")
    end
    
    # Read clean data and sensors
    df = CSV.read(clean_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    
    # Convert YAML sensors to SensorColumn objects
    sensors = [SensorColumn(
        Symbol(s["columnName"]),
        s["sensorType"],
        s["sensorDirection"],
        s["height"],
        s["statType"],
        s["unit"]
    ) for s in sensors_yaml["sensors"]]
    
    time_series = TimeSeriesData(df, sensors)
    
    # Process tower shading
    println("Processing tower shading...")
    result = process_tower_shading!(config, time_series)
    
    # Save processed data
    output_filename = "tower_shading.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), result.df)
    
    # Save updated sensors to YAML
    sensors_yaml = Dict(
        "sensors" => [Dict(
            "columnName" => String(s.columnName),
            "sensorType" => s.sensorType,
            "sensorDirection" => s.sensorDirection,
            "height" => s.height,
            "statType" => s.statType,
            "unit" => s.unit
        ) for s in result.sensors]
    )
    
    open(joinpath(dir, "tower-shading-sensors.yaml"), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("Tower shading processing completed:")
    println("- Saved processed data to $(output_filename)")
    println("- Saved updated sensors to tower-shading-sensors.yaml")
end

end 