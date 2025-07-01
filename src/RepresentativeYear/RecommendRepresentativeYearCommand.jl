module RecommendRepresentativeYearCommand

using TOML
using Dates
using ...Types.RepresentativeYearConfig: RepresentativeYearConfiguration, RepresentativeYearMast, RepresentativeYearMesoModel
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoSource
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict

export execute

# In future, we shall use best correlation to find which meso model to use.
function find_16sectors_meso_models(config :: TrainMesoConfiguration, mast_name :: String) :: RepresentativeYearMesoModel
    models = filter(m -> m.mast_name == mast_name && m.method == "16-sector", config.models)
    if isempty(models)
        error("No 16-sector model found for $(mast_name)")
    end
    model = first(models)
    return from_dict(RepresentativeYearMesoModel, Dict{String, Any}(
        "method" => "16-sector",
        "meso_name" => model.meso_name,
        "model_file" => model.output
    ))
end

"""
    execute(dir::String)

Generate representative-year.toml configuration based on reconstruct-meso.toml.

# Arguments
- `dir::String`: Project directory containing reconstruct-meso.toml
"""
function execute(dir::String)
    # Read reconstruct-meso.toml
    reconstruct_meso_path = joinpath(dir, "reconstruct-meso.toml")
    if !isfile(reconstruct_meso_path)
        error("reconstruct-meso.toml not found. Please run 'recommend reconstruct-meso' first.")
    end
    
    # Load reconstruct meso configuration
    reconstruct_config_dict = load_dict(reconstruct_meso_path)
    reconstruct_config = from_dict(ReconstructMesoConfiguration, reconstruct_config_dict)
    
    # Load train-meso.toml to find 16-sector models if needed
    train_meso_path = joinpath(dir, "train-meso.toml")
    train_config = nothing
    if isfile(train_meso_path)
        train_dict = load_dict(train_meso_path)
        train_config = from_dict(TrainMesoConfiguration, train_dict)
    end
    
    # Create mast entry for calibration
    masts = map(reconstruct_config.masts) do mast
        RepresentativeYearMast(
            mast.name,
            mast.output,
             TimeSeriesSource(
                joinpath("./representative-year", "$(mast.name).csv"),
                joinpath("./representative-year", "$(mast.name).sensors.yaml")
            ),
            mast.time_range,
            find_16sectors_meso_models(train_config, mast.name)
        )
    end
    
    # Create output configuration
    output_config = RepresentativeYearConfiguration(
        masts,
        train_config.mesos
    )
    
    # Write to representative-year.toml
    output_path = joinpath(dir, "representative-year.toml")
    open(output_path, "w") do io
        println(io, "# Representative Year Calibration Configuration")
        println(io, "# Calibrates data to a representative year using mesoscale patterns")
        println(io, "# Note: Prefers 16-sector windspeed model for directional calibration")
        println(io)
        TOML.print(io, to_dict(output_config))
    end
    
    println("Generated representative-year.toml at: $output_path")
    println("Found $(length(masts)) configuration(s) for calibration")
end

end # module 