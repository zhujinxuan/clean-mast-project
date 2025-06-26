module RepresentativeYearCalibration

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using ...RepresentativeYear: calibrate_to_representative_year
using ..TrainMesoModel: load_model

export execute

function execute(dir::String)
    config = parse_config(dir)
    
    # Read reconstructed mast data from reconstruct_meso
    mast_name = config.mast.name
    reconstructed_filename = "reconstruct_meso/$(mast_name).csv"
    reconstructed_filepath = joinpath(dir, reconstructed_filename)
    
    if !isfile(reconstructed_filepath)
        error("Reconstructed mast data file not found: $reconstructed_filepath")
    end
    
    # Read sensors from YAML
    sensors_filepath = joinpath(dir, "reconstruct_meso/$(mast_name).sensors.yaml")
    if !isfile(sensors_filepath)
        error("Reconstructed mast sensors file not found: $sensors_filepath")
    end
    
    # Read mast data and sensors
    mast_df = CSV.read(reconstructed_filepath, DataFrame)
    sensors_dict = load_dict(sensors_filepath)
    mast_sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_dict["sensors"]]
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    
    # Read meso data from raw files
    meso_name = config.meso.name
    meso_filepath = joinpath(dir, "raw/$(meso_name).csv")
    if !isfile(meso_filepath)
        error("Raw meso data file not found: $meso_filepath. Please run 'project parse-sensors' first.")
    end
    
    # Read meso sensors from raw TOML file
    meso_sensors_filepath = joinpath(dir, "raw/$(meso_name).sensors.toml")
    if !isfile(meso_sensors_filepath)
        error("Raw meso sensors file not found: $meso_sensors_filepath. Please run 'project parse-sensors' first.")
    end
    
    # Read meso data and sensors
    meso_df = CSV.read(meso_filepath, DataFrame)
    meso_sensors_dict = load_dict(meso_sensors_filepath)
    meso_sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in meso_sensors_dict["sensors"]]
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
    output_filename = "rep_year_calibration/$(mast_name).csv"
    mkpath(dirname(joinpath(dir, output_filename)))
    CSV.write(joinpath(dir, output_filename), result.df)
    
    # Save updated sensors to YAML
    sensors_output_path = "rep_year_calibration/$(mast_name).sensors.yaml"
    sensors_yaml = Dict(
        "sensors" => map(to_dict, result.sensors)
    )
    open(joinpath(dir, sensors_output_path), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("\nRepresentative year calibration completed:")
    println("- Saved calibrated data to $(output_filename)")
    println("- Saved updated sensors to $(sensors_output_path)")
end

end 