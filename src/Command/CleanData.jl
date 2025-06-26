module CleanData

using CSV, YAML, DataFrames, Dates, TOML
using ...Types.CleanMastConfig: ProjectConfig, MastConfig
using ...CleanMastConfig: parse_config
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ...CleanMastRules.Process: apply_rules!

export execute, process_clean_data!

"""
Process clean data by applying cleaning rules to the time series data.
    
Parameters
----------
config : CleanMastConfig
    Configuration containing cleaning rules
time_series : TimeSeriesData
    Time series data to be processed

Returns
-------
TimeSeriesData
    Processed time series data with violations set to missing
"""
function process_clean_data!(config::MastConfig, time_series::TimeSeriesData)::TimeSeriesData
    # Apply all cleaning rules
    violations = apply_rules!(config.rules, time_series)
    
    # Return the processed time series
    return time_series
end

function execute(dir::String)
    config = parse_config(dir)
    
    # Construct paths using the logical name
    name = config.mast.name
    raw_filename = "raw/$(name).csv"
    raw_filepath = joinpath(dir, raw_filename)
    
    if !isfile(raw_filepath)
        error("Raw data file not found: $raw_filepath. Please run 'project parse-sensors' first.")
    end
    
    # Read sensors from the new TOML format
    sensors_filepath = joinpath(dir, "raw/$(name).sensors.toml")
    if !isfile(sensors_filepath)
        error("Raw sensors file not found: $sensors_filepath. Please run 'project parse-sensors' first.")
    end
    
    sensors_dict = load_dict(sensors_filepath)
    
    # Convert TOML sensors to SensorColumn objects
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_dict["sensors"]]

    # Read raw data and sensors
    df = CSV.read(
        raw_filepath, 
        DataFrame;
        types=Dict(
            :timestamp => DateTime,  # Ensure timestamp is read as DateTime
            # All other columns should allow for missing values
            [col => Union{Float64, Missing} for col in map(s -> s.columnName, sensors) if col != :timestamp]...
        )
    )
    
    
    time_series = TimeSeriesData(df, sensors)
    
    # Process clean data
    println("Processing clean data...")
    result = process_clean_data!(config.mast, time_series)
    
    # Save processed data
    output_filename = "clean/$(name).csv"
    output_dir = dirname(joinpath(dir, output_filename))
    mkpath(output_dir)
    CSV.write(joinpath(dir, output_filename), result.df)
    
    # Save updated sensors to YAML in the same directory
    sensors_output_path = joinpath(dir, "clean/$(name).sensors.yaml")
    sensors_yaml = Dict(
        "sensors" => [to_dict(s) for s in result.sensors]
    )
    open(sensors_output_path, "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("Clean data processing completed:")
    println("- Saved processed data to $(output_filename)")
    println("- Saved updated sensors to $(sensors_output_path)")
end

end 