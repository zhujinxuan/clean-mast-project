module CleanData

using CSV, YAML, DataFrames, Dates
using ...Types.CleanMastConfig: ProjectConfig, MastConfig
using ...CleanMastConfig: parse_config
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData
using ...Types.Utils: from_dict, to_dict
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
    
    # Read raw data file
    original_filename = config.mast.data_path
    raw_filename = "raw.$(original_filename).csv"
    raw_filepath = joinpath(dir, raw_filename)
    
    if !isfile(raw_filepath)
        error("Raw data file not found: $raw_filepath. Please run process-sensors first.")
    end
    
    # Read sensors from raw.{data_path}.sensors.yaml
    sensors_filepath = joinpath(dir, "raw.$(original_filename).sensors.yaml")
    if !isfile(sensors_filepath)
        error("Raw sensors file not found: $sensors_filepath. Please run process-sensors first.")
    end
    

    sensors_yaml = YAML.load_file(sensors_filepath)
    
    # Convert YAML sensors to SensorColumn objects
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_yaml["sensors"]]

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
    output_filename = "clean_data.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), result.df)
    
    # Save updated sensors to YAML
    sensors_yaml = Dict(
        "sensors" => [to_dict(s) for s in result.sensors]
    )
    
    open(joinpath(dir, "sensors.yaml"), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("Clean data processing completed:")
    println("- Saved processed data to $(output_filename)")
    println("- Saved updated sensors to sensors.yaml")
end

end 