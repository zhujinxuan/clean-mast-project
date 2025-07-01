module Core

using CSV, DataFrames, Dates
using ...Types.WtTimeSeriesConfig: WtTimeSeriesConfiguration, WtTimeSeriesMast
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries
using ...Types.SensorColumns: find_nearest_height_sensor

export process_wt_timeseries

"""
    process_wt_timeseries(config::WtTimeSeriesConfiguration, project_dir::String)

Process wind turbine time series data for all masts in the configuration.

# Arguments
- `config::WtTimeSeriesConfiguration`: Configuration with masts and their target heights
- `project_dir::String`: Base project directory for resolving relative paths
"""
function process_wt_timeseries(config::WtTimeSeriesConfiguration, project_dir::String)
    println("Processing WT time series for $(length(config.masts)) mast(s)")
    
    for mast in config.masts
        process_single_mast(mast, project_dir)
    end
    
    println("\nWT time series processing completed successfully.")
end

"""
    process_single_mast(mast::WtTimeSeriesMast, project_dir::String)

Process wind turbine time series data for a single mast at all its target heights.

# Arguments
- `mast::WtTimeSeriesMast`: Mast configuration with input data and target heights
- `project_dir::String`: Base project directory for resolving relative paths
"""
function process_single_mast(mast::WtTimeSeriesMast, project_dir::String)
    println("\nProcessing mast: $(mast.name)")
    
    # Load time series data for this mast
    time_series = load_timeseries(mast.input, project_dir)
    
    if isempty(mast.target_heights)
        @warn "No target heights specified for mast $(mast.name). Skipping."
        return
    end
    
    println("Processing $(length(mast.target_heights)) target height(s): $(mast.target_heights)")
    
    for height in sort(mast.target_heights)
        println("\nProcessing height: $(height)m")
        process_single_height(mast.name, height, time_series, mast.output_dir, project_dir)
    end
end

"""
    process_single_height(mast_name::String, target_height::Float64, time_series::TimeSeriesData, 
                         output_dir::String, project_dir::String)

Process WT time series for a single height of a single mast.

# Arguments
- `mast_name::String`: Name of the mast
- `target_height::Float64`: Target height to process
- `time_series::TimeSeriesData`: Time series data with sensors
- `output_dir::String`: Output directory for CSV files
- `project_dir::String`: Base project directory for resolving relative paths
"""
function process_single_height(mast_name::String, target_height::Float64, time_series::TimeSeriesData, 
                              output_dir::String, project_dir::String)
    # Find WindSpeed sensor closest to target height with statType = "avg"
    wind_speed_sensor = find_nearest_height_sensor(target_height, time_series.sensors, "WindSpeed", "avg")
    if isnothing(wind_speed_sensor)
        @warn "No suitable WindSpeed sensor found near height $(target_height)m for mast $(mast_name). Skipping."
        return
    end
    
    # Find WindDirection sensor closest to target height with statType = "avg"
    wind_dir_sensor = find_nearest_height_sensor(target_height, time_series.sensors, "WindDirection", "avg")
    if isnothing(wind_dir_sensor)
        @warn "No suitable WindDirection sensor found near height $(target_height)m for mast $(mast_name). Skipping."
        return
    end
    
    println("- Selected sensors:")
    println("  Wind Speed: $(wind_speed_sensor.columnName) ($(wind_speed_sensor.height)m)")
    println("  Wind Direction: $(wind_dir_sensor.columnName) ($(wind_dir_sensor.height)m)")
    
    # Create a new DataFrame with only the required columns
    wt_df = DataFrame(
        timestamp = time_series.df.timestamp,
        wind_speed = time_series.df[:, wind_speed_sensor.columnName],
        wind_direction = time_series.df[:, wind_dir_sensor.columnName]
    )
    
    # Format timestamp to yyyy-mm-dd HH:MM:ss
    wt_df.timestamp = Dates.format.(wt_df.timestamp, "yyyy-mm-dd HH:MM:ss")
    
    # Save to CSV with height included in filename
    height_str = replace(string(target_height), "." => "_")
    output_filename = "$(mast_name)-$(height_str)m.csv"
    full_output_dir = joinpath(project_dir, output_dir)
    mkpath(full_output_dir)
    
    output_path = joinpath(full_output_dir, output_filename)
    CSV.write(output_path, wt_df)
    
    println("- Saved wind turbine time series data to $(joinpath(output_dir, output_filename))")
end

end # module Core 