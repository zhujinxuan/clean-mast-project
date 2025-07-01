module RecommendReconstructMesoCommand

using TOML
using Dates
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoSource
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration, ReconstructMesoMast, ReconstructMesoModels, ReconstructMesoModelSpec
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ...TimeSeriesProcessing.TimeRangeProcessor: calculate_measurement_year_time_range

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
    
    # Build masts array
    masts = map(reconstruct_config.masts) do mast
        reconstruct_model = select_reconstruct_model(train_config, mast.name)
        if isnothing(reconstruct_model)
            return nothing
        end
        ReconstructMesoMast(
            mast.name,
            mast.output,
            TimeSeriesSource(
                joinpath("./reconstruct-meso", "$(mast.name).csv"),
                joinpath("./reconstruct-meso", "$(mast.name).sensors.yaml")
            ),
            calculate_measurement_year_time_range(load_timeseries(mast.input, dir)),
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