module TurbulenceIntensity

using DataFrames
using CSV
using YAML
using ...Types.CleanMastConfig: ProjectConfig
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.Sector: DIRECTION_16_SECTORS
using ...Types.TurbulenceIntensity: TurbulenceResults
using ...TurbulenceIntensity: process_turbulence_intensity
using ...CleanMastConfig: parse_config
using ...Types.Utils: from_dict

"""
Save turbulence intensity results to files

# Arguments
- `dir::String`: Project directory
- `config::ProjectConfig`: Project configuration
- `results::TurbulenceResults`: Complete turbulence intensity analysis results
"""
function save_results(
    dir::String,
    config::ProjectConfig,
    results::TurbulenceResults
)::Nothing
    # Create output directory if it doesn't exist
    mkpath(dir)
    
    # Save main TI results with all required columns
    ti_results = select(
        results.sector_stats.sector_stats,
        :sector,
        :mean_speed => :mean,
        :ti,
        :std,
        :occurrence
    )
    CSV.write(
        joinpath(dir, "turbulence_intensity.csv"),
        ti_results
    )
    
    # Save report summary
    mast_name = basename(dir)
    report_df = DataFrame(
        mast = [mast_name],
        mean_ti = [results.sector_stats.mean_ti],
        representative_ti = [results.sector_stats.representative_ti],
        ti_std = [results.sector_stats.std_ti]
    )
    CSV.write(
        joinpath(dir, "turbulence_intensity_report.csv"),
        report_df
    )
    
    # Save Meteodyn WT input file
    open(joinpath(dir, "meteodyn_ti.txt"), "w") do io
        println(io, length(results.matrix.v_max))
        for row in eachrow(results.matrix)
            values = [row.v_max]
            append!(values, [row[sector.name] for sector in DIRECTION_16_SECTORS])
            println(io, join(values, "\t"))
        end
    end
    
    println("Turbulence intensity analysis completed:")
    println("- Saved TI results to turbulence_intensity.csv")
    println("- Saved report to turbulence_intensity_report.csv")
    println("- Saved Meteodyn WT input to meteodyn_ti.txt")
    
    return nothing
end

"""
Execute turbulence intensity analysis

# Arguments
- `project_path::String`: Path to the project directory containing config.yaml
"""
function execute(project_path::String)::Nothing
    # Load project configuration
    config = parse_config(project_path)
    
    # Read tower shading results
    original_filename = config.mast.data_path
    tower_shading_file = joinpath(project_path, "tower_shading.$(original_filename).csv")
    
    if !isfile(tower_shading_file)
        error("Tower shading results not found: $tower_shading_file")
    end
    
    # Read the data
    df = CSV.read(tower_shading_file, DataFrame)
    
    # Read sensors from YAML
    sensors_file = joinpath(project_path, "tower-shading-sensors.yaml")
    if !isfile(sensors_file)
        error("Sensors file not found: $sensors_file")
    end
    
    # Read and convert sensors
    sensors_yaml = YAML.load_file(sensors_file)
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_yaml["sensors"]]
    
    ts = TimeSeriesData(df, sensors)
    
    # Process turbulence intensity
    results = process_turbulence_intensity(config, ts)
    
    # Save results
    save_results(project_path, config, results)
    
    return nothing
end

export execute

end 