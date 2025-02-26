module ReconstructMeso

using CSV, YAML, DataFrames, JLD2
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData, TimeRange
using ...MastTimeSeries: read_meso_data
using ...Types.Utils: from_dict, to_dict, show_as_dataframe
using ...Types.MastReferenceModel: ReconstructionPayload
using ...MergeReconstructMeso: merge_reconstruct_meso
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using ...Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel
using ...TimeSeriesProcessing.TimeRangeProcessor: calculate_reconstruction_time_range

export execute

"""
    load_model(model_path::String, model_type::Type{T})::T where T

Load a trained model from a JLD2 file.
"""
function load_model(model_path::String, model_type::Type{T})::T where T
    if !isfile(model_path)
        error("Model file not found: $model_path")
    end
    jldopen(model_path, "r") do file
        file["model"]::model_type
    end
end

function execute(dir::String)
    # Parse config
    config = parse_config(dir)
    
    # Read reconstructed mast data from single mast reconstruction
    original_filename = config.mast.data_path
    reconstructed_filename = "reconstruct_single_mast.$(original_filename).csv"
    reconstructed_filepath = joinpath(dir, reconstructed_filename)
    
    if !isfile(reconstructed_filepath)
        error("Reconstructed mast data file not found: $reconstructed_filepath")
    end
    
    # Read sensors from reconstruct_single_mast-sensors.yaml
    sensors_filepath = joinpath(dir, "reconstruct_single_mast-sensors.yaml")
    if !isfile(sensors_filepath)
        error("Reconstructed mast sensors file not found: $sensors_filepath")
    end
    
    # Read mast data and sensors
    mast_df = CSV.read(reconstructed_filepath, DataFrame)
    sensors_yaml = YAML.load_file(sensors_filepath)
    mast_sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_yaml["sensors"]]
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    
    # Read meso data
    meso_ts = read_meso_data(config, dir)
    
    # Get time range from config or use full range
    time_range = calculate_reconstruction_time_range(mast_ts, config.analysis.time_range)
    
    # Create initial reconstruction payload
    mast_payload = ReconstructionPayload(mast_ts, [])
    
    # Load and apply 1-sector wind speed model
    println("Reconstructing wind speeds using 1-sector model...")
    model_1sector_path = joinpath(dir, "models", "windspeed", "1-sector", "_meso_era5.jld2")
    model_1sector = load_model(model_1sector_path, SectorizedRegressionModel)
    mast_payload = merge_reconstruct_meso(mast_payload, meso_ts, model_1sector, time_range)
    
    # Load and apply direction offset model
    println("Reconstructing wind directions using constant offset model...")
    model_direction_path = joinpath(dir, "models", "winddirection", "constant-direction-offset", "_meso_era5.jld2")
    model_direction = load_model(model_direction_path, DirectionOffsetModel)
    mast_payload = merge_reconstruct_meso(mast_payload, meso_ts, model_direction, time_range)
    
    # Save reconstructed data
    output_filename = "reconstruct_meso.$(original_filename).csv"
    CSV.write(joinpath(dir, output_filename), mast_payload.data.df)
    
    # Save updated sensors to YAML
    sensors_yaml = Dict(
        "sensors" => map(to_dict, mast_payload.data.sensors)
    )
    open(joinpath(dir, "reconstruct_meso-sensors.yaml"), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    # Save reconstruction sources to YAML
    sources_df = show_as_dataframe(mast_payload.reconstruction_sources)
    CSV.write(joinpath(dir, "process-stats", "reconstruct_meso-sources.csv"), sources_df)
    
    println("\nMeso reconstruction completed:")
    println("- Saved reconstructed data to $(output_filename)")
    println("- Saved updated sensors to reconstruct_meso-sensors.yaml")
    println("- Saved reconstruction sources to meso-reconstruction-sources.yaml")
    
    # Print reconstruction statistics
    total_reconstructions = length(mast_payload.reconstruction_sources)
    reconstructions_by_model = Dict{String,Int}()
    for source in mast_payload.reconstruction_sources
        reconstructions_by_model[source.model_id] = get(reconstructions_by_model, source.model_id, 0) + 1
    end
    
    println("\nReconstruction Statistics:")
    println("==========================")
    println("Total reconstructed points: $total_reconstructions")
    for (model_id, count) in sort(collect(reconstructions_by_model))
        println("- $model_id: $count points")
    end
end

end # module 