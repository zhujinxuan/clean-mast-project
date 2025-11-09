module WindFrequency

using DataFrames
using CSV
using AlgebraOfGraphics, CairoMakie
using Statistics
using StatsBase: fit, Histogram
using SummaryTables

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.ReportTimeSeriesConfiguration: ReportTimeSeriesConfig, MastReportTimeSeriesConfig, get_output_path, AirDensityConfig
import ..AirDensity: calculate_air_density, calculate_wind_power_density
import ..Utils: format_height

struct MastOneHeightStats
    height :: Float64
    data :: DataFrame
end

"""
    calculate_wind_power_frequency_stats(config::ReportTimeSeriesConfig)

Calculate wind power frequency distribution statistics across wind speed bins for all masts.
Returns the statistical data without creating plots or saving files.
"""
function calculate_wind_power_frequency_stats(config::ReportTimeSeriesConfig) :: Dict{String, Vector{MastOneHeightStats}}
    results = Dict{String, Vector{MastOneHeightStats}}()
    
    for mast in config.masts
        # Skip power analysis if air density is not configured
        if isnothing(mast.airDensity)
            @info "Skipping power frequency analysis for mast $(mast.name) - no air density configured"
            continue
        end
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        sort!(speed_sensors, by = s -> s.height, rev=true)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Define wind speed bins (0 to 28 m/s, 1 m/s increments)
        bins = 0:1:28
        bin_centers = 0.5:1:27.5
        
        mast_results = map(speed_sensors) do sensor
            # Calculate air density at sensor height
            air_density = calculate_air_density(sensor.height, mast.airDensity)
            
            # Get wind speed data for this sensor
            wind_speeds = collect(skipmissing(mast.timeSeriesData.df[:, sensor.columnName]))
            
            # Calculate wind power for each observation
            wind_powers = calculate_wind_power_density.(wind_speeds, air_density)
            
            # Create histogram of wind speeds
            hist_counts = fit(Histogram, wind_speeds, bins).weights
            frequency = hist_counts ./ sum(hist_counts)
            
            # Calculate power contribution in each bin
            power_in_bins = zeros(length(bins)-1)
            total_power = sum(wind_powers)
            
            for (i, speed) in enumerate(wind_speeds)
                bin_idx = min(floor(Int, speed) + 1, length(bins)-1)
                power_in_bins[bin_idx] += wind_powers[i]
            end
            
            # Calculate power frequency (ratio of bin power to total power)
            power_frequency = power_in_bins ./ total_power
            
            # Create DataFrames for results
            results_df = DataFrame(
                bin_start = bins[1:end-1],
                bin_end = bins[2:end],
                bin_center = bin_centers,
                frequency = frequency,
                power_frequency = power_frequency
            )
            
             MastOneHeightStats(sensor.height, results_df)
        end
        
        results[mast.name] = mast_results
    end

    return results
end

"""
    create_wind_power_frequency_plots(config::ReportTimeSeriesConfig, frequency_stats::Dict)

Create wind power frequency plots and save CSV files based on pre-calculated statistics.
"""
function create_wind_power_frequency_plots(config::ReportTimeSeriesConfig, frequency_stats::Dict{String, Vector{MastOneHeightStats}})
    for mast in config.masts
        if !haskey(frequency_stats, mast.name)
            continue
        end
        
        output_dir = get_output_path(config, mast.name, "wind-power-frequency")
        mast_results = frequency_stats[mast.name]
        
        for (mast_one_height_stats) in mast_results
            height = mast_one_height_stats.height
            results_df = mast_one_height_stats.data
            
            # Save to CSV
            height_str = format_height(height)
            CSV.write(joinpath(output_dir, "wind_power_frequency_$(height_str)m.csv"), results_df)
            
            # Create a combined plot with both frequency distributions
            # First reshape the data for grouped bar plot
            plot_df = DataFrame(
                bin_center = repeat(results_df.bin_center, 2),
                value = [results_df.frequency; results_df.power_frequency],
                type = repeat(["Wind Speed Frequency", "Wind Power Frequency"], inner=length(results_df.bin_center))
            )
            
            # Find the maximum wind speed with non-zero frequency
            max_nonzero_speed = maximum(plot_df[plot_df.value .> 0, :bin_center])
            # Set x-axis limit: use data max + 1, but cap at 25 m/s
            x_max = min(max_nonzero_speed + 1, 25.0)
            
            # Create the plot using AlgebraOfGraphics with custom colors
            plt = data(plot_df) * 
                  mapping(:bin_center, :value, dodge=:type, color=:type) * 
                  visual(BarPlot)
            
            # Create figure with limited x-axis range
            fig = draw(plt, axis=(
                xlabel="Wind Speed (m/s)",
                ylabel="Frequency", 
                title="Wind Speed and Power Frequency Distribution - $(mast.name) ($(height_str)m)",
                limits=(0, x_max, nothing, nothing),  # Set x-limits directly
                xticks=0:2:Int(ceil(x_max))
            ))
            
            # Save the plot
            save(joinpath(output_dir, "wind_frequency_distribution_$(height_str)m.svg"), fig)

            @info "Generated wind power frequency plots for mast $(mast.name) at $(height_str)m"
        end
    end
    
    return nothing
