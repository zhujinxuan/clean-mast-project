module CommandReconstructSingle

using CSV, YAML, DataFrames, TOML
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, save_timeseries
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ..ProcessData: process_data!

export execute

"""
    execute(config_path::String)

Execute single mast reconstruction based on configuration file.

# Arguments
- `config_path::String`: Path to reconstruct-single.toml configuration file
"""
function execute(config_path::String)
    println("🔄 Processing single mast reconstruction...")
    
    # Load configuration
    config_dict = load_dict(config_path)
    config = from_dict(ReconstructSingleConfiguration, config_dict)
    project_dir = dirname(config_path)
    
    # Process each mast
    for (i, mast_config) in enumerate(config.masts)
        println("\n📊 Processing mast $(i)/$(length(config.masts)): $(mast_config.name)")
        
        # Load time series data
        print("  Loading time series data... ")
        time_series = load_timeseries(mast_config.input, project_dir)
        println("✓ $(nrow(time_series.df)) rows, $(length(time_series.sensors)) sensors")
        
        # Process reconstruction and get results
        reconstruction_results = process_data!(time_series)
        
        # Save results
        print("  Saving results... ")
        save_timeseries(mast_config.output, project_dir, time_series)
        println("✓")
        
        # Write reconstruction results to YAML
        reconstruction_dict = Dict(
            "successes" => reconstruction_results.successes,
            "failures" => reconstruction_results.failures
        )
        
        # Ensure the process-stats directory exists
        process_stats_dir = joinpath(project_dir, "process-stats")
        mkpath(process_stats_dir)
        
        stats_filename = "reconstruct-single-$(mast_config.name).yaml"
        open(joinpath(process_stats_dir, stats_filename), "w") do io
            YAML.write(io, reconstruction_dict)
        end
        
        println("  📁 Results saved:")
        println("    • Data: $(mast_config.output.data)")
        println("    • Sensors: $(mast_config.output.sensors)")
        println("    • Statistics: process-stats/$(stats_filename)")
    end
    
    println("\n🎉 Single mast reconstruction completed successfully!")
end

end # module 