module TowerShading

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: TimeSeriesData
using ...TowerShading: process_tower_shading!
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict

export execute

function execute(dir::String)
    config = parse_config(dir)
    
    # Read clean data file
    name = config.mast.name
    clean_filename = "clean/$(name).csv"
    clean_filepath = joinpath(dir, clean_filename)
    
    if !isfile(clean_filepath)
        error("Clean data file not found: $clean_filepath")
    end
    
    # Read sensors from YAML
    sensors_filepath = joinpath(dir, "clean/$(name).sensors.yaml")
    if !isfile(sensors_filepath)
        error("Sensors file not found: $sensors_filepath")
    end
    
    # Read clean data and sensors
    df = CSV.read(clean_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    
    # Convert YAML sensors to SensorColumn objects
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_yaml["sensors"]]
    
    time_series = TimeSeriesData(df, sensors)
    
    # Process tower shading
    println("Processing tower shading...")
    result = process_tower_shading!(config, time_series)
    
    # Save processed data
    output_filename = "tower_shading/$(name).csv"
    mkpath(dirname(joinpath(dir, output_filename)))
    CSV.write(joinpath(dir, output_filename), result.df)
    
    # Save updated sensors to YAML
    sensors_output_path = "tower_shading/$(name).sensors.yaml"
    sensors_yaml = Dict(
        "sensors" => [to_dict(s) for s in result.sensors]
    )
    open(joinpath(dir, sensors_output_path), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("Tower shading processing completed:")
    println("- Saved processed data to $(output_filename)")
    println("- Saved updated sensors to $(sensors_output_path)")
end

end 