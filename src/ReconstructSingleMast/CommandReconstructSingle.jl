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
    println("Processing single mast reconstruction...")
    
    # Load configuration
    config_dict = load_dict(config_path)
    config = from_dict(ReconstructSingleConfiguration, config_dict)
    project_dir = dirname(config_path)
    
    # Process each mast
    for mast_config in config.masts
        println("Processing mast: $(mast_config.name)")
        
        # Load time series data
        time_series = load_timeseries(mast_config.input, project_dir)
        
        # Process reconstruction and get results
        reconstruction_results = process_data!(time_series)
        
        # Save results
        save_timeseries(mast_config.output, project_dir, time_series)
        
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
        
        # Display reconstruction statistics
        total_reconstructed = length(reconstruction_results.successes)
        total_failures = length(reconstruction_results.failures)
        total_attempts = total_reconstructed + total_failures
        success_rate = total_attempts > 0 ? round(total_reconstructed / total_attempts * 100, digits=1) : 0.0
        
        println("\nReconstruction Statistics for $(mast_config.name):")
        println("==========================")
        println("Total points attempted: $total_attempts")
        println("Successfully reconstructed: $total_reconstructed")
        println("Failed to reconstruct: $total_failures")
        println("Success rate: $(success_rate)%")
        
        # Group successes by column to show per-sensor statistics
        successes_by_column = Dict{Symbol, Int}()
        for success in reconstruction_results.successes
            col = success["columnName"]
            successes_by_column[col] = get(successes_by_column, col, 0) + 1
        end
        
        if !isempty(successes_by_column)
            println("\nReconstructions by sensor:")
            for (col, count) in sort(collect(successes_by_column))
                println("  $col: $count points")
            end
        end
        
        println("\nSingle mast reconstruction completed for $(mast_config.name):")
        println("- Saved processed data to $(mast_config.output.data)")
        println("- Saved updated sensors to $(mast_config.output.sensors)")
        println("- Saved reconstruction details to process-stats/$(stats_filename)")
    end
    
    println("\nSingle mast reconstruction completed successfully.")
end

end # module 