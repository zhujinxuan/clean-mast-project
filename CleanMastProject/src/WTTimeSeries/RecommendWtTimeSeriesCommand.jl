module RecommendWtTimeSeriesCommand

using TOML
using YAML
using ...Types.WtTimeSeriesConfig: WtTimeSeriesConfiguration, WtTimeSeriesMast
using ...Types.RepresentativeYearConfig: RepresentativeYearConfiguration, RepresentativeYearMast
using ...Types.MastTimeSeries: TimeSeriesSource, load_timeseries
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict

export execute


"""
    discover_target_heights(dir::String, mast_name::String)::Vector{Float64}

Discover target heights for a specific mast by examining its sensors file.
Finds all WindSpeed sensors with statType="avg" and height >= 100.0m.

# Arguments
- `dir::String`: Project directory
- `mast_name::String`: Name of the mast

# Returns
- `Vector{Float64}`: List of target heights for this mast

# Note
This function uses a hardcoded 100.0m threshold for backward compatibility.
For configurable height thresholds, use the analyze timeseries functionality.
"""
function discover_target_heights(mast:: RepresentativeYearMast, dir::String)::Vector{Float64}
    ts = load_timeseries(mast.output, dir)

    # Find WindSpeed sensors with avg statType
    wind_speed_sensors = filter(s ->
        s.sensorType == "WindSpeed" &&
        s.statType == "avg" && s.height >= 100.0,
        ts.sensors
    )
    sort!(wind_speed_sensors, by = s -> s.height)

    return [s.height for s in wind_speed_sensors]
end

"""
    execute(dir::String)

Generate wt-timeseries.toml configuration based on available representative year data.

# Arguments
- `dir::String`: Project directory containing rep_year_calibration/
"""
function execute(dir::String)
    println("Discovering available masts in representative year calibration data...")
    rep_config_dict = load_dict(joinpath(dir, "representative-year.toml"))
    rep_config = from_dict(RepresentativeYearConfiguration, rep_config_dict)
    masts = map(rep_config.masts) do mast
        target_heights = discover_target_heights(mast, dir)
        WtTimeSeriesMast(
            mast.name,
            mast.output,
            "wt-timeseries",
            target_heights
        )
    end
    config = WtTimeSeriesConfiguration(masts)
    output_path = joinpath(dir, "wt-timeseries.toml")
    open(output_path, "w") do io
        println(io, "# Wind Turbine Time Series Configuration")
        println(io, "# Processes representative year data for wind turbine analysis")
        println(io, "# Generated automatically from rep_year_calibration/ directory")
        println(io)
        TOML.print(io, to_dict(config))
    end
    
    println("\nGenerated wt-timeseries.toml at: $output_path")
    println("Found $(length(masts)) valid mast configuration(s)")
    
    println("\nNext steps:")
    println("  1. Review and edit $(joinpath(dir, "wt-timeseries.toml")) if needed")
    println("  2. Run: julia bin/CleanMast.jl process wt-timeseries wt-timeseries.toml")
end

end # module 