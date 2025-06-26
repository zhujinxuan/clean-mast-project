module WtTimeSeries

using CSV, YAML, DataFrames, Dates
using ...Types.CleanMastConfig
using ...Types.Utils: from_dict
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.SensorColumns: SensorColumn, find_nearest_height_sensor
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
    name = config.mast.name
    
    # Load the sensors from the final representative year step
    sensors_filepath = joinpath(dir, "rep_year_calibration/$(name).sensors.yaml")
    if !isfile(sensors_filepath)
        error("Representative year sensors file not found: $sensors_filepath")
    end
    sensors_yaml = YAML.load_file(sensors_filepath)
    sensors = map(s -> from_dict(SensorColumn, Dict{String,Any}(String(k) => v for (k,v) in s)), 
                 sensors_yaml["sensors"])

    # Determine which heights to process by finding all unique WindSpeed sensor heights >= 120m
    wind_speed_sensors = filter(s -> s.sensorType == "WindSpeed", sensors)
    target_heights = unique([s.height for s in wind_speed_sensors if s.height >= 120.0])
    
    if isempty(target_heights)
        @warn "No WindSpeed sensors found at or above 120m. Nothing to process."
        return
    end

    # Load the main data file once
    rep_year_filepath = joinpath(dir, "rep_year_calibration/$(name).csv")
    if !isfile(rep_year_filepath)
        error("Representative year data file not found: $rep_year_filepath")
    end
    rep_year_df = CSV.read(rep_year_filepath, DataFrame)

    println("Processing WT time series for $(length(target_heights)) height(s):")
    for height in sort(target_heights)
        println("\nProcessing height: $(height)m")
        time_series = TimeSeriesData(rep_year_df, sensors)
        process_single_height(dir, name, height, time_series)
    end
end

"""
Process WT time series for a single height
"""
function process_single_height(dir::String, name::String, target_height::Float64, time_series::TimeSeriesData)
    # Find WindSpeed sensor closest to target height with statType = "avg"
    wind_speed_sensor = find_nearest_height_sensor(target_height, time_series.sensors, "WindSpeed", "avg")
    if isnothing(wind_speed_sensor)
        @warn "No suitable WindSpeed sensor found near height $(target_height)m. Skipping."
        return
    end
    
    # Find WindDirection sensor closest to target height with statType = "avg"
    wind_dir_sensor = find_nearest_height_sensor(target_height, time_series.sensors, "WindDirection", "avg")
    if isnothing(wind_dir_sensor)
        @warn "No suitable WindDirection sensor found near height $(target_height)m. Skipping."
        return
    end
    
    println("- Selected sensors:")
    println("  Wind Speed: $(wind_speed_sensor.columnName) ($(wind_speed_sensor.height)m)")
    println("  Wind Direction: $(wind_dir_sensor.columnName) ($(wind_dir_sensor.height)m)")
    
    # Create a new DataFrame with only the required columns
    wt_df = DataFrame(
        timestamp = time_series.df.timestamp,
        wind_speed = time_series.df[:, wind_speed_sensor.columnName],
        wind_direction = time_series.df[:, wind_dir_sensor.columnName]
    )
    
    # Format timestamp to yyyy-mm-dd HH:MM:ss
    wt_df.timestamp = Dates.format.(wt_df.timestamp, "yyyy-mm-dd HH:MM:ss")
    
    # Save to CSV with height included in filename
    height_str = replace(string(target_height), "." => "_")
    output_filename = "wt-timeseries/$(name)-$(height_str)m.csv"
    mkpath(dirname(joinpath(dir, output_filename)))
    CSV.write(joinpath(dir, output_filename), wt_df)
    
    println("- Saved wind turbine time series data to $(output_filename)")
end

end # module WtTimeSeries 