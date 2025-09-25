module CommandTrainMeso

using DataFrames
using CSV
using TOML
using JLD2

using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoModel
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, SensorColumn
using ...Types.MastReferenceModel: AbstractMastReferenceModel, AbstractSpeedReferenceModel, AbstractDirectionReferenceModel, getModelName
using ...Types.Utils: from_dict,to_dict
using ...CleanMastUtils: load_dict
using ..Core: train_meso_windspeed_sectorized, train_meso_winddirection_directionoffset
using ..Core: prepare_training_data
using Statistics: cor, mean
using ...Types.TrainMesoResultsTypes: TrainMesoResults, TrainMesoPairResult, TrainMesoEntity, TrainMesoSpeedMetrics



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
    compute_train_meso_metrics(config, mast_data, meso_data, model_groups) :: TrainMesoResults

Compute training metrics (currently windspeed 1-sector correlation only) per mast×meso pair
and return a TrainMesoResults structure suitable for writing to TOML.
"""
function compute_train_meso_metrics(
    config::TrainMesoConfiguration,
    mast_data::Dict{String, TimeSeriesData},
    meso_data::Dict{String, TimeSeriesData},
    model_groups
)::TrainMesoResults
    pairs = TrainMesoPairResult[]
    # Entities for output
    mast_entities = Dict(m.name => TrainMesoEntity(m.name, m.input) for m in config.masts)
    meso_entities = Dict(m.name => TrainMesoEntity(m.name, m.input) for m in config.mesos)

    for ((mast_name, meso_name), models) in model_groups
        mast_ts = mast_data[mast_name]
        meso_ts = meso_data[meso_name]
        mast_aligned, meso_aligned = prepare_training_data(mast_ts, meso_ts)

        # Select highest-height avg WindSpeed sensors
        mast_ws = filter(s -> s.statType == "avg" && s.sensorType == "WindSpeed" && s.height <= 160.0, mast_aligned.sensors)
        meso_ws = filter(s -> s.statType == "avg" && s.sensorType == "WindSpeed", meso_aligned.sensors)
        isempty(mast_ws) && error("No wind speed sensors in mast $(mast_name)")
        isempty(meso_ws) && error("No wind speed sensors in meso $(meso_name)")
        mast_high = argmax(s -> s.height, mast_ws)
        meso_high = argmax(s -> s.height, meso_ws)
        mast_vec = mast_aligned.df[!, mast_high.columnName]
        meso_vec = meso_aligned.df[!, meso_high.columnName]
        mask = .!(ismissing.(mast_vec) .| ismissing.(meso_vec))
        if count(mask) == 0
            error("No overlapping non-missing windspeed samples for $(mast_name) × $(meso_name)")
        end
        m = collect(skipmissing(mast_vec[mask]))
        e = collect(skipmissing(meso_vec[mask]))

        corr = cor(m, e)

        # Record metrics only if 1-sector method is present for this pair
        has_1sector = any(model -> model.method == "1-sector", models)
        model_metrics = TrainMesoSpeedMetrics[]
        if has_1sector
            push!(model_metrics, TrainMesoSpeedMetrics("1-sector", corr))
        end

        push!(pairs, TrainMesoPairResult(mast_entities[mast_name], meso_entities[meso_name], model_metrics))
    end

    return TrainMesoResults(pairs)
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

    # Group models by mast-meso pair for efficient processing (typed, functional style)
    keys = unique((m.mast_name, m.meso_name) for m in config.models)
    model_groups = Dict{Tuple{String,String}, Vector{TrainMesoModel}}(
        k => [m for m in config.models if (m.mast_name, m.meso_name) == k] for k in keys
    )

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
    # Compute and write training results metrics (1-sector only for now)
    println("\nComputing training metrics and writing results...")
    results = compute_train_meso_metrics(config, mast_data, meso_data, model_groups)
    results_path = joinpath(project_dir, "meso-models", "train-meso-results.toml")
    mkpath(dirname(results_path))
    open(results_path, "w") do io
        TOML.print(io, to_dict(results))
    end
    println("Saved training metrics to: $(results_path)")

    println("\nMesoscale model training completed successfully.")
    println("Trained $(length(config.models)) model(s) total.")
end

end # module