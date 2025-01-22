module RepresentativeYearCalibration

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData
using ...RepresentativeYear: calibrate_to_representative_year
using ...Types.ReconstructMeso: TrainingTimeRange
using ...MastTimeSeries: read_meso_data
using ...Types.Utils: from_dict, to_dict

export execute

function execute(dir::String)
    config = parse_config(dir)
    
    # Read reconstructed mast data file
    original_filename = config.mast.data_path
    reconstructed_filename = "reconstruct_meso.$(original_filename).csv"
    reconstructed_filepath = joinpath(dir, reconstructed_filename)
    
    if !isfile(reconstructed_filepath)
        error("Reconstructed mast data file not found: $reconstructed_filepath")
    end
    
    # Read sensors from reconstruct_meso-sensors.yaml
    sensors_filepath = joinpath(dir, "reconstruct_meso-sensors.yaml")
    if !isfile(sensors_filepath)
        error("Reconstructed mast sensors file not found: $sensors_filepath")
    end
    
    # Read mast data and sensors
    mast_df = CSV.read(reconstructed_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    mast_sensors = map(s -> from_dict(SensorColumn, Dict{String,Any}(String(k) => v for (k,v) in s)), 
                      sensors_yaml["sensors"])
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    
    # Read meso data
    meso_ts = read_meso_data(config, dir)
    
    # Get training time range from config
    time_range = TrainingTimeRange(
        config.analysis.time_range.min isa Nothing ? minimum(mast_df.timestamp) : config.analysis.time_range.min,
        config.analysis.time_range.max isa Nothing ? maximum(mast_df.timestamp) : config.analysis.time_range.max
    )
    
    # Get target height from config or use default
    target_height = something(config.analysis.target_height, 120.0)
    
    # Perform calibration
    println("Performing representative year calibration for $(target_height)m wind speed...")
    calibrated_ts = calibrate_to_representative_year(
        mast_ts, 
        meso_ts, 
        time_range;
        target_height=target_height
    )
    
    # Save calibrated data
    output_filename = "rep_year_calibration.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), calibrated_ts.df)
    
    # Save sensors to YAML (they remain unchanged)
    sensors_yaml = Dict(
        "sensors" => [
            to_dict(s) for s in calibrated_ts.sensors
        ]
    )
    
    open(joinpath(dir, "rep_year_calibration-sensors.yaml"), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("Representative year calibration completed:")
    println("- Saved calibrated data to $(output_filename)")
    println("- Saved sensors to rep_year_calibration-sensors.yaml")
end

end 