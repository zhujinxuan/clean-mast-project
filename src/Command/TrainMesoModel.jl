"""
    TrainMesoModel.jl

Command module for training mesoscale reference models for wind speed and direction.
Implements training for:
- 16-sector wind speed model
- 1-sector wind speed model
- Constant direction offset model
"""
module TrainMesoModel

using DataFrames
using Dates
using JLD2
using CSV
using YAML

using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.MastReferenceModel: getModelName
using ...Types.Utils: from_dict, show_as_dataframe
using ...TrainMeso: train_meso_windspeed_sectorized, train_meso_winddirection_directionoffset
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using ...Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel
using ...MastTimeSeries: read_meso_data

export execute

"""
    save_model(project_dir::String, 
              model::Union{SectorizedRegressionModel, DirectionOffsetModel}, 
              mast_id::String, 
              source_type::String, 
              source_id::String)

Save a trained model to both JLD2 and CSV formats following the specified directory structure.

# Arguments
- `project_dir::String`: The project directory to save models in
- `model`: The trained model to save
- `mast_id`: Identifier for the target mast
- `source_type`: Type of source data (e.g., "meso")
- `source_id`: Identifier for the source (e.g., "era5")
"""
function save_model(project_dir::String,
                   model::Union{SectorizedRegressionModel, DirectionOffsetModel}, 
                   mast_id::String, 
                   source_type::String, 
                   source_id::String)
    # Determine base directory based on model type
    base_dir = if model isa SectorizedRegressionModel
        joinpath(project_dir, "models/windspeed")
    else
        joinpath(project_dir, "models/winddirection")
    end
    
    # Create directory structure if it doesn't exist
    model_dir = joinpath(base_dir, getModelName(model))
    mkpath(model_dir)
    
    # Generate base filename
    base_filename = "$(mast_id)_$(source_type)_$(source_id)"
    
    # Save JLD2 file
    jld2_path = joinpath(model_dir, "$(base_filename).jld2")
    @save jld2_path model
    
    # Save CSV summary
    csv_path = joinpath(model_dir, "$(base_filename).csv")
    summary_data = show_as_dataframe(model)
    describe(summary_data)
    
    CSV.write(csv_path, summary_data)
end

"""
    execute(dir::String)

Execute the train meso model command.
"""
function execute(dir::String)
    # Parse config
    config = parse_config(dir)
    
    # Read reconstructed mast data
    original_filename = config.mast.data_path
    reconstructed_filename = "reconstruct_single_mast.$(original_filename).csv"
    reconstructed_filepath = joinpath(dir, reconstructed_filename)
    
    if !isfile(reconstructed_filepath)
        error("Reconstructed mast data file not found: $reconstructed_filepath")
    end
    
    # Read sensors from reconstruct_single_mast-sensors.yaml
    sensors_filepath = joinpath(dir, "reconstruct_single_mast-sensors.yaml")
    if !isfile(sensors_filepath)
        error("Reconstructed mast sensors file not found: $sensors_filepath")
    end
    
    # Read mast data and sensors
    mast_df = CSV.read(reconstructed_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    mast_sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_yaml["sensors"]]
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    
    # Read meso data using config
    meso_filepath = joinpath(dir, config.meso.data_path)
    if !isfile(meso_filepath)
        error("Meso data file not found: $meso_filepath")
    end
    
    meso_ts = read_meso_data(config, dir)
    
    
    # Extract mast ID from config or use default
    mast_id = basename(dir)
    
    # Train models
    println("\nTraining mesoscale reference models...")
    
    # Train 16-sector wind speed model
    println("Training 16-sector wind speed model...")
    model_16sector = train_meso_windspeed_sectorized(mast_ts, meso_ts, "16-sector")
    save_model(dir, model_16sector, mast_id, "meso", "era5")
    
    # Train 1-sector wind speed model
    println("Training 1-sector wind speed model...")
    model_1sector = train_meso_windspeed_sectorized(mast_ts, meso_ts, "1-sector")
    save_model(dir,model_1sector, mast_id, "meso", "era5")
    
    # Train direction offset model
    println("Training direction offset model...")
    model_direction = train_meso_winddirection_directionoffset(mast_ts, meso_ts)
    save_model(dir, model_direction, mast_id, "meso", "era5")
    
    println("\nModel training completed:")
    println("- Saved models under models/windspeed/16-sectors/")
    println("- Saved models under models/windspeed/1-sector/")
    println("- Saved models under models/winddirection/constant-offset/")
end

end # module 