module ReconstructMeso

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.Utils: from_dict, to_dict, show_as_dataframe
using ...Types.SensorColumns: SensorColumn
using ...CleanMastUtils: load_dict
using ...Types.MastReferenceModel: ReconstructionPayload
using ...ReconstructMeso: merge_reconstruct_meso
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using ...Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel
using ...TimeSeriesProcessing.TimeRangeProcessor: calculate_reconstruction_time_range
using ..TrainMesoModel: load_model

export execute

function execute(dir::String)
    # Parse config
    config = parse_config(dir)
    
    # Read reconstructed mast data from single mast reconstruction
    mast_name = config.mast.name
    reconstructed_filename = "reconstruct_single_mast/$(mast_name).csv"
    reconstructed_filepath = joinpath(dir, reconstructed_filename)
    
    if !isfile(reconstructed_filepath)
        error("Reconstructed mast data file not found: $reconstructed_filepath")
    end
    
    # Read sensors from YAML
    sensors_filepath = joinpath(dir, "reconstruct_single_mast/$(mast_name).sensors.yaml")
    if !isfile(sensors_filepath)
        error("Reconstructed mast sensors file not found: $sensors_filepath")
    end
    
    # Read mast data and sensors
    mast_df = CSV.read(reconstructed_filepath, DataFrame)
    sensors_dict = load_dict(sensors_filepath)
    mast_sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_dict["sensors"]]
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    
    # Read meso data from raw files
    meso_name = config.meso.name
    meso_filepath = joinpath(dir, "raw/$(meso_name).csv")
    if !isfile(meso_filepath)
        error("Raw meso data file not found: $meso_filepath. Please run 'project parse-sensors' first.")
    end
    
    # Read meso sensors from raw TOML file
    meso_sensors_filepath = joinpath(dir, "raw/$(meso_name).sensors.toml")
    if !isfile(meso_sensors_filepath)
        error("Raw meso sensors file not found: $meso_sensors_filepath. Please run 'project parse-sensors' first.")
    end
    
    # Read meso data and sensors
    meso_df = CSV.read(meso_filepath, DataFrame)
    meso_sensors_dict = load_dict(meso_sensors_filepath)
    meso_sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in meso_sensors_dict["sensors"]]
    meso_ts = TimeSeriesData(meso_df, meso_sensors)
    
    # Get time range from config or use full range
    time_range = calculate_reconstruction_time_range(mast_ts, config.analysis.time_range)
    
    # Create initial reconstruction payload
    mast_payload = ReconstructionPayload(mast_ts, [])
    
    # Load and apply 1-sector wind speed model
    println("Reconstructing wind speeds using 1-sector model...")
    model_1sector = load_model(dir, SectorizedRegressionModel, "1-sector", "meso", "era5")
    mast_payload = merge_reconstruct_meso(mast_payload, meso_ts, model_1sector, time_range)
    
    # Load and apply direction offset model
    println("Reconstructing wind directions using constant offset model...")
    model_direction = load_model(dir, DirectionOffsetModel, "constant-direction-offset", "meso", "era5")
    mast_payload = merge_reconstruct_meso(mast_payload, meso_ts, model_direction, time_range)
    
    # Save reconstructed data
    output_filename = "reconstruct_meso/$(mast_name).csv"
    mkpath(dirname(joinpath(dir, output_filename)))
    CSV.write(joinpath(dir, output_filename), mast_payload.data.df)
    
    # Save updated sensors to YAML
    sensors_output_path = "reconstruct_meso/$(mast_name).sensors.yaml"
    sensors_yaml = Dict(
        "sensors" => map(to_dict, mast_payload.data.sensors)
    )
    open(joinpath(dir, sensors_output_path), "w") do io
        YAML.write(io, sensors_yaml)
    end
    
    # Save reconstruction sources to CSV
    sources_df = show_as_dataframe(mast_payload.reconstruction_sources)
    sources_output_path = "process-stats/reconstruct_meso-sources.csv"
    mkpath(dirname(joinpath(dir, sources_output_path)))
    CSV.write(joinpath(dir, sources_output_path), sources_df)
    
    println("\nMeso reconstruction completed:")
    println("- Saved reconstructed data to $(output_filename)")
    println("- Saved updated sensors to $(sensors_output_path)")
    println("- Saved reconstruction sources to $(sources_output_path)")
    
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