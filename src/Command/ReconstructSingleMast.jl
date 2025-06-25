module ReconstructSingleMast

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.SensorColumns: SensorColumn
using ...Types.Utils: from_dict, to_dict
using ...ReconstructSingleMast.ProcessData: process_data!

export execute

function execute(dir::String)
    config = parse_config(dir)
    
    # Read tower shading data file
    original_filename = config.mast.data_path
    tower_shading_filename = "tower_shading.$(original_filename).csv"
    tower_shading_filepath = joinpath(dir, tower_shading_filename)
    
    if !isfile(tower_shading_filepath)
        error("Tower shading data file not found: $tower_shading_filepath")
    end
    
    # Read sensors from tower-shading-sensors.yaml
    sensors_filepath = joinpath(dir, "tower-shading-sensors.yaml")
    if !isfile(sensors_filepath)
        error("Tower shading sensors file not found: $sensors_filepath")
    end
    
    # Read tower shading data and sensors
    df = CSV.read(tower_shading_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    
    # Convert YAML sensors to SensorColumn objects
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_yaml["sensors"]]
    
    time_series = TimeSeriesData(df, sensors)
    
    # Process reconstruction and get results
    println("Processing single mast reconstruction...")
    reconstruction_results = process_data!(config, time_series)
    
    # Save processed data
    output_filename = "reconstruct_single_mast.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), time_series.df)
    
    # Save updated sensors to YAML
    sensors_yaml = Dict(
        "sensors" => map(to_dict, time_series.sensors)
    )
    
    open(joinpath(dir, "reconstruct_single_mast-sensors.yaml"), "w") do io
        YAML.write(io, sensors_yaml)
    end

    # Write reconstruction results to YAML
    reconstruction_dict = Dict(
        "successes" => reconstruction_results.successes,
        "failures" => reconstruction_results.failures
    )

    # Ensure the process-stats directory exists
    process_stats_dir = joinpath(dir, "process-stats")
    mkpath(process_stats_dir)

    open(joinpath(process_stats_dir, "single-reconstruction.yaml"), "w") do io
        YAML.write(io, reconstruction_dict)
    end
    
    # Display reconstruction statistics
    total_reconstructed = length(reconstruction_results.successes)
    total_failures = length(reconstruction_results.failures)
    total_attempts = total_reconstructed + total_failures
    success_rate = total_attempts > 0 ? round(total_reconstructed / total_attempts * 100, digits=1) : 0.0

    println("\nReconstruction Statistics:")
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
    
    println("\nSingle mast reconstruction completed:")
    println("- Saved processed data to $(output_filename)")
    println("- Saved updated sensors to reconstruct_single_mast-sensors.yaml")
    println("- Saved reconstruction details to single-reconstruction.yaml")
end

end # module 