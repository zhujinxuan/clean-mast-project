module CommandRepresentativeYear

using CSV, YAML, DataFrames
using JLD2
using ...Types.RepresentativeYearConfig: RepresentativeYearConfiguration
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange, load_timeseries, save_timeseries
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ...Types.MastReferenceModel: AbstractMastReferenceModel
using ..Core: calibrate_to_representative_year

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

Execute representative year calibration based on configuration file.

# Arguments
- `config_path::String`: Path to representative-year.toml configuration file
"""
function execute(config_path::String)
    println("Processing representative year calibration...")
    
    # Load configuration
    config_dict = load_dict(config_path)
    config = from_dict(RepresentativeYearConfiguration, config_dict)
    project_dir = dirname(config_path)
    
    # Load all meso data sources
    meso_data = Dict{String, TimeSeriesData}(
        map(config.mesos) do meso_source
            return meso_source.name => load_timeseries(meso_source.input, project_dir)
        end
    )
    
    # Process each mast calibration
    for mast_config in config.masts
        println("\nProcessing calibration for $(mast_config.name)...")
        
        # Load mast time series data
        mast_ts = load_timeseries(mast_config.input, project_dir)
        
        # Get meso data based on model specification
        meso_name = mast_config.meso_model.meso_name
        meso_ts = meso_data[meso_name]
        
        # Load 16-sector wind speed model
        model_path = joinpath(project_dir, mast_config.meso_model.model_file)
        println("  Loading model: $(mast_config.meso_model.method)")
        model = load_model(model_path)
        
        # Perform calibration
        println("  Performing representative year calibration...")
        result, calibration_info = calibrate_to_representative_year(
            mast_ts, 
            meso_ts, 
            mast_config.time_range, 
            model
        )
        
        # Save results
        save_timeseries(mast_config.output, project_dir, result)
        
        # Save calibration info if available
        if calibration_info !== nothing
            println("  Calibration completed:")
            println("  - Reference year starts at: $(calibration_info.reference_year)")
            println("  - Calibrated $(length(calibration_info.calibrations)) wind speed sensors")
        else
            println("  No calibration needed - meso data is already representative")
        end
        
        println("\n  Output saved to:")
        println("  - Data: $(mast_config.output.data)")
        println("  - Sensors: $(mast_config.output.sensors)")
    end
    
    println("\nRepresentative year calibration completed successfully.")
end

end # module 