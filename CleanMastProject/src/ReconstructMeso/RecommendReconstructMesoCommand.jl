module RecommendReconstructMesoCommand

using TOML
using Dates
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoSource
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.ReconstructCrossConfig: ReconstructCrossConfiguration, ReconstructCrossSettings
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration, ReconstructMesoMast, ReconstructMesoModels, ReconstructMesoModelSpec
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesSource, TimeSeriesData, TimeRange
using ...Types.Utils: from_dict, to_dict, strip_nothing_values
using ...CleanMastUtils: load_dict
using ...TimeSeriesProcessing.MeasurementPeriodCalculator: calculate_optimal_measurement_period
using ...TimeSeriesProcessing.MastPeriodAlignment:
    calculate_pairwise_overlap,
    cluster_masts_by_overlap,
    calculate_cluster_optimal_period
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
                             dir::String;
                             override_period::Union{Nothing, TimeRange}=nothing)

Create a single mast configuration for meso reconstruction.

# Arguments
- `override_period::Union{Nothing, TimeRange}`: If provided, use this period instead of calculating

# Returns
- ReconstructMesoMast configuration
"""
function create_mast_configuration(mast_name::String, train_config::TrainMesoConfiguration,
                                  meso_by_name::Dict{String, TimeSeriesSource},
                                  results::TrainMesoResults,
                                  single_outputs_by_mast::Dict{String, TimeSeriesSource},
                                  use_cross_mast_data::Bool, cross_outputs_by_mast::Dict{String, TimeSeriesSource},
                                  dir::String;
                                  override_period::Union{Nothing, TimeRange}=nothing)::ReconstructMesoMast
    # Choose reconstruct model and meso input using helper (results-driven if available)
    reconstruct_model, meso_source = select_reconstruct_model(train_config, mast_name, meso_by_name, results)

    # Determine input data source
    input_source = determine_input_source(mast_name, use_cross_mast_data, single_outputs_by_mast, cross_outputs_by_mast)

    # Use override period if provided, otherwise calculate
    if override_period !== nothing
        optimal_time_range = override_period
    else
        # Get single-mast source for period calculation
        single_source = get(single_outputs_by_mast, mast_name, nothing)
        if single_source === nothing
            error("No reconstruct-single output configured for $(mast_name). Please generate reconstruct-single first.")
        end
        reconstruct_single_ts = load_timeseries(single_source, dir)
        input_reconstruction_ts = load_timeseries(input_source, dir)
        meso_data = load_timeseries(meso_source, dir)

        optimal_time_range = calculate_optimal_measurement_period(
            reconstruct_single_ts,
            input_reconstruction_ts,
            meso_data
        )
    end

        return ReconstructMesoMast(
        mast_name,
        input_source,
        TimeSeriesSource(
            joinpath("./reconstruct-meso", "$(mast_name).parquet"),
            nothing
        ),
        optimal_time_range,
        reconstruct_model,
    )
end

"""
    execute(dir::String; cluster_threshold::Float64=0.8, threshold_period::Int=120)

Generate reconstruct-meso.toml configuration based on train-meso.toml.

When multiple masts have overlapping data coverage (>cluster_threshold), they will be
clustered and share the same reconstruction period for consistency.

# Arguments
- `dir::String`: Project directory containing train-meso.toml

# Keyword Arguments
- `cluster_threshold::Float64`: Overlap threshold for mast clustering (default: 0.8)
- `threshold_period::Int`: Minimum intersection period in days for clustering (default: 120)
"""
function execute(
    dir::String;
    cluster_threshold::Float64=0.8,
    threshold_period::Int=120
)::Nothing
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

    # Determine periods for each mast (with clustering for multi-mast projects)
    mast_periods = calculate_mast_periods(
        available_masts,
        train_config,
        meso_by_name,
        results,
        single_outputs_by_mast,
        use_cross_mast_data,
        cross_outputs_by_mast,
        dir,
        cluster_threshold,
        threshold_period
    )

    # Create mast configurations with assigned periods
    masts = map(available_masts) do mast_name
        create_mast_configuration(
            mast_name, train_config, meso_by_name, results,
            single_outputs_by_mast, use_cross_mast_data, cross_outputs_by_mast, dir;
            override_period=mast_periods[mast_name]
        )
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
        TOML.print(io, strip_nothing_values(Dict{String, Any}(to_dict(output_config))))
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

"""
    calculate_mast_periods(...)

Calculate optimal periods for all masts, using clustering for multi-mast projects.

