module CommandTowerShading

using CSV, YAML, DataFrames, TOML
using ...Types.TowerShadingConfig: TowerShadingConfiguration
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, save_timeseries
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ..Core: process_tower_shading!

export execute

"""
    execute(config_path::String)

Execute tower shading processing based on configuration file.

# Arguments
- `config_path::String`: Path to tower-shading.toml configuration file
"""
function execute(config_path::String)
    println("Processing tower shading...")
    
    # Load configuration
    config_dict = load_dict(config_path)
    config = from_dict(TowerShadingConfiguration, config_dict)
    project_dir = dirname(config_path)
    
    # Process each mast
    for mast_config in config.masts
        println("Processing mast: $(mast_config.name)")
        
        # Load time series data
        time_series = load_timeseries(mast_config.input, project_dir)
        
        # Process tower shading
        result = process_tower_shading!(time_series)
        
        # Save results
        save_timeseries(mast_config.output, project_dir, result)
        
        println("Tower shading processing completed for mast: $(mast_config.name)")
        println("- Saved processed data to $(mast_config.output.data)")
        println("- Saved updated sensors to $(mast_config.output.sensors)")
    end
    
    println("\nTower shading processing completed successfully.")
end

end # module 