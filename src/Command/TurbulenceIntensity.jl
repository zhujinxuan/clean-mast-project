module TurbulenceIntensity

using DataFrames
using CSV
using YAML
using ...Types.CleanMastConfig: ProjectConfig
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.Sector: DIRECTION_16_SECTORS
using ...Types.TurbulenceIntensity: TurbulenceResults
using ...TurbulenceIntensity: process_turbulence_intensity, DEFAULT_WIND_SPEED_BINS, calculate_filtered_sector_stats, calculate_ti_by_wind_speed
using ...CleanMastConfig: parse_config
using ...Types.Utils: from_dict

"""
Save turbulence intensity results to files

# Arguments
- `dir::String`: Project directory
- `results::TurbulenceResults`: Complete turbulence intensity analysis results
"""
function save_results(
    project_dir::String,
    results::TurbulenceResults,
    height::Float64
)::Nothing
    # Create output directory including height in the path
    dir = joinpath(project_dir, "analysis", "turbulence_intensity", "$(height)m")
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
        joinpath(dir,"turbulence_intensity.csv"),
        ti_results
    )
    
    # Generate and save turbulence intensity by wind speed analysis
    ti_by_wind_speed = calculate_ti_by_wind_speed(results.time_series, DEFAULT_WIND_SPEED_BINS)
    CSV.write(
        joinpath(dir, "turbulence_intensity_by_wind_speed.csv"),
        ti_by_wind_speed
    )
    
    # Calculate TI for different wind speed ranges
    mast_name = basename(dir)
    
    # All wind speeds (already calculated)
    all_speeds_ti = results.sector_stats.mean_ti
    all_speeds_rep_ti = results.sector_stats.representative_ti
    all_speeds_std_ti = results.sector_stats.std_ti
    
    # Wind speeds > 3 m/s
    above_3_stats = calculate_filtered_sector_stats(results.time_series, min_ws=3.0)
    
    # Wind speeds between 14.5 and 16.5 m/s
    ws_14_5_16_5_stats = calculate_filtered_sector_stats(results.time_series, min_ws=14.5, max_ws=16.5)
    
    # Wind speeds between 9.5 and 10.5 m/s
    ws_9_5_10_5_stats = calculate_filtered_sector_stats(results.time_series, min_ws=9.5, max_ws=10.5)
    
    # Create expanded report with all wind speed ranges
    report_df = DataFrame(
        mast = [mast_name, mast_name, mast_name, mast_name],
        wind_speed_range = ["all", ">3 m/s", "14.5-16.5 m/s", "9.5-10.5 m/s"],
        mean_ti = [
            all_speeds_ti,
            above_3_stats.mean_ti,
            ws_14_5_16_5_stats.mean_ti,
            ws_9_5_10_5_stats.mean_ti
        ],
        representative_ti = [
            all_speeds_rep_ti,
            above_3_stats.representative_ti,
            ws_14_5_16_5_stats.representative_ti,
            ws_9_5_10_5_stats.representative_ti
        ],
        ti_std = [
            all_speeds_std_ti,
            above_3_stats.std_ti,
            ws_14_5_16_5_stats.std_ti,
            ws_9_5_10_5_stats.std_ti
        ]
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
    println("- Saved TI results to $(height)m/turbulence_intensity.csv")
    println("- Saved TI by wind speed to $(height)m/turbulence_intensity_by_wind_speed.csv")
    println("- Saved report to $(height)m/turbulence_intensity_report.csv")
    println("- Saved Meteodyn WT input to $(height)m/meteodyn_ti.txt")
    
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
    
    # Determine which heights to process
    ti_heights = if !isempty(config.analysis.ti_target_heights)
        config.analysis.ti_target_heights
    elseif !isempty(config.analysis.target_heights)
        # Fallback to regular target heights if no TI-specific heights are configured
        config.analysis.target_heights
    else
        error("No target heights configured for turbulence intensity analysis")
    end
    
    # Load data (only once) to avoid repeated file reads
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
    
    # Process each height
    println("Processing turbulence intensity for $(length(ti_heights)) height(s):")
    for height in ti_heights
        println("\nProcessing height: $(height)m")
        
        # Process turbulence intensity for this height
        results = process_turbulence_intensity(ts, height, DEFAULT_WIND_SPEED_BINS)
        
        # Save results to height-specific location
        save_results(project_path, results, height)
    end
    
    return nothing
end

export execute

end 