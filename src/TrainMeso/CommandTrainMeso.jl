module CommandTrainMeso

using DataFrames
using CSV
using TOML
using JLD2

using ...Types.TrainMesoConfig: TrainMesoConfiguration
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries
using ...Types.MastReferenceModel: AbstractMastReferenceModel, AbstractSpeedReferenceModel, AbstractDirectionReferenceModel, getModelName
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ..Core: train_meso_windspeed_sectorized, train_meso_winddirection_directionoffset

export execute

"""
    generate_model_filepath(save_path::String,
                          model_type::Type{T},
                          method::String) where T <: AbstractMastReferenceModel

Generate the full path for a model file following the new structure.

# Arguments
- `save_path::String`: Base save path from config (e.g., "./meso-models/met40/era5_met40")
- `model_type`: Type of model (speed or direction)
- `method`: Model method name (e.g., "16-sector", "1-sector", "constant-offset")

# Returns
- Full path to the model file
"""
function generate_model_filepath(save_path::String,
                          model_type::Type{T},
                          method::String) where T <: AbstractMastReferenceModel
    # Determine subdirectory based on model type
    subdir = if model_type <: AbstractSpeedReferenceModel
        "windspeed"
    elseif model_type <: AbstractDirectionReferenceModel
        "winddirection"
    else
        error("Unsupported model type: $(model_type)")
    end
    
    return joinpath(save_path, subdir, "$(method).jld2")
end

"""
    save_model(save_path::String,
               model::T,
               method::String) where T <: AbstractMastReferenceModel

Save a trained model to JLD2 format.

# Arguments
- `save_path::String`: Base save path from config
- `model`: The trained model to save
- `method`: Model method name
"""
function save_model(save_path::String,
                   model::T,
                   method::String) where T <: AbstractMastReferenceModel
    # Generate full path
    jld2_path = generate_model_filepath(save_path, typeof(model), method)
    
    # Create directory structure if it doesn't exist
    mkpath(dirname(jld2_path))
    
    # Save JLD2 file
    @save jld2_path model
    println("  Saved model to: $jld2_path")
end

"""
    execute(config_path::String)

Execute mesoscale model training based on configuration file.

# Arguments
- `config_path::String`: Path to train-meso.toml configuration file
"""
function execute(config_path::String)
    println("Training mesoscale reference models...")
    
    # Load configuration
    config_dict = load_dict(config_path)
    config = from_dict(TrainMesoConfiguration, config_dict)
    project_dir = dirname(config_path)
    
    # Load all mast data into a dictionary
    mast_data = Dict(
        mast_config.name => load_timeseries(mast_config.input, project_dir)
        for mast_config in config.masts
    )
    println("Loaded $(length(mast_data)) mast data source(s)")
    
    # Load all meso data into a dictionary
    meso_data = Dict(
        meso_config.name => load_timeseries(meso_config.input, project_dir)
        for meso_config in config.mesos
    )
    println("Loaded $(length(meso_data)) meso data source(s)")
    
    # Group models by mast-meso pair for efficient processing
    model_groups = Dict{Tuple{String,String}, Vector}()
    for model in config.models
        key = (model.mast_name, model.meso_name)
        if !haskey(model_groups, key)
            model_groups[key] = []
        end
        push!(model_groups[key], model)
    end
    
    # Train models for each mast-meso pair
    for ((mast_name, meso_name), models) in model_groups
        println("\nTraining models for $mast_name with $meso_name...")
        
        # Get data
        mast_ts = mast_data[mast_name]
        meso_ts = meso_data[meso_name]
        
        # Train each model
        for model_config in models
            println("  Training $(model_config.method) model...")
            
            # Train and save based on method
            trained_model = if model_config.method == "16-sector"
                train_meso_windspeed_sectorized(mast_ts, meso_ts, "16-sector")
            elseif model_config.method == "1-sector"
                train_meso_windspeed_sectorized(mast_ts, meso_ts, "1-sector")
            elseif model_config.method == "constant-offset"
                train_meso_winddirection_directionoffset(mast_ts, meso_ts)
            else
                println("    Warning: Unknown method: $(model_config.method)")
                continue
            end
            
            # Save model
            output_path = joinpath(project_dir, model_config.output)
            mkpath(dirname(output_path))
            @save output_path model=trained_model
            println("    Saved model to: $(model_config.output)")
        end
    end
    
    println("\nMesoscale model training completed successfully.")
    println("Trained $(length(config.models)) model(s) total.")
end

end # module 