module RecommendRepresentativeYearCommand

using TOML
using Dates
using ...Types.RepresentativeYearConfig: RepresentativeYearConfiguration, RepresentativeYearMast, RepresentativeYearMesoModel
using ...Types.TrainMesoConfig: TrainMesoConfiguration, TrainMesoSource
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration
using ...Types.MastTimeSeries: TimeSeriesSource, TimeRange
using ...Types.Utils: from_dict, to_dict, strip_nothing_values
using ...CleanMastUtils: load_dict

export execute, select_last_year

"""
    select_last_year(time_range::TimeRange)::TimeRange

Select the last year from a time range for representative year calibration.

Representative year calibration requires exactly 1 year of data. When reconstruct-meso
spans multiple years, this function extracts the last year.

# Algorithm
1. If end time is 23:59:59, round to next day (00:00:00)
2. Subtract 1 year to get start time
3. Keep original end time

# Examples
- Input: 2022-01-01 00:00:00 to 2024-12-31 23:59:59 (3 years)
  Output: 2024-01-01 00:00:00 to 2024-12-31 23:59:59 (last year)

- Input: 2023-06-15 00:00:00 to 2024-06-14 23:59:59 (1 year)
  Output: 2023-06-15 00:00:00 to 2024-06-14 23:59:59 (unchanged)

# Arguments
- `time_range::TimeRange`: Time range from reconstruct-meso (can be 1+ years)

# Returns
- `TimeRange`: Exactly 1 year period (the last year of the input range)
"""
function select_last_year(time_range::TimeRange)::TimeRange
    end_time = time_range.max

    # If end time is within 10 minutes of next day, round to next day for calculation
    # This handles the common pattern where periods end near midnight (e.g., 23:59:59)
    rounded_end = if Date(end_time + Minute(10)) != Date(end_time)
        DateTime(Date(end_time) + Day(1))
    else
        end_time
    end

    # Calculate start as exactly 1 year before rounded end
    start_time = rounded_end - Year(1)

    # Return with original end time
    return TimeRange(start_time, end_time)
end

# Find 16-sector model that uses the same meso source as reconstruct meso operation
function find_16sectors_meso_models(
    config :: TrainMesoConfiguration,
    mast_name :: String,
    reconstruct_config :: ReconstructMesoConfiguration
) :: RepresentativeYearMesoModel

    # Find the meso source used by windspeed model in reconstruct meso
    reconstruct_mast = findfirst(m -> m.name == mast_name, reconstruct_config.masts)
    if isnothing(reconstruct_mast)
        error("Mast $(mast_name) not found in reconstruct meso configuration")
    end

    preferred_meso_name = reconstruct_config.masts[reconstruct_mast].models.windspeed.meso_name

    # Filter 16-sector models for this mast
    models = filter(m -> m.mast_name == mast_name && m.method == "16-sector", config.models)
    if isempty(models)
        error("No 16-sector model found for $(mast_name)")
    end

    # Try to find a model that uses the same meso source as reconstruct meso
    preferred_model = findfirst(m -> m.meso_name == preferred_meso_name, models)

    if !isnothing(preferred_model)
        model = models[preferred_model]
        println("  Using 16-sector model with meso source '$(preferred_meso_name)' to match reconstruct meso")
    else
        model = first(models)  # Fall back to first available
        @warn "No 16-sector model found for meso source '$(preferred_meso_name)'. Using '$(model.meso_name)' instead."
    end

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
    # Representative year requires exactly 1 year - select last year from meso period
    masts = map(reconstruct_config.masts) do mast
        RepresentativeYearMast(
            mast.name,
            mast.output,
                 TimeSeriesSource(
                    joinpath("./representative-year", "$(mast.name).parquet"),
                    nothing
                ),
            select_last_year(mast.time_range),
            find_16sectors_meso_models(train_config, mast.name, reconstruct_config)
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
        TOML.print(io, strip_nothing_values(Dict{String, Any}(to_dict(output_config))))
    end
    
    println("Generated representative-year.toml at: $output_path")
    println("Found $(length(masts)) configuration(s) for calibration")
end

end # module 