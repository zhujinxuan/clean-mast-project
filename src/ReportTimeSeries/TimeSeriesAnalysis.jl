module TimeSeriesAnalysis

using DataFrames
using CSV
using Statistics
using Dates
using ColorSchemes
using DataFramesMeta
using GLM
using StatsBase: mean, fit, Histogram
using YAML

using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path, AirDensityConfig

# Import functions from sub-modules
import ..WindTemporal: analyze_all_temporal
import ..Vertical: analyze_all_vertical
import ..WindFrequency: analyze_all_frequency
import ..WindRose: analyze_all_wind_rose
import ..Turbulence: analyze_all_turbulence
import ..Weibull: analyze_weibull_distribution
import ..FiftyYearsExtremeWind: analyze_fifty_years_extreme_wind

export analyze_all

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

    @info "Starting comprehensive time series analysis for $(length(config.masts)) mast(s)"

    # Create output directory
    mkpath(config.output.path)

    # Wind temporal analyses
    @info "Running wind temporal analyses..."
    results["temporal"] = analyze_all_temporal(config)

    # Vertical profile analyses
    @info "Running vertical profile analyses..."
    results["vertical"] = analyze_all_vertical(config)

    # Wind frequency analyses
    @info "Running wind frequency analyses..."
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

    # 50-year extreme wind analysis
    @info "Running 50-year extreme wind analysis..."
    results["fifty_years_extreme"] = analyze_fifty_years_extreme_wind(config)

    @info "Analysis complete for all masts"

    return results
end

end # module