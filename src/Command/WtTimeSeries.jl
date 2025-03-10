module WtTimeSeries

using CSV, YAML, DataFrames, Dates
using ...Types.CleanMastConfig
using ...Types.Utils: from_dict
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData, find_nearest_height_sensor
using ...CleanMastConfig

export execute

"""
    execute(dir::String)

Process wind turbine time series data.
This command:
1. Finds the target_height from the ProjectConfig
2. Loads the representative year data
3. Finds the WindSpeed and WindDirection sensors closest to target_height
4. Saves timestamp, wind speed, and wind direction to a CSV file

Parameters:
- `dir`: Project directory containing config.yaml
"""
function execute(dir::String)
    # Parse the project configuration
    config = parse_config(dir)
    
    # Get target height from config
    target_height = something(config.analysis.target_height, 120.0)
    println("Using target height: $(target_height)m")
    
    # Read representative year data
    original_filename = config.mast.data_path
    rep_year_filename = "rep_year_calibration.$(original_filename).csv"
    rep_year_filepath = joinpath(dir, rep_year_filename)
    
    if !isfile(rep_year_filepath)
        error("Representative year data file not found: $rep_year_filepath")
    end
    
    # Read sensors from rep_year_calibration-sensors.yaml
    sensors_filepath = joinpath(dir, "rep_year_calibration-sensors.yaml")
    if !isfile(sensors_filepath)
        error("Representative year sensors file not found: $sensors_filepath")
    end
    
    # Read data and sensors
    rep_year_df = CSV.read(rep_year_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    sensors = map(s -> from_dict(SensorColumn, Dict{String,Any}(String(k) => v for (k,v) in s)), 
                 sensors_yaml["sensors"])
    
    # Find WindSpeed sensor closest to target height with statType = "avg"
    wind_speed_sensor = find_nearest_height_sensor(target_height, sensors, "WindSpeed", "avg")
    if isnothing(wind_speed_sensor)
        error("No suitable WindSpeed sensor found near height $(target_height)m")
    end
    
    # Find WindDirection sensor closest to target height with statType = "avg"
    wind_dir_sensor = find_nearest_height_sensor(target_height, sensors, "WindDirection", "avg")
    if isnothing(wind_dir_sensor)
        error("No suitable WindDirection sensor found near height $(target_height)m")
    end
    
    println("Selected sensors:")
    println("- Wind Speed: $(wind_speed_sensor.columnName) ($(wind_speed_sensor.height)m)")
    println("- Wind Direction: $(wind_dir_sensor.columnName) ($(wind_dir_sensor.height)m)")
    
    # Create a new DataFrame with only the required columns
    wt_df = DataFrame(
        timestamp = rep_year_df.timestamp,
        wind_speed = rep_year_df[:, wind_speed_sensor.columnName],
        wind_direction = rep_year_df[:, wind_dir_sensor.columnName]
    )
    
    # Format timestamp to yyyy-mm-dd HH:MM:ss
    wt_df.timestamp = Dates.format.(wt_df.timestamp, "yyyy-mm-dd HH:MM:ss")
    
    # Save to CSV
    output_filename = "wt-timeseries.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), wt_df)
    
    println("\nWind turbine time series processing completed:")
    println("- Saved wind turbine time series data to $(output_filename)")
end

end # module WtTimeSeries 