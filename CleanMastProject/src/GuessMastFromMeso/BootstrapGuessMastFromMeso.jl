module BootstrapGuessMastFromMeso

using Dates
using TOML
using ...Types.MastTimeSeries: TimeSeriesSource, load_timeseries
using ...RepresentativeYear.Utils: find_heighest_meso_sensor, calculate_climatology_mean,
                                    find_representative_year

export bootstrap_guess_mast_from_meso_config

"""
    find_sensors_file(meso_csv_path::String)::String

Find sensors file for given meso CSV by checking basename.sensors.toml in same directory.
"""
function find_sensors_file(meso_csv_path::String)::String
    dir = dirname(meso_csv_path)
    base = basename(meso_csv_path)

    base_without_ext = replace(base, r"\.csv$" => "")
    sensors_path = joinpath(dir, "$(base_without_ext).sensors.toml")

    if !isfile(sensors_path)
        error("Sensors file not found: $sensors_path")
    end

    return sensors_path
end

"""
    bootstrap_guess_mast_from_meso_config(meso_csv_path::String; output_path::Union{String, Nothing}=nothing)::String

Generate an incomplete guess-mast-from-meso.toml configuration file with time_series and meso sections.

# Arguments
- `meso_csv_path::String`: Path to meso data CSV file
- `output_path::Union{String, Nothing}`: Optional output path for configuration file (default: ../{meso-basename}.guess-mast-from-meso.toml relative to meso directory)

# Returns
- `String`: Path to generated configuration file
"""
function bootstrap_guess_mast_from_meso_config(meso_csv_path::String; output_path::Union{String, Nothing}=nothing)::String
    abs_meso_path = abspath(meso_csv_path)

    println("🔍 Finding sensors file for meso data...")
    sensors_path = find_sensors_file(abs_meso_path)
    println("   Found: $sensors_path")

    meso_dir = dirname(abs_meso_path)
    base_name = replace(basename(meso_csv_path), r"\.csv$" => "")

    config_output_path = if isnothing(output_path)
        joinpath(meso_dir, "..", "$(base_name).guess-mast-from-meso.toml")
    else
        output_path
    end
    config_output_path = abspath(config_output_path)

    config_dir = dirname(config_output_path)
    rel_data_path = relpath(abs_meso_path, config_dir)
    rel_sensors_path = relpath(sensors_path, config_dir)

    println("   Loading meso data to find representative year...")
    meso_source = TimeSeriesSource(rel_data_path, rel_sensors_path)
    meso_ts = load_timeseries(meso_source, config_dir)

    meso_sensor = find_heighest_meso_sensor(meso_ts)
    if isnothing(meso_sensor)
        error("No wind speed sensor found in meso data")
    end
    println("   Highest meso sensor: $(meso_sensor.columnName) @ $(meso_sensor.height)m")

    climatology_mean = calculate_climatology_mean(meso_ts, meso_sensor)
    println("   Climatology mean wind speed (complete years only): $(round(climatology_mean, digits=2)) m/s")

    rep_year_start = find_representative_year(meso_ts, climatology_mean, meso_sensor)
    rep_year_end = rep_year_start + Year(1) - Second(1)
    println("   Representative year found: $rep_year_start to $rep_year_end")

    config_dict = Dict{String, Any}(
        "meso" => Dict{String, Any}(
            "name" => base_name,
            "input" => Dict{String, Any}(
                "data" => rel_data_path,
                "sensors" => rel_sensors_path
            ),
            "time_range" => Dict{String, Any}(
                "min" => rep_year_start,
                "max" => rep_year_end
            )
        ),
        "output" => Dict{String, Any}(
            "name" => "guessed-mast",
            "sensors" => "./guessed-masts/$(base_name)-vm.sensors.toml",
            "data" => "./guessed-masts/$(base_name)-vm.csv"
        ),
        "targets" => [
            Dict{String, Any}("height" => 160.0, "mean_speed" => "TODO"),
            Dict{String, Any}("height" => 140.0, "mean_speed" => "TODO"),
            Dict{String, Any}("height" => 120.0, "mean_speed" => "TODO")
        ]
    )

    println("   Generating bootstrap configuration file...")
    open(config_output_path, "w") do io
        write(io, """
# Guess Mast Data from Mesoscale Configuration (INCOMPLETE - REQUIRES MANUAL EDITING)
# Fill in TODO fields before processing

""")
        TOML.print(io, config_dict)
        write(io, """

# Instructions:
# 1. Review [meso.time_range] (auto-generated representative year, adjust if needed)
# 2. Set [targets] mean_speed values for each height (m/s)
# 3. Run: julia bin/CleanMast.jl process guess-mast-from-meso $(basename(config_output_path))
#
# Note: This command generates synthetic mast data from meso data alone.
# Wind speeds are scaled to match your target mean_speed values.
# No actual mast data is required as input
""")
    end

    println("✅ Bootstrap configuration file generated: $config_output_path")
    println("   ⚠️  Please set target mean_speed values before processing")

    return config_output_path
end

end
