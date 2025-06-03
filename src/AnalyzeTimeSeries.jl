module AnalyzeTimeSeries

using DataFrames
using CSV
using Gadfly
using Statistics
using Dates
using ColorSchemes
using DataFramesMeta
using GLM
using StatsBase: mean, fit, Histogram
using Compose
using YAML

import ..Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ..Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path, AirDensityConfig

# Include sub-modules for different analysis types
include("AnalyzeTimeSeries/AirDensity.jl")
include("AnalyzeTimeSeries/WindTemporal.jl")
include("AnalyzeTimeSeries/Vertical.jl")
include("AnalyzeTimeSeries/WindFrequency.jl")
include("AnalyzeTimeSeries/WindRose.jl")
include("AnalyzeTimeSeries/Turbulence.jl")
include("AnalyzeTimeSeries/Weibull.jl")

# Import specific functions from sub-modules
import .WindTemporal: analyze_wind_speed_timeseries, analyze_daily_pattern, 
                     analyze_monthly_pattern, analyze_monthly_daily_wind,
                     analyze_monthly_daily_windpower, analyze_all_temporal
import .Vertical: analyze_vertical_profile, analyze_wind_shear, analyze_all_vertical
import .WindFrequency: analyze_wind_power_frequency, analyze_wind_energy_content, 
                      analyze_all_frequency
import .WindRose: analyze_wind_rose, analyze_all_wind_rose
import .Turbulence: analyze_turbulence_intensity, analyze_all_turbulence
import .Weibull: analyze_weibull_distribution

"""
    analyze_all(config::AnalyzeConfig)

Run all available analyses for all masts in the configuration.

# Arguments
- `config::AnalyzeConfig`: Analysis configuration with multiple masts

# Returns
- `Dict{String, Any}`: Dictionary with results from all analyses
"""
function analyze_all(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    @info "Starting comprehensive analysis for $(length(config.masts)) mast(s)"
    
    # Wind temporal analyses (time series, daily, monthly patterns)
    @info "Running temporal wind analyses..."
    results["temporal"] = analyze_all_temporal(config)
    
    # Vertical profile analyses
    @info "Running vertical profile analyses..."
    results["vertical"] = analyze_all_vertical(config)
    
    # Wind direction frequency analyses
    @info "Running wind direction frequency analyses..."
    results["frequency"] = analyze_all_frequency(config)
    
    # Wind rose analyses
    @info "Running wind rose analyses..."
    results["windrose"] = analyze_all_wind_rose(config)
    
    # Turbulence intensity analyses
    @info "Running turbulence intensity analyses..."
    results["turbulence"] = analyze_all_turbulence(config)
    
    # Weibull distribution analysis
    @info "Running Weibull distribution analysis..."
    results["weibull"] = analyze_weibull_distribution(config)
    
    @info "Analysis complete for all masts"
    
    return results
end

"""
    analyze_all(data::TimeSeriesData, output_dir::String, air_density_config::AirDensityConfig)

Legacy function to maintain backward compatibility.
Run all analysis functions on a single time series dataset.

# Arguments
- `data::TimeSeriesData`: Time series data for a single mast
- `output_dir::String`: Output directory for results
- `air_density_config::AirDensityConfig`: Air density configuration

This function is maintained for backward compatibility but it's recommended
to use the new AnalyzeConfig-based approach for better flexibility.
"""
function analyze_all(data::TimeSeriesData, output_dir::String, air_density_config::AirDensityConfig)
    @warn "Using legacy analyze_all function. Consider using AnalyzeConfig-based approach for better flexibility."
    
    # Create legacy sub-directories
    analyze_wind_speed_timeseries_legacy(data, output_dir)
    analyze_daily_pattern_legacy(data, output_dir, air_density_config)
    analyze_vertical_profile_legacy(data, output_dir)
    analyze_monthly_pattern_legacy(data, output_dir, air_density_config)
    analyze_monthly_daily_wind_legacy(data, output_dir)
    analyze_monthly_daily_windpower_legacy(data, output_dir, air_density_config)
    analyze_weibull_distribution(data, joinpath(output_dir, "weibull"))
    analyze_wind_power_frequency_legacy(data, output_dir, air_density_config)
end

# Legacy function implementations (simplified versions that work with single mast data)
function analyze_wind_speed_timeseries_legacy(data::TimeSeriesData, output_dir::String)
    # Implementation moved to WindTemporal module
    # This is a wrapper for backward compatibility
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Prepare plotting data
    plot_df = select(data.df, :timestamp)
    for sensor in speed_sensors
        plot_df[!, "$(sensor.height)m"] = data.df[:, sensor.columnName]
    end
    
    # Save to CSV
    CSV.write(joinpath(output_dir, "wind_speed_timeseries.csv"), plot_df)
    
    return plot_df
end

# Export main functions
export analyze_all

end # module 