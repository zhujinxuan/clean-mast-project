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
import .WindFrequency: analyze_all_frequency
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
    
    # Generate comprehensive Typst report
    @info "Generating comprehensive Typst report..."
    results["report_path"] = generate_comprehensive_report(config)
    
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

"""
    generate_comprehensive_report(config::AnalyzeConfig)

Generate a comprehensive Typst report that includes all individual Typst files
created by the various analysis modules for all masts.

# Arguments
- `config::AnalyzeConfig`: Analysis configuration with multiple masts

# Returns
- `String`: Path to the generated main Typst report file
"""
function generate_comprehensive_report(config::AnalyzeConfig)
    # Define the main report file path
    report_path = joinpath(config.output.path, "comprehensive_analysis_report.typ")
    
    @info "Generating comprehensive Typst report at: $report_path"
    
    # Open the main report file
    open(report_path, "w") do io
        # Write document header
        write(io, """
        // Comprehensive Wind Mast Analysis Report
        // Generated by CleanMastProject.jl
        // Date: $(Dates.format(now(), "yyyy-mm-dd HH:MM:SS"))
        
        #set document(
          title: "Wind Mast Comprehensive Analysis Report",
          author: "CleanMastProject Analysis System",
        )
        
        #set page(
          paper: "a4",
          margin: (x: 2cm, y: 2.5cm),
          numbering: "1",
          number-align: center,
        )
        
        #set heading(numbering: "1.")
        
        #set par(justify: true)
        
        // Title page
        #align(center)[
          #v(5cm)
          #text(size: 24pt, weight: "bold")[风能资源评估综合分析报告]
          
          #v(1cm)
          
          #text(size: 18pt)[Wind Resource Assessment Comprehensive Analysis Report]
          
          #v(2cm)
          
          #text(size: 14pt)[
            项目包含 $(length(config.masts)) 个测风塔数据分析
          ]
          
          #v(4cm)
          
          #text(size: 12pt)[
            生成日期: #datetime.today().display("[year]年[month]月[day]日")
          ]
        ]
        
        #pagebreak()
        
        // Table of contents
        #outline(
          title: [目录 / Table of Contents],
          indent: 1em,
          depth: 3,
        )
        
        #pagebreak()
        
        // Executive summary
        = 执行摘要 / Executive Summary
        
        本报告包含了 $(length(config.masts)) 个测风塔的综合风能资源分析结果，涵盖以下分析内容：
        
        - 风速时序分析 (Wind Speed Temporal Analysis)
        - 垂直风廓线分析 (Vertical Wind Profile Analysis)  
        - 风向频率分析 (Wind Direction Frequency Analysis)
        - 风玫瑰图分析 (Wind Rose Analysis)
        
        """)
        
        # Process each mast
        for (idx, mast) in enumerate(config.masts)
            write(io, """
            
            #pagebreak()
            
            = 测风塔 $(mast.name) 分析结果
            
            """)
            
            # Define the expected Typst files and their locations
            typst_files = [
                ("wind-temporal", "wind-temporal.typ"),
                ("wind-rose", "wind-rose.typ"),
                ("vertical-profile", "wind_shear_exponent_table.typ"),
                ("wind-power-frequency", "wind-frequency.typ"),
                ("weibull", "weibull.typ"),
                ("turbulence", "turbulence.typ")
            ]
            
            # Include each Typst file if it exists
            for (dir_name, file_name) in typst_files
                file_path = joinpath(get_output_path(config, mast.name, dir_name), file_name)
                
                if isfile(file_path)
                    # Calculate relative path from report location
                    rel_path = relpath(file_path, config.output.path)
                    # Convert Windows path separators to forward slashes for Typst
                    rel_path = replace(rel_path, "\\" => "/")
                    

                    write(io, """
                     #set heading(offset: $(config.output.docx.sectionLevel-1))
                    
                    #include "$(rel_path)"
                    
                    """)
                else
                    @warn "Typst file not found: $file_path"
                end
            end
            
            # Add page break between masts (except for the last one)
            if idx < length(config.masts)
                write(io, "\n#pagebreak()\n")
            end
        end
    end
    
    @info "Comprehensive Typst report generated successfully at: $report_path"
    
    return report_path
end

# Export main functions
export analyze_all, generate_comprehensive_report

end # module 