end

"""
    analyze_wind_power_frequency(config::ReportTimeSeriesConfig)

Analyze wind power frequency distribution across wind speed bins for all masts.
This function combines statistical calculation and plotting.
"""
function analyze_wind_power_frequency(config::ReportTimeSeriesConfig)
    # Calculate statistics
    frequency_stats = calculate_wind_power_frequency_stats(config)
    
    # Create plots and save files
    create_wind_power_frequency_plots(config, frequency_stats)
    
    return frequency_stats
end

"""
    analyze_all_frequency(config::ReportTimeSeriesConfig)

Run all wind direction frequency analyses for all masts in the configuration.
"""
function analyze_all_frequency(config::ReportTimeSeriesConfig)
    results = analyze_wind_power_frequency(config)
    generate_wind_frequency_report(config)
    return results
end

"""
    create_wind_frequency_tables(config::ReportTimeSeriesConfig)

Create wind frequency tables using SummaryTables.jl and export to Typst format.
Includes wind speed frequency and wind power frequency tables for heights >= 120m.
Saves all results to "./wind-frequency.typ"
"""
function generate_wind_frequency_report(config::ReportTimeSeriesConfig)
    # First run the wind power frequency stats calculation to get the data
    frequency_results = calculate_wind_power_frequency_stats(config)
    
    
    for mast in config.masts
        # Create/clear the output file
        output_dir = get_output_path(config, mast.name, "wind-power-frequency")
        typst_file = joinpath(output_dir, "wind-frequency.typ")
        if isfile(typst_file)
            rm(typst_file)
        end
        
        open(typst_file, "w") do io
            println(io, "// Wind Frequency Analysis Tables")
            println(io, "// Generated by WindFrequency.jl")
            println(io, "== 风速频率分析")
            println(io, "")
        end
        if !haskey(frequency_results, mast.name)
            continue
        end
        
        mast_results = frequency_results[mast.name]
        
        # Filter for heights >= min_plot_height
        valid_data = filter(data -> data.height >= config.min_plot_height, mast_results)

        
        # Create wind speed frequency table
        speed_freq_table = create_wind_speed_frequency_table(valid_data)
        
        # Create wind power frequency table  
        power_freq_table = create_wind_power_frequency_table(valid_data)
        
        # Create wind range summary table (3-25 m/s)
        range_summary_table = create_wind_range_summary_table(valid_data)
        
        # Append to typst file
        open(typst_file, "a") do io
            println(io, "")
            println(io, "== 测风塔$(mast.name)风速频率分析")
            println(io, "")
            println(io, "表格：$(mast.name) 风速频率表")
            println(io, "")
            show(io, MIME"text/typst"(), speed_freq_table)
            println(io, "")
            println(io, "")
            println(io, "表格：$(mast.name) 风功率频率表")
            println(io, "")
            show(io, MIME"text/typst"(), power_freq_table)
            println(io, "")
            println(io, "")
            println(io, "表格：$(mast.name) 风速区间3-25m/s统计汇总表")
            println(io, "")
            show(io, MIME"text/typst"(), range_summary_table)
            println(io, "")
            println(io, "")
            
            # Add wind frequency distribution plots for each height
            println(io, "== 风速与风功率频率分布图")
            for mast_one_height_data in valid_data
                height = mast_one_height_data.height
                height_str = format_height(height)
                svg_filename = "wind_frequency_distribution_$(height_str)m.svg"
                svg_path = joinpath(output_dir, svg_filename)
                
                if isfile(svg_path)
                    println(io, "")
                    println(io, "=== $(height_str)m 高度风速与风功率频率分布")
                    println(io, "")
                    println(io, "#figure(")
                    println(io, "  image(\"$svg_filename\", width: 90%),")
                    println(io, "  caption: [$(height_str)m 高度风速与风功率频率分布图]")
                    println(io, ")")
                    println(io, "")
                end
            end
        end
        
        @info "Generated wind frequency tables for mast $(mast.name) with heights >= 120m"
        @info "Wind frequency tables saved to $(typst_file)"
    end
