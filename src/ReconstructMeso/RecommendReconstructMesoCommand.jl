module RecommendReconstructMesoCommand

using TOML
using Dates
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoSource
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.ReconstructCrossConfig: ReconstructCrossConfiguration, ReconstructCrossSettings
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration, ReconstructMesoMast, ReconstructMesoModels, ReconstructMesoModelSpec
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ...TimeSeriesProcessing.MeasurementPeriodCalculator: calculate_optimal_measurement_period
using ...Types.TrainMesoResultsTypes: TrainMesoResults


export execute


# Overload: select model using results (if provided) and return meso input as well
function select_reconstruct_model(
    train_config::TrainMesoConfiguration,
    mast_name::String,
    meso_by_name::Dict{String, TimeSeriesSource},
    results::TrainMesoResults
)
    # Choose best meso by highest 1-sector correlation for this mast
    mast_pairs = filter(p -> p.mast.name == mast_name, results.pairs)
    if isempty(mast_pairs)
        error("No training results found for mast $(mast_name) in train-meso-results.toml")
    end

    best_pair = nothing
    best_score = -Inf
    for p in mast_pairs
        ms = filter(m -> m.method == "1-sector", p.models)
        if !isempty(ms)
            score = ms[1].correlation
            if score > best_score
                best_score = score
                best_pair = p
            end
        end
    end
    if best_pair === nothing
        error("No '1-sector' metrics found for mast $(mast_name) in train-meso-results.toml")
    end

    # Pick models in train_config matching this mast and the chosen meso
    candidates = filter(m -> m.mast_name == mast_name && m.meso_name == best_pair.meso.name, train_config.models)
    if isempty(candidates)
        error("No trained models found for mast $(mast_name) and meso $(best_pair.meso.name) in train-meso.toml")
    end
    ws_matches = filter(m -> m.method == "1-sector", candidates)
    wd_matches = filter(m -> m.method == "constant-offset", candidates)
    if isempty(ws_matches) || isempty(wd_matches)
        error("Required models missing for mast $(mast_name) and meso $(best_pair.meso.name): need '1-sector' and 'constant-offset'")
    end
    ws = first(ws_matches)
    wd = first(wd_matches)
    ws_spec = ReconstructMesoModelSpec("1-sector", ws.meso_name, ws.output)
    wd_spec = ReconstructMesoModelSpec("constant-offset", wd.meso_name, wd.output)
    models = ReconstructMesoModels(ws_spec, wd_spec)

    # Resolve meso source by the windspeed model's meso (warn if mismatch)
    if ws.meso_name != wd.meso_name
        @warn "Windspeed and winddirection models use different meso sources ($(ws.meso_name) vs $(wd.meso_name)). Using windspeed's meso for period calculation."
    end
    meso_source = get(meso_by_name, ws.meso_name, nothing)
    meso_source === nothing && error("Meso source '$(ws.meso_name)' not found in train-meso configuration")
    return models, meso_source
end


"""
    load_required_configurations(dir::String)

Load all required configuration files and return structured data.

# Returns
- Tuple of (train_config, single_outputs_by_mast, use_cross_mast_data, cross_outputs_by_mast, available_masts)
"""
function load_required_configurations(dir::String)::Tuple{TrainMesoConfiguration, Dict{String, TimeSeriesSource}, Bool, Dict{String, TimeSeriesSource}, Vector{String}}
    # Load train-meso.toml
    train_meso_path = joinpath(dir, "train-meso.toml")
    if !isfile(train_meso_path)
        error("train-meso.toml not found. Please run 'recommend train-meso' first.")
    end
    config_dict = load_dict(train_meso_path)
    train_config = from_dict(TrainMesoConfiguration, config_dict)

    # Load reconstruct-single.toml
    reconstruct_single_path = joinpath(dir, "reconstruct-single.toml")
    if !isfile(reconstruct_single_path)
        error("reconstruct-single.toml not found. Please run 'recommend reconstruct-single' first.")
    end
    reconstruct_single_dict = load_dict(reconstruct_single_path)
    reconstruct_single_config = from_dict(ReconstructSingleConfiguration, reconstruct_single_dict)
    single_outputs_by_mast = Dict(mast.name => mast.output for mast in reconstruct_single_config.masts)

    # Check for cross-mast configuration (multi-mast vs single-mast project)
    cross_config_path = joinpath(dir, "reconstruct-cross.toml")
    use_cross_mast_data = isfile(cross_config_path)

    cross_outputs_by_mast = Dict{String, TimeSeriesSource}()
    available_masts = String[]

    if use_cross_mast_data
        cross_config_dict = load_dict(cross_config_path)
        cross_config = from_dict(ReconstructCrossConfiguration, cross_config_dict)
        cross_outputs_by_mast = Dict(mast.name => mast.output for mast in cross_config.masts)
        available_masts = collect(keys(cross_outputs_by_mast))
        println("📊 Multi-mast project detected: Using cross-mast reconstructed data from $(length(available_masts)) masts")
    else
        available_masts = collect(keys(single_outputs_by_mast))
        println("📊 Single mast project detected: Using reconstruct-single data directly from $(length(available_masts)) masts")
    end

    return train_config, single_outputs_by_mast, use_cross_mast_data, cross_outputs_by_mast, available_masts
end

"""
    load_training_results(dir::String)

Load meso training results. Fails fast if not available.

# Returns
- TrainMesoResults
"""
function load_training_results(dir::String)::TrainMesoResults
    results_path = joinpath(dir, "meso-models", "train-meso-results.toml")
    if !isfile(results_path)
        error("train-meso-results.toml not found at: $results_path. Please run meso training first.")
    end
    results_dict = load_dict(results_path)
    return from_dict(TrainMesoResults, results_dict)
end

"""
    determine_input_source(mast_name::String, use_cross_mast_data::Bool,
                          single_outputs_by_mast::Dict, cross_outputs_by_mast::Dict)

Determine the input data source for meso reconstruction (cross-mast or single-mast).

# Returns
- TimeSeriesSource for the input data
"""
function determine_input_source(mast_name::String, use_cross_mast_data::Bool,
                               single_outputs_by_mast::Dict{String, TimeSeriesSource},
                               cross_outputs_by_mast::Dict{String, TimeSeriesSource})::TimeSeriesSource
    if use_cross_mast_data
        cross_source = get(cross_outputs_by_mast, mast_name, nothing)
        if cross_source === nothing
            error("No reconstruct-cross output configured for $(mast_name). Ensure this mast exists in reconstruct-cross.toml with an output path.")
        end
        return cross_source
    else
        single_source = get(single_outputs_by_mast, mast_name, nothing)
        if single_source === nothing
            error("No reconstruct-single output configured for $(mast_name). Please generate reconstruct-single first.")
        end
        return single_source
    end
end

"""
    create_mast_configuration(mast_name::String, train_config::TrainMesoConfiguration,
                             meso_by_name::Dict{String, TimeSeriesSource},
                             results::TrainMesoResults,
                             single_outputs_by_mast::Dict{String, TimeSeriesSource},
                             use_cross_mast_data::Bool, cross_outputs_by_mast::Dict{String, TimeSeriesSource},
                             dir::String)

Create a single mast configuration for meso reconstruction.

# Returns
- ReconstructMesoMast configuration
"""
function create_mast_configuration(mast_name::String, train_config::TrainMesoConfiguration,
                                  meso_by_name::Dict{String, TimeSeriesSource},
                                  results::TrainMesoResults,
                                  single_outputs_by_mast::Dict{String, TimeSeriesSource},
                                  use_cross_mast_data::Bool, cross_outputs_by_mast::Dict{String, TimeSeriesSource},
                                  dir::String)::ReconstructMesoMast
    # Choose reconstruct model and meso input using helper (results-driven if available)
    reconstruct_model, meso_source = select_reconstruct_model(train_config, mast_name, meso_by_name, results)

    # Get single-mast source for period calculation
    single_source = get(single_outputs_by_mast, mast_name, nothing)
    if single_source === nothing
        error("No reconstruct-single output configured for $(mast_name). Please generate reconstruct-single first.")
    end
    reconstruct_single_ts = load_timeseries(single_source, dir)

    # Determine input data source
    input_source = determine_input_source(mast_name, use_cross_mast_data, single_outputs_by_mast, cross_outputs_by_mast)
    input_reconstruction_ts = load_timeseries(input_source, dir)

    # Load meso dataset
    meso_data = load_timeseries(meso_source, dir)

    # Calculate optimal measurement period
    optimal_time_range = calculate_optimal_measurement_period(
        reconstruct_single_ts,
        input_reconstruction_ts,
        meso_data
    )

    return ReconstructMesoMast(
        mast_name,
        input_source,
        TimeSeriesSource(
            joinpath("./reconstruct-meso", "$(mast_name).csv"),
            joinpath("./reconstruct-meso", "$(mast_name).sensors.yaml")
        ),
        optimal_time_range,
        reconstruct_model,
    )
end

"""
    execute(dir::String)

Generate reconstruct-meso.toml configuration based on train-meso.toml.

# Arguments
- `dir::String`: Project directory containing train-meso.toml
"""
function execute(dir::String)::Nothing
    # Load all required configurations
    train_config, single_outputs_by_mast, use_cross_mast_data, cross_outputs_by_mast, available_masts =
        load_required_configurations(dir)

    # Load training results
    results = load_training_results(dir)

    # Build meso sources lookup
    meso_by_name = Dict(m.name => m.input for m in train_config.mesos)
    if isempty(meso_by_name)
        error("No mesoscale data sources found in train-meso configuration")
    end

    # Create mast configurations
    masts = map(available_masts) do mast_name
        create_mast_configuration(mast_name, train_config, meso_by_name, results,
                                 single_outputs_by_mast, use_cross_mast_data, cross_outputs_by_mast, dir)
    end

    # Create and save output configuration
    output_config = ReconstructMesoConfiguration(
        filter(x -> !isnothing(x), masts),
        train_config.mesos
    )

    output_path = joinpath(dir, "reconstruct-meso.toml")
    open(output_path, "w") do io
        println(io, "# Mesoscale Reconstruction Configuration")
        println(io, "# Uses trained models to fill remaining gaps with mesoscale data")
        println(io)
        TOML.print(io, to_dict(output_config))
    end

    # Print summary
    println("Generated reconstruct-meso.toml at: $output_path")
    println("Found $(length(masts)) mast configuration(s) for reconstruction")
    if use_cross_mast_data
        println("📊 Using cross-mast reconstructed data as input for mesoscale reconstruction")
    else
        println("📊 Using single-mast reconstructed data as input for mesoscale reconstruction (cross-mast step skipped)")
    end
end

end # module