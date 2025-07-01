module CommandReconstructMeso

using CSV, YAML, DataFrames
using JLD2
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, save_timeseries
using ...Types.Utils: from_dict, show_as_dataframe
using ...CleanMastUtils: load_dict
using ...Types.MastReferenceModel: ReconstructionPayload, AbstractMastReferenceModel
using ..Core: merge_reconstruct_meso
using ...TimeSeriesProcessing.TimeRangeProcessor: TimeRange

export execute

"""
    load_model(model_path::String)::AbstractMastReferenceModel

Load a trained model from JLD2 file.

# Arguments
- `model_path::String`: Full path to the model JLD2 file

# Returns
- The loaded model
"""
function load_model(model_path::String)::AbstractMastReferenceModel
    if !isfile(model_path)
        error("Model file not found: $model_path")
    end
    
    # Load model from JLD2
    @load model_path model
    return model
end

"""
    execute(config_path::String)

Execute mesoscale reconstruction based on configuration file.

# Arguments
- `config_path::String`: Path to reconstruct-meso.toml configuration file
"""
function execute(config_path::String)
    println("Processing mesoscale reconstruction...")
    
    # Load configuration
    config_dict = load_dict(config_path)
    config = from_dict(ReconstructMesoConfiguration, config_dict)
    project_dir = dirname(config_path)
    
    # Load all meso data sources
    meso_data = Dict{String, TimeSeriesData}(
        map(
            meso_source -> (meso_source.name => load_timeseries(meso_source.input, project_dir)),
            config.mesos
        )
    )
    
    # Process each mast configuration
    for mast_config in config.masts
        println("\nProcessing reconstruction for $(mast_config.name)...")
        
        # Load mast time series data
        mast_ts = load_timeseries(mast_config.input, project_dir)
        
        # Get meso data for windspeed and winddirection models
        ws_meso_name = mast_config.models.windspeed.meso_name
        wd_meso_name = mast_config.models.winddirection.meso_name
        
        # Use the same meso data if both models use the same source
        meso_ws_ts = meso_data[ws_meso_name]
        meso_wd_ts = meso_data[wd_meso_name]
        
        # Create initial reconstruction payload
        mast_payload = ReconstructionPayload(mast_ts, [])
        
        # Load and apply wind speed model
        ws_model_path = joinpath(project_dir, mast_config.models.windspeed.model_file)
        println("  Loading wind speed model: $(mast_config.models.windspeed.method)")
        ws_model = load_model(ws_model_path)
        mast_payload = merge_reconstruct_meso(mast_payload, meso_ws_ts, ws_model, mast_config.time_range)
        
        # Load and apply wind direction model
        wd_model_path = joinpath(project_dir, mast_config.models.winddirection.model_file)
        println("  Loading wind direction model: $(mast_config.models.winddirection.method)")
        wd_model = load_model(wd_model_path)
        mast_payload = merge_reconstruct_meso(mast_payload, meso_wd_ts, wd_model, mast_config.time_range)
        
        # Save results
        save_timeseries(mast_config.output, project_dir, mast_payload.data)
        
        # Save reconstruction sources to CSV
        sources_df = show_as_dataframe(mast_payload.reconstruction_sources)
        sources_filename = "reconstruct-meso-sources-$(mast_config.name).csv"
        sources_output_path = joinpath(project_dir, "process-stats", sources_filename)
        mkpath(dirname(sources_output_path))
        CSV.write(sources_output_path, sources_df)
        
        # Print reconstruction statistics
        total_reconstructions = length(mast_payload.reconstruction_sources)
        reconstructions_by_model = Dict{String,Int}()
        for source in mast_payload.reconstruction_sources
            reconstructions_by_model[source.model_id] = get(reconstructions_by_model, source.model_id, 0) + 1
        end
        
        println("\n  Reconstruction Statistics for $(mast_config.name):")
        println("  ==========================================")
        println("  Total reconstructed points: $total_reconstructions")
        for (model_id, count) in sort(collect(reconstructions_by_model))
            println("  - $model_id: $count points")
        end
        
        println("\n  Output saved to:")
        println("  - Data: $(mast_config.output.data)")
        println("  - Sensors: $(mast_config.output.sensors)")
        println("  - Sources: process-stats/$(sources_filename)")
    end
    
    println("\nMesoscale reconstruction completed successfully.")
end

end # module 