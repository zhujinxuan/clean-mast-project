module CommandTrainMeso

using DataFrames
using CSV
using TOML
using JLD2
using Base.Threads: @threads
using Logging

using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoModel
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, SensorColumn
using ...Types.MastReferenceModel: AbstractMastReferenceModel, AbstractSpeedReferenceModel, AbstractDirectionReferenceModel, getModelName
using ...Types.Utils: from_dict,to_dict
using ...CleanMastUtils: load_dict
using ..Core: train_meso_windspeed_sectorized, train_meso_winddirection_directionoffset
using ..Core: prepare_training_data
using Statistics: cor, mean
using ...Types.TrainMesoResultsTypes: TrainMesoResults, TrainMesoPairResult, TrainMesoEntity, TrainMesoSpeedMetrics

using ...CleanMastLogging: create_cleanmast_logger, WorkerLoggerManager, get_logger
using ...CleanMastLogging.CleanMastLogger.LogRotation: archive_all_worker_logs



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
    train_mast_meso_pair(mast_name::String, meso_name::String,
                        models::Vector{TrainMesoModel},
                        mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                        project_dir::String)

Train all models for a single mast-meso pair.

# Returns
- Vector of (model_config, trained_model) tuples
"""
function train_mast_meso_pair(mast_name::String, meso_name::String,
                              models::Vector{TrainMesoModel},
                              mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                              project_dir::String)
    @info "Training models" mast=mast_name meso=meso_name num_models=length(models)

    results = Tuple{TrainMesoModel, AbstractMastReferenceModel}[]

    for model_config in models
        @info "Training model" method=model_config.method

        trained_model = if model_config.method == "16-sector"
            train_meso_windspeed_sectorized(mast_ts, meso_ts, "16-sector")
        elseif model_config.method == "1-sector"
            train_meso_windspeed_sectorized(mast_ts, meso_ts, "1-sector")
        elseif model_config.method == "constant-offset"
            train_meso_winddirection_directionoffset(mast_ts, meso_ts)
        else
            @warn "Unknown method" method=model_config.method
            continue
        end

        output_path = joinpath(project_dir, model_config.output)
        mkpath(dirname(output_path))
        @save output_path model=trained_model
        @info "Saved model" output=model_config.output

        push!(results, (model_config, trained_model))
    end

    return results
end

"""
    execute(config_path::String)

Execute mesoscale model training based on configuration file.

# Arguments
- `config_path::String`: Path to train-meso.toml configuration file
"""
function execute(config_path::String)
    # Setup logging
    config_dir = dirname(config_path)
    config_basename = splitext(basename(config_path))[1]

    main_logger = create_cleanmast_logger(
        job_name="train-meso",
        worker_id=1,
        config_dir=config_dir,
        config_basename=config_basename
    )
    global_logger(main_logger)

    @info "Starting mesoscale model training" config_file=config_path

    # Load configuration
    config_dict = load_dict(config_path)
    config = from_dict(TrainMesoConfiguration, config_dict)
    project_dir = dirname(config_path)

    # Load all mast data into a dictionary
    @info "Loading mast data"
    mast_data = Dict(
        mast_config.name => load_timeseries(mast_config.input, project_dir)
        for mast_config in config.masts
    )
    @info "Loaded mast data sources" count=length(mast_data)

    # Load all meso data into a dictionary
    @info "Loading meso data"
    meso_data = Dict(
        meso_config.name => load_timeseries(meso_config.input, project_dir)
        for meso_config in config.mesos
    )
    @info "Loaded meso data sources" count=length(meso_data)

    # Group models by mast-meso pair for efficient processing
    keys = unique((m.mast_name, m.meso_name) for m in config.models)
    model_groups = Dict{Tuple{String,String}, Vector{TrainMesoModel}}(
        k => [m for m in config.models if (m.mast_name, m.meso_name) == k] for k in keys
    )

    @info "Training models in parallel" num_pairs=length(model_groups) num_threads=Threads.nthreads()

    # Archive old worker logs and create worker loggers for parallel execution
    @info "Archiving old worker logs"
    archive_all_worker_logs(config_dir, config_basename, Threads.nthreads())

    @info "Creating worker logger manager" num_threads=Threads.nthreads()
    manager = WorkerLoggerManager(
        config_dir,
        config_basename
    )

    # Convert model_groups to array for parallel processing
    pair_list = collect(model_groups)
    trained_pairs = Vector{Bool}(undef, length(pair_list))

    # Train models for each mast-meso pair in parallel
    @threads for idx in eachindex(pair_list)
        worker_id = Threads.threadid()
        worker_logger = get_logger(manager, worker_id)

        with_logger(worker_logger) do
            (mast_name, meso_name), models = pair_list[idx]
            @info "Starting training" pair_index="$idx/$(length(pair_list))" mast=mast_name meso=meso_name

            try
                mast_ts = mast_data[mast_name]
                meso_ts = meso_data[meso_name]

                train_mast_meso_pair(mast_name, meso_name, models, mast_ts, meso_ts, project_dir)
                trained_pairs[idx] = true
                @info "Completed training" mast=mast_name meso=meso_name
            catch e
                @error "Training failed" mast=mast_name meso=meso_name error=e
                trained_pairs[idx] = false
            end
        end
    end

    # Check if all pairs were trained successfully
    num_successful = count(trained_pairs)
    if num_successful < length(pair_list)
        @warn "Some training jobs failed" successful=num_successful total=length(pair_list)
    end

    # Compute and write training results metrics (1-sector only for now)
    @info "Computing training metrics"
    results = compute_train_meso_metrics(config, mast_data, meso_data, model_groups)
    results_path = joinpath(project_dir, "meso-models", "train-meso-results.toml")
    mkpath(dirname(results_path))
    open(results_path, "w") do io
        TOML.print(io, to_dict(results))
    end
    @info "Saved training metrics" path=results_path

    @info "Mesoscale model training completed" total_models=length(config.models) successful_pairs=num_successful
end

end # module