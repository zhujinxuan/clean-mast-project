module RepresentativeYearCalibration

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using ...RepresentativeYear: calibrate_to_representative_year
using ..TrainMesoModel: load_model

export execute

function execute(dir::String)
    config = parse_config(dir)
    
    # Read reconstructed mast data from reconstruct_meso
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
    
    # Read meso data from raw files
    meso_filename = "raw.$(config.meso.data_path).csv"
    meso_filepath = joinpath(dir, meso_filename)
    if !isfile(meso_filepath)
        error("Raw meso data file not found: $meso_filepath. Please run process-sensors first.")
    end
    
    # Read meso sensors from raw.{data_path}.sensors.yaml
    meso_sensors_filepath = joinpath(dir, "raw.$(config.meso.data_path).sensors.yaml")
    if !isfile(meso_sensors_filepath)
        error("Raw meso sensors file not found: $meso_sensors_filepath. Please run process-sensors first.")
    end
    
    # Read meso data and sensors
    meso_df = CSV.read(meso_filepath, DataFrame)
    meso_sensors_yaml = YAML.load_file(meso_sensors_filepath)
    meso_sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in meso_sensors_yaml["sensors"]]
    meso_ts = TimeSeriesData(meso_df, meso_sensors)
    
    # Load 16-sector wind speed model
    println("Loading 16-sector model...")
    model_16sector = load_model(dir, SectorizedRegressionModel, "16-sector", "meso", "era5")
    
    # Get training time range from config
    time_range = TimeRange(
        config.analysis.time_range.min isa Nothing ? minimum(mast_df.timestamp) : config.analysis.time_range.min,
        config.analysis.time_range.max isa Nothing ? maximum(mast_df.timestamp) : config.analysis.time_range.max
    )
    
    # Perform calibration
    println("Performing representative year calibration for wind speed...")
    result, _ = calibrate_to_representative_year(mast_ts, meso_ts, time_range, model_16sector)
    
    # Save calibrated data
    output_filename = "rep_year_calibration.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), result.df)
    
    # Save updated sensors to YAML
    sensors_yaml = Dict(
        "sensors" => map(to_dict, result.sensors)
    )
    open(joinpath(dir, "rep_year_calibration-sensors.yaml"), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("\nRepresentative year calibration completed:")
    println("- Saved calibrated data to $(output_filename)")
    println("- Saved updated sensors to rep_year_calibration-sensors.yaml")
end

end 