end

"""
    create_wind_speed_frequency_table(valid_data::Dict, heights::Vector{Float64}, mast_name::String)

Create a wind speed frequency table with wind speed ranges and occurrence hours.
"""
function create_wind_speed_frequency_table(valid_data::Vector{MastOneHeightStats})
    # Get data from the first height to establish bins
    first_data = first(valid_data).data
    
    # Create base DataFrame with wind speed ranges
    table_df = DataFrame(
        风速区间 = ["$(Int(row.bin_start))-$(Int(row.bin_end))" for row in eachrow(first_data)]
    )
    
    # Add columns for each height >= min_plot_height
    for mast_one_height_data in valid_data
        height = mast_one_height_data.height
        height_str = format_height(height)

        # Wind speed frequency percentage
        freq_col = "$(height_str)m频率"
        table_df[!, freq_col] = ["$(round(row.frequency * 100, digits=2))%" for row in eachrow(mast_one_height_data.data)]

        # Occurrence hours (8760 * frequency)
        hours_col = "$(height_str)m小时数"
        table_df[!, hours_col] = [round(Int, row.frequency * 8760) for row in eachrow(mast_one_height_data.data)]
    end
    
    # Create SummaryTables table
    return simple_table(table_df)
end

"""
    create_wind_power_frequency_table(valid_data::Vector{MastOneHeightStats})

Create a wind power frequency table with wind speed ranges and power frequency percentages.
"""
function create_wind_power_frequency_table(valid_data::Vector{MastOneHeightStats})
    # Get data from the first height to establish bins
    first_data = first(valid_data).data
    
    # Create base DataFrame with wind speed ranges
    table_df = DataFrame(
        风速区间 = ["$(Int(row.bin_start))-$(Int(row.bin_end))" for row in eachrow(first_data)]
    )
    
    # Add columns for each height >= min_plot_height
    for mast_one_height_data in valid_data
        height = mast_one_height_data.height
        height_str = format_height(height)

        # Wind power frequency percentage
        power_freq_col = "$(height_str)m功率频率"
        table_df[!, power_freq_col] = ["$(round(row.power_frequency*100, digits=1))%" for row in eachrow(mast_one_height_data.data)]

        # Wind power density for each bin (calculate average power density for each bin)
        power_hours_col = "$(height_str)m功率出现小时数"
        table_df[!, power_hours_col] = [round(Int, row.power_frequency .* 8760) for row in eachrow(mast_one_height_data.data)]
    end
    
    # Create SummaryTables table
    return simple_table(table_df)
end

"""
    create_wind_range_summary_table(valid_data::Vector{MastOneHeightStats})

Create a summary table for wind speed range 3-25m/s showing frequency and hours for each height >= 120m.
Includes 风速频率, 风速出现小时数, 风能频率, 风能出现小时数.
"""
function create_wind_range_summary_table(valid_data::Vector{MastOneHeightStats})
    # Create summary data for each height
    summary_data = map(valid_data) do mast_one_height_data
        height = mast_one_height_data.height
        data = mast_one_height_data.data
        
        # Filter for wind speed range 3-25 m/s (bin_start >= 3 and bin_end <= 25)
        range_data = filter(row -> row.bin_start >= 3 && row.bin_end <= 25, data)
        
        # Sum frequencies for the range
        total_wind_freq = sum(range_data.frequency)
        total_power_freq = sum(range_data.power_frequency)
        
        # Calculate hours
        wind_hours = round(Int, total_wind_freq * 8760)
        power_hours = round(Int, total_power_freq * 8760)
        
        (
            height = "$(format_height(height))m",
            wind_freq = "$(round(total_wind_freq * 100, digits=2))%",
            wind_hours = wind_hours,
            power_freq = "$(round(total_power_freq * 100, digits=1))%",
            power_hours = power_hours
        )
    end
    
    # Create DataFrame for the table
    table_df = DataFrame(
        高度 = [data.height for data in summary_data],
        风速频率 = [data.wind_freq for data in summary_data],
        风速出现小时数 = [data.wind_hours for data in summary_data],
        风能频率 = [data.power_freq for data in summary_data],
        风能出现小时数 = [data.power_hours for data in summary_data]
    )
    
    return simple_table(table_df)
end

export analyze_wind_power_frequency, analyze_all_frequency, create_wind_frequency_tables,
       calculate_wind_power_frequency_stats, create_wind_power_frequency_plots

end # module 