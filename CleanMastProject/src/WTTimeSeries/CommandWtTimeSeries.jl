module CommandWtTimeSeries

using ...Types.WtTimeSeriesConfig: WtTimeSeriesConfiguration
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ..Core: process_wt_timeseries

export execute

"""
    execute(config_path::String)

Execute wind turbine time series processing based on configuration file.

# Arguments
- `config_path::String`: Path to wt-timeseries.toml configuration file

# Example
```bash
julia bin/CleanMast.jl process wt-timeseries wt-timeseries.toml
```

The configuration file should specify:
- Multiple masts with their input data sources and target heights
- Output directories for each mast
- Individual target heights for each mast based on available sensors

For each mast and target height combination, generates:
- CSV file with timestamp, wind_speed, and wind_direction columns
- Files named as: {mast_name}-{height}m.csv (e.g., mast-01-120_0m.csv)
"""
function execute(config_path::String)
    println("Processing wind turbine time series...")
    
    # Validate configuration file exists
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end
    
    # Load configuration
    println("Loading configuration from: $config_path")
    config_dict = load_dict(config_path)
    config = from_dict(WtTimeSeriesConfiguration, config_dict)
    
    # Get project directory from config file location
    project_dir = dirname(config_path)
    
    # Validate configuration
    if isempty(config.masts)
        error("No masts specified in configuration file")
    end
    
    # Print configuration summary
    println("Configuration loaded successfully:")
    println("- Project directory: $project_dir")
    println("- Number of masts: $(length(config.masts))")
    
    for mast in config.masts
        println("  - $(mast.name): $(length(mast.target_heights)) height(s) → $(mast.output_dir)")
    end
    
    # Execute processing
    process_wt_timeseries(config, project_dir)
end

end # module 