module RecommendReconstructMesoCommand

using TOML
using Dates
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoSource
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration, ReconstructMesoMast, ReconstructMesoModels, ReconstructMesoModelSpec
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ...TimeSeriesProcessing.MeasurementPeriodCalculator: calculate_optimal_measurement_period

export execute

# Find the suitable meso source and model for reconstruction.
# Right now use the first model that matches.
function select_reconstruct_model(trainMeso :: TrainMesoConfiguration, mast_name :: String) :: Union{ReconstructMesoModels, Nothing}
    models = filter(m -> m.mast_name == mast_name, trainMeso.models)

    if (isempty(models))
        return nothing
    end

    windspeed_model = first(filter(m -> m.method == "1-sector", models))
    winddirection_model = first(filter(m -> m.method == "constant-offset", models))
    return ReconstructMesoModels(
        ReconstructMesoModelSpec(
            "1-sector",
            windspeed_model.meso_name,
            windspeed_model.output
        ),
        ReconstructMesoModelSpec(
              "constant-offset",
              winddirection_model.meso_name,
              winddirection_model.output
        )
    )
end

"""
    execute(dir::String)

Generate reconstruct-meso.toml configuration based on train-meso.toml.

# Arguments
- `dir::String`: Project directory containing train-meso.toml
"""
function execute(dir::String)
    # Read train-meso.toml
    train_meso_path = joinpath(dir, "train-meso.toml")
    if !isfile(train_meso_path)
        error("train-meso.toml not found. Please run 'recommend train-meso' first.")
    end
    
    # Load train meso configuration
    config_dict = load_dict(train_meso_path)
    train_config = from_dict(TrainMesoConfiguration, config_dict)
    
    # Read reconstruct-single.toml to get mast data paths
    reconstruct_single_path = joinpath(dir, "reconstruct-single.toml")
    if !isfile(reconstruct_single_path)
        error("reconstruct-single.toml not found. Please run 'recommend reconstruct-single' first.")
    end
    
    reconstruct_dict = load_dict(reconstruct_single_path)
    reconstruct_config = from_dict(ReconstructSingleConfiguration, reconstruct_dict)
    
    # Load meso data for time range calculation
    meso_data = if !isempty(train_config.mesos)
        load_timeseries(train_config.mesos[1].input, dir)  # Use first available meso source
    else
        error("No mesoscale data sources found in train-meso configuration")
    end

    # Build masts array
    masts = map(reconstruct_config.masts) do mast
        reconstruct_model = select_reconstruct_model(train_config, mast.name)
        if isnothing(reconstruct_model)
            return nothing
        end

        # Load the time series data needed for optimal period calculation
        reconstruct_single_ts = load_timeseries(mast.input, dir)
        
        # Try to find reconstruct-cross data for this mast
        cross_mast_path = joinpath(dir, "reconstruct-cross", "$(mast.name)_reconstructed.csv")
        cross_sensors_path = joinpath(dir, "reconstruct-cross", "$(mast.name)_reconstructed.sensors.yaml")
        
        reconstruct_cross_ts = if isfile(cross_mast_path) && isfile(cross_sensors_path)
            cross_source = TimeSeriesSource(cross_mast_path, cross_sensors_path)
            load_timeseries(cross_source, ".")  # Use absolute paths
        else
            # If no cross reconstruction available, use single reconstruction as fallback
            @warn "No reconstruct-cross data found for $(mast.name), using reconstruct-single data for both inputs"
            reconstruct_single_ts
        end

        # Calculate optimal measurement period
        optimal_time_range = calculate_optimal_measurement_period(
            reconstruct_single_ts,
            reconstruct_cross_ts,
            meso_data
        )

        ReconstructMesoMast(
            mast.name,
            mast.output,
            TimeSeriesSource(
                joinpath("./reconstruct-meso", "$(mast.name).csv"),
                joinpath("./reconstruct-meso", "$(mast.name).sensors.yaml")
            ),
            optimal_time_range,
            reconstruct_model,
        )
    end
    
    # Create output configuration
    output_config = ReconstructMesoConfiguration(
        filter(x -> !isnothing(x), masts),
        train_config.mesos
    )
    
    # Write to reconstruct-meso.toml
    output_path = joinpath(dir, "reconstruct-meso.toml")
    open(output_path, "w") do io
        println(io, "# Mesoscale Reconstruction Configuration")
        println(io, "# Uses trained models to fill remaining gaps with mesoscale data")
        println(io)
        TOML.print(io, to_dict(output_config))
    end
    
    println("Generated reconstruct-meso.toml at: $output_path")
    println("Found $(length(masts)) mast configuration(s) for reconstruction")
end

end # module 