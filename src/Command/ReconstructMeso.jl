module ReconstructMeso

using CSV, YAML, DataFrames, Dates
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.Utils: from_dict, to_dict
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData
using ...ReconstructMeso: reconstruct_from_meso
using ...MastTimeSeries: read_meso_data

export execute

"""
Generate reconstruction statistics for a column
"""
function analyze_column_reconstruction(
    mast_ts::TimeSeriesData,
    reconstructed_ts::TimeSeriesData,
    col::Symbol
)::NamedTuple{(:total_points, :original_missing, :final_missing, :reconstructed), 
              Tuple{Int, Int, Int, Int}}
    # Get all timestamps from both datasets
    all_times = sort(unique(vcat(mast_ts.df.timestamp, reconstructed_ts.df.timestamp)))
    
    # Create masks for missing data
    original_data = Dict(
        t => get(mast_ts.df[mast_ts.df.timestamp .== t, col], 1, missing)
        for t in all_times
    )
    reconstructed_data = Dict(
        t => get(reconstructed_ts.df[reconstructed_ts.df.timestamp .== t, col], 1, missing)
        for t in all_times
    )
    
    total_points = length(all_times)
    original_missing = count(ismissing, values(original_data))
    final_missing = count(ismissing, values(reconstructed_data))
    reconstructed = count(t -> ismissing(original_data[t]) && !ismissing(reconstructed_data[t]), all_times)
    
    return (
        total_points=total_points,
        original_missing=original_missing,
        final_missing=final_missing,
        reconstructed=reconstructed
    )
end

"""
Analyze timestamps that were added or still missing after reconstruction
"""
function analyze_timestamps(
    mast_ts::TimeSeriesData,
    reconstructed_ts::TimeSeriesData
)::NamedTuple{(:added_timestamps, :still_missing_timestamps), Tuple{Vector{DateTime}, Vector{DateTime}}}
    mast_times = Set(mast_ts.df.timestamp)
    reconstructed_times = Set(reconstructed_ts.df.timestamp)
    
    added_timestamps = sort(collect(setdiff(reconstructed_times, mast_times)))
    still_missing = Vector{DateTime}()
    
    # For each timestamp in reconstructed data, check if all columns are missing
    for t in sort(collect(reconstructed_times))
        row = reconstructed_ts.df[reconstructed_ts.df.timestamp .== t, :]
        sensor_columns = [s.columnName for s in reconstructed_ts.sensors]
        # Check if all sensor values are missing for this timestamp
        if all(ismissing, Array(row[:, sensor_columns]))
            push!(still_missing, t)
        end
    end
    
    return (
        added_timestamps=added_timestamps,
        still_missing_timestamps=sort(still_missing)
    )
end

function execute(dir::String)
    config = parse_config(dir)
    
    # Read single mast reconstruction data file
    original_filename = config.mast.data_path
    single_mast_filename = "reconstruct_single_mast.$(original_filename).csv"
    single_mast_filepath = joinpath(dir, single_mast_filename)
    
    if !isfile(single_mast_filepath)
        error("Single mast reconstruction data file not found: $single_mast_filepath")
    end
    
    # Read sensors from reconstruct_single_mast-sensors.yaml
    sensors_filepath = joinpath(dir, "reconstruct_single_mast-sensors.yaml")
    if !isfile(sensors_filepath)
        error("Single mast reconstruction sensors file not found: $sensors_filepath")
    end
    
    # Read mast data and sensors
    mast_df = CSV.read(single_mast_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    mast_sensors = map(s -> from_dict(SensorColumn, Dict{String,Any}(String(k) => v for (k,v) in s)), 
                      sensors_yaml["sensors"])
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    
    # Read meso data using existing function
    println("Reading meso data...")
    meso_ts = read_meso_data(config, dir)
    
    # Process reconstruction using meso data
    println("Processing meso reconstruction...")
    reconstructed_ts, ws_results, wd_results = reconstruct_from_meso(mast_ts, meso_ts, config.analysis.time_range)
    
    # Save training results to YAML
    ws_results_yaml = Dict{String, Any}()
    for (col, result) in ws_results
        ws_results_yaml[String(col)] = to_dict(result)
    end
    
    wd_results_yaml = Dict{String, Any}()
    for (col, result) in wd_results
        wd_results_yaml[String(col)] = to_dict(result)
    end
    
    # Combine both results into a single dictionary
    training_results = Dict{String, Any}(
        "ws_results" => ws_results_yaml,
        "wd_results" => wd_results_yaml
    )
    
    open(joinpath(dir, "reconstruct_meso-training.yaml"), "w") do io
        YAML.write(io, training_results)
    end
    
    # Analyze reconstruction results
    println("\nReconstruction Statistics:")
    println("==========================")
    
    # Filter and analyze only sensors with statType "avg"
    avg_sensors = filter(s -> s.statType == "avg", reconstructed_ts.sensors)
    
    println("\nReconstruction Statistics (Average Sensors Only):")
    println("=============================================")
    
    for sensor in avg_sensors
        stats = analyze_column_reconstruction(mast_ts, reconstructed_ts, sensor.columnName)
        println("\nColumn: $(sensor.columnName)")
        println("  Total points: $(stats.total_points)")
        println("  Originally missing: $(stats.original_missing)")
        println("  Reconstructed: $(stats.reconstructed)")
        println("  Still missing: $(stats.final_missing)")
        
        if stats.original_missing > 0
            pct_recovered = round(stats.reconstructed / stats.original_missing * 100, digits=1)
            println("  Recovery rate: $(pct_recovered)%")
        end
    end
    
    # Analyze timestamp changes
    time_analysis = analyze_timestamps(mast_ts, reconstructed_ts)
    
    println("\nTimestamp Analysis:")
    println("==================")
    println("Added $(length(time_analysis.added_timestamps)) new timestamps")
    if !isempty(time_analysis.added_timestamps)
        println("First 5 added timestamps:")
        for t in time_analysis.added_timestamps[1:min(5, length(time_analysis.added_timestamps))]
            println("  $t")
        end
    end
    
    println("\nFound $(length(time_analysis.still_missing_timestamps)) timestamps with all data missing")
    if !isempty(time_analysis.still_missing_timestamps)
        println("First 5 completely missing timestamps:")
        for t in time_analysis.still_missing_timestamps[1:min(5, length(time_analysis.still_missing_timestamps))]
            println("  $t")
        end
    end
    
    # Save processed data
    output_filename = "reconstruct_meso.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), reconstructed_ts.df)
    
    # Save sensors to YAML
    sensors_yaml = Dict("sensors" => map(to_dict, reconstructed_ts.sensors))
    
    open(joinpath(dir, "reconstruct_meso-sensors.yaml"), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    println("\nMeso reconstruction completed:")
    println("- Saved processed data to $(output_filename)")
    println("- Saved sensors to reconstruct_meso-sensors.yaml")
    println("- Saved training results to reconstruct_meso-training.yaml")
end

end # module 