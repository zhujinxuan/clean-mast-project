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
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.MastReferenceModel: getModelName, AbstractSpeedReferenceModel, AbstractDirectionReferenceModel, AbstractMastReferenceModel
using ...Types.Utils: from_dict
using ...Types.SensorColumns: SensorColumn
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using ...Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel
using ...TrainMeso: train_meso_windspeed_sectorized, train_meso_winddirection_directionoffset

export execute, load_model, save_model

"""
    generate_model_filepath(project_dir::String, 
                      model_type::Type{T},
                      modelName::String,
                      source_type::String, 
                      source_id::String,
                      extension::String) where T <: AbstractMastReferenceModel

Generate the full path for a model file.

# Arguments
- `project_dir::String`: The project directory containing models
- `model_type`: Type of model (SectorizedRegressionModel or DirectionOffsetModel)
- `modelName`: Name of the model (e.g., "16-sector" or "1-sector")
- `source_type`: Type of source data (e.g., "meso")
- `source_id`: Identifier for the source (e.g., "era5")
- `extension`: File extension (e.g., "jld2" or "csv")

# Returns
- Full path to the model file
"""
function generate_model_filepath(project_dir::String,
                          model_type::Type{T},
                          modelName::String,
                          source_type::String, 
                          source_id::String,
                          extension::String)::String where T <: AbstractMastReferenceModel
    # Determine base directory based on model type
    base_dir = begin 
        if model_type <: AbstractSpeedReferenceModel
          joinpath(project_dir, "models/windspeed")
        elseif model_type <: AbstractDirectionReferenceModel
          joinpath(project_dir, "models/winddirection")
        else
          error("Unsupported model type: $(model_type)")
        end
    end
    
    # Get model directory
    model_dir = joinpath(base_dir, modelName)
    
    # Generate filename
    base_filename = "_$(source_type)_$(source_id)"
    return joinpath(model_dir, "$(base_filename).$(extension)")
end

"""
    load_model(project_dir::String, 
              model_type::Type{T},
              modelName::String,
              source_type::String, 
              source_id::String) where T <: AbstractDirectionReferenceModel

Load a trained model from JLD2 file.

# Arguments
- `project_dir::String`: The project directory containing models
- `model_type`: Type of model to load (SectorizedRegressionModel or DirectionOffsetModel)
- `modelName`: Name of the model (e.g., "16-sector" or "1-sector")
- `source_type`: Type of source data (e.g., "meso")
- `source_id`: Identifier for the source (e.g., "era5")

# Returns
- The loaded model
"""
function load_model(project_dir::String,
                   model_type::Type{T},
                   modelName::String,
                   source_type::String, 
                   source_id::String) :: T where T <: AbstractMastReferenceModel
    jld2_path = generate_model_filepath(project_dir, model_type, modelName, source_type, source_id, "jld2")
    
    if !isfile(jld2_path)
        error("Model file not found: $jld2_path")
    end
    
    # Load model from JLD2
    @load jld2_path model
    return model
end

"""
    save_model(project_dir::String, 
              model::T, 
              source_type::String, 
              source_id::String) where T <: AbstractMastReferenceModel

Save a trained model to both JLD2 and CSV formats following the specified directory structure.

# Arguments
- `project_dir::String`: The project directory to save models in
- `model`: The trained model to save
- `source_type`: Type of source data (e.g., "meso")
- `source_id`: Identifier for the source (e.g., "era5")
"""
function save_model(project_dir::String,
                   model::T,
                   source_type::String, 
                   source_id::String) where T <: AbstractMastReferenceModel
    # Create directory structure if it doesn't exist
    jld2_path = generate_model_filepath(project_dir, typeof(model), getModelName(model), source_type, source_id, "jld2")
    mkpath(dirname(jld2_path))
    
    # Save JLD2 file
    @save jld2_path model
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
    
    # Train models
    println("\nTraining mesoscale reference models...")
    
    # Train 16-sector wind speed model
    println("Training 16-sector wind speed model...")
    model_16sector = train_meso_windspeed_sectorized(mast_ts, meso_ts, "16-sector")
    save_model(dir, model_16sector, "meso", "era5")
    
    # Train 1-sector wind speed model
    println("Training 1-sector wind speed model...")
    model_1sector = train_meso_windspeed_sectorized(mast_ts, meso_ts, "1-sector")
    save_model(dir, model_1sector, "meso", "era5")
    
    # Train direction offset model
    println("Training direction offset model...")
    model_direction = train_meso_winddirection_directionoffset(mast_ts, meso_ts)
    save_model(dir, model_direction, "meso", "era5")
    
    println("\nModel training completed:")
    println("- Saved models under models/windspeed/16-sectors/")
    println("- Saved models under models/windspeed/1-sector/")
    println("- Saved models under models/winddirection/constant-offset/")
end

end # module 