Single-mast projects: Each mast gets its own optimal period.
Multi-mast projects: Masts are clustered by overlap, and each cluster shares a period.
"""
function calculate_mast_periods(
    available_masts::Vector{String},
    train_config::TrainMesoConfiguration,
    meso_by_name::Dict{String, TimeSeriesSource},
    results::TrainMesoResults,
    single_outputs_by_mast::Dict{String, TimeSeriesSource},
    use_cross_mast_data::Bool,
    cross_outputs_by_mast::Dict{String, TimeSeriesSource},
    dir::String,
    cluster_threshold::Float64,
    threshold_period::Int
)::Dict{String, TimeRange}
    # For single mast, no clustering needed
    if length(available_masts) == 1
        mast_name = available_masts[1]
        period = calculate_single_mast_period(
            mast_name, meso_by_name, results, train_config,
            single_outputs_by_mast, use_cross_mast_data, cross_outputs_by_mast, dir
        )
        return Dict(mast_name => period)
    end

    # Step 1: Load timeseries data for all masts (needed for timestamp-based overlap calculation)
    # IMPORTANT: Use reconstruct-single data for clustering, NOT cross-mast data
    # Cross-mast reconstruction fills gaps and artificially creates identical coverage
    # We want to cluster based on ACTUAL measurement overlap
    println("📊 Loading reconstruct-single timeseries data for $(length(available_masts)) masts (for clustering)...")
    mast_timeseries = Dict{String, TimeSeriesData}()
    for mast_name in available_masts
        single_source = get(single_outputs_by_mast, mast_name, nothing)
        if single_source === nothing
            error("No reconstruct-single output configured for $(mast_name). Please generate reconstruct-single first.")
        end
        mast_timeseries[mast_name] = load_timeseries(single_source, dir)
    end

    # Step 2: Calculate pairwise overlap matrix using actual timestamp intersection
    println("📊 Calculating pairwise overlap matrix (using timestamp intersection)...")
    overlap_matrix = calculate_pairwise_overlap(mast_timeseries, threshold_period)

    # Debug: Print overlap matrix
    sorted_masts = sort(available_masts)
    println("\n📊 Overlap Matrix (using timestamp intersection, sorted masts: $(join(sorted_masts, ", "))):")
    println("        ", join([rpad(m, 8) for m in sorted_masts], " "))
    for (i, mast_i) in enumerate(sorted_masts)
        row_values = [rpad(string(round(overlap_matrix[i, j], digits=3)), 8) for j in 1:length(sorted_masts)]
        println(rpad(mast_i, 7), " ", join(row_values, " "))
    end
    println()

    # Step 3: Cluster masts by overlap
    println("📊 Clustering masts (threshold=$(cluster_threshold), min_period=$(threshold_period) days)...")
    clusters = cluster_masts_by_overlap(sorted_masts, overlap_matrix, cluster_threshold)

    # Report clustering results
    n_clusters = length(clusters)
    single_mast_clusters = count(c -> length(c) == 1, values(clusters))
    multi_mast_clusters = n_clusters - single_mast_clusters
    println("📊 Found $(n_clusters) cluster(s): $(multi_mast_clusters) multi-mast, $(single_mast_clusters) single-mast")

    # Step 3.5: Calculate individual periods for single-mast clusters
    individual_periods = Dict{String, TimeRange}()
    for (cluster_id, cluster_masts) in clusters
        if length(cluster_masts) == 1
            mast_name = cluster_masts[1]
            individual_periods[mast_name] = calculate_single_mast_period(
                mast_name, meso_by_name, results, train_config,
                single_outputs_by_mast, use_cross_mast_data, cross_outputs_by_mast, dir
            )
        end
    end

    # Step 4: Calculate optimal period for each cluster
    mast_periods = Dict{String, TimeRange}()

    for (cluster_id, cluster_masts) in clusters
        if length(cluster_masts) == 1
            # Single-mast cluster: use individual period
            mast_name = cluster_masts[1]
            mast_periods[mast_name] = individual_periods[mast_name]
        else
            # Multi-mast cluster: calculate shared optimal period
            println("📊 Calculating shared period for cluster: $(join(cluster_masts, ", "))")

            # Reuse already-loaded timeseries for cluster masts
            cluster_ts = Dict(name => mast_timeseries[name] for name in cluster_masts)

            # Get meso data for first mast (should be same for all in practice)
            first_mast = cluster_masts[1]
            _, meso_source = select_reconstruct_model(train_config, first_mast, meso_by_name, results)
            meso_ts = load_timeseries(meso_source, dir)

            # Calculate cluster optimal period
            cluster_period = calculate_cluster_optimal_period(cluster_masts, cluster_ts, meso_ts)

            # Assign same period to all masts in cluster
            for mast_name in cluster_masts
                mast_periods[mast_name] = cluster_period
            end

            println("📊 Cluster period: $(Date(cluster_period.min)) to $(Date(cluster_period.max))")
        end
    end

    return mast_periods
end

"""
    calculate_single_mast_period(...)

Calculate optimal period for a single mast using the standard algorithm.
"""
function calculate_single_mast_period(
    mast_name::String,
    meso_by_name::Dict{String, TimeSeriesSource},
    results::TrainMesoResults,
    train_config::TrainMesoConfiguration,
    single_outputs_by_mast::Dict{String, TimeSeriesSource},
    use_cross_mast_data::Bool,
    cross_outputs_by_mast::Dict{String, TimeSeriesSource},
    dir::String
)::TimeRange
    _, meso_source = select_reconstruct_model(train_config, mast_name, meso_by_name, results)

    single_source = get(single_outputs_by_mast, mast_name, nothing)
    if single_source === nothing
        error("No reconstruct-single output configured for $(mast_name)")
    end
    reconstruct_single_ts = load_timeseries(single_source, dir)

    input_source = determine_input_source(
        mast_name, use_cross_mast_data,
        single_outputs_by_mast, cross_outputs_by_mast
    )
    input_reconstruction_ts = load_timeseries(input_source, dir)

    meso_data = load_timeseries(meso_source, dir)

    return calculate_optimal_measurement_period(
        reconstruct_single_ts,
        input_reconstruction_ts,
        meso_data
    )
end

end # module