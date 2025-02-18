module AnalyzeTimeSeriesCommand

using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.CleanMastConfig: ProjectConfig
using ...CleanMastConfig: parse_config
using ...AnalyzeTimeSeries: analyze_all
using CSV
using YAML
using DataFrames
using Dates
using ...Types.Utils: from_dict

"""
Load time series data from CSV and YAML files
"""
function load_timeseries(project_dir::String, data_file::String, sensors_file::String)::Union{TimeSeriesData, Nothing}
    data_path = joinpath(project_dir, data_file)
    sensors_path = joinpath(project_dir, sensors_file)
    
    # Check if files exist
    if !isfile(data_path) || !isfile(sensors_path)
        return nothing
    end
    
    # Read data and sensors
    df = CSV.read(data_path, DataFrame)
    sensors_yaml = YAML.load_file(sensors_path)
    sensors = [from_dict(SensorColumn, Dict{String,Any}(s)) for s in sensors_yaml["sensors"]]
    
    return TimeSeriesData(df, sensors)
end

"""
Process a specific time series type and save results to output directory
"""
function process_timeseries(project_dir::String, config::ProjectConfig, timeseries_type::String)
    # Define input paths based on time series type
    original_filename = config.mast.data_path
    data_paths = Dict(
        "tower-shading" => "tower_shading.$(original_filename).csv",
        "reconstruct-single" => "reconstruct_single_mast.$(original_filename).csv",
        "reconstruct-meso" => "reconstruct_meso.$(original_filename).csv",
        "representative-year" => "rep_year_calibration.$(original_filename).csv"
    )
    
    sensor_paths = Dict(
        "tower-shading" => "tower-shading-sensors.yaml",
        "reconstruct-single" => "reconstruct_single_mast-sensors.yaml",
        "reconstruct-meso" => "reconstruct_meso-sensors.yaml",
        "representative-year" => "rep_year_calibration-sensors.yaml"
    )
    
    # Find matching data file
    data_file =  data_paths[timeseries_type]
    
    # Load time series data
    time_series = load_timeseries(project_dir, data_file, sensor_paths[timeseries_type])
    
    if isnothing(time_series)
        @warn "Skipping $timeseries_type analysis: Failed to load data or sensors"
        return nothing
    end
    
    # Create output directory
    output_dir = joinpath(project_dir, "analysis", timeseries_type)
    mkpath(output_dir)
    
    # Analyze data
    @info "Analyzing $timeseries_type"
    analyze_all(time_series, output_dir)
    @info "Completed analysis for $timeseries_type"
end

"""
Main entry point for analyze time series command
"""
function execute(project_dir::String)
    
    # Create main analysis directory
    mkpath(joinpath(project_dir, "analysis"))
    config = parse_config(project_dir)
    
    # Process each time series type
    timeseries_types = [
        "tower-shading",
        "reconstruct-single",
        "reconstruct-meso",
        "representative-year"
    ]
    
    for ts_type in timeseries_types
        process_timeseries(project_dir, config, ts_type)
    end
    
    return 0
end

end # module 