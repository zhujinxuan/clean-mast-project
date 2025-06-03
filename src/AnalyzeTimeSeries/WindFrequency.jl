module WindFrequency

using DataFrames
using CSV
using Gadfly
using Statistics
using StatsBase: fit, Histogram

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, to_air_density_config, get_output_path, AirDensityConfig
import ..AirDensity: calculate_air_density, calculate_wind_power_density

"""
    analyze_wind_power_frequency(config::AnalyzeConfig)

Analyze wind power frequency distribution across wind speed bins for all masts.
"""
function analyze_wind_power_frequency(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-power-frequency")
        air_density_config = to_air_density_config(mast.airDensity)
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Define wind speed bins (0 to 28 m/s, 1 m/s increments)
        bins = 0:1:28
        bin_centers = 0.5:1:27.5
        
        mast_results = Dict{String, Any}()
        
        for sensor in speed_sensors
            # Calculate air density at sensor height
            air_density = calculate_air_density(sensor.height, air_density_config)
            
            # Get wind speed data for this sensor
            wind_speeds = collect(skipmissing(mast.timeSeriesData.df[:, sensor.columnName]))
            
            # Skip if no valid data
            if isempty(wind_speeds)
                @warn "No valid wind speed data for sensor at $(sensor.height)m in mast $(mast.name)"
                continue
            end
            
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
                power_frequency = power_frequency,
                cumulative_frequency = cumsum(frequency),
                cumulative_power_frequency = cumsum(power_frequency)
            )
            
            # Calculate statistics
            mean_wind_speed = mean(wind_speeds)
            mean_power_density = mean(wind_powers)
            total_hours = length(wind_speeds)
            
            stats_df = DataFrame(
                parameter = ["mean_wind_speed", "mean_power_density", "total_hours", "air_density"],
                value = [mean_wind_speed, mean_power_density, total_hours, air_density],
                unit = ["m/s", "W/m²", "hours", "kg/m³"]
            )
            
            # Save to CSV
            CSV.write(joinpath(output_dir, "wind_power_frequency_$(sensor.height)m.csv"), results_df)
            CSV.write(joinpath(output_dir, "wind_power_frequency_stats_$(sensor.height)m.csv"), stats_df)
            
            # Create a combined plot with both frequency distributions
            # First reshape the data for grouped bar plot
            plot_df = DataFrame(
                bin_center = repeat(bin_centers, 2),
                value = [frequency; power_frequency],
                type = repeat(["Wind Speed Frequency", "Wind Power Frequency"], inner=length(bin_centers))
            )
            
            p_combined = plot(plot_df,
                x=:bin_center, y=:value, color=:type, group=:type,
                Geom.bar(position=:dodge),
                Guide.title("Wind Speed and Power Frequency Distribution - $(mast.name) ($(sensor.height)m)"),
                Guide.xlabel("Wind Speed (m/s)"),
                Guide.ylabel("Frequency"),
                Scale.color_discrete_manual(colorant"steelblue", colorant"darkred"),
                Theme(background_color="white")
            )
            
            draw(SVG(joinpath(output_dir, "wind_frequency_distribution_$(sensor.height)m.svg"), 12inch, 7inch), p_combined)
            
            # Create cumulative distribution plot
            p_cumulative = plot(
                layer(results_df, x=:bin_center, y=:cumulative_frequency, 
                      Geom.line(), Theme(default_color=colorant"steelblue")),
                layer(results_df, x=:bin_center, y=:cumulative_power_frequency, 
                      Geom.line(), Theme(default_color=colorant"darkred")),
                Guide.title("Cumulative Distribution - $(mast.name) ($(sensor.height)m)"),
                Guide.xlabel("Wind Speed (m/s)"),
                Guide.ylabel("Cumulative Frequency"),
                Guide.manual_color_key("", ["Wind Speed", "Wind Power"], 
                                     [colorant"steelblue", colorant"darkred"]),
                Theme(background_color="white")
            )
            
            draw(SVG(joinpath(output_dir, "cumulative_distribution_$(sensor.height)m.svg"), 10inch, 6inch), p_cumulative)
            
            mast_results["$(sensor.height)m"] = Dict(
                "data" => results_df,
                "stats" => stats_df
            )
            @info "Generated wind power frequency analysis for mast $(mast.name) at $(sensor.height)m"
        end
        
        results[mast.name] = mast_results
    end
    
    return results
end

"""
    analyze_wind_energy_content(config::AnalyzeConfig)

Analyze wind energy content by wind speed bins for all masts.
Shows which wind speeds contribute most to total energy production.
"""
function analyze_wind_energy_content(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-power-frequency")
        air_density_config = to_air_density_config(mast.airDensity)
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            continue
        end
        
        # Define wind speed bins
        bins = 0:1:28
        bin_centers = 0.5:1:27.5
        
        mast_results = Dict{String, Any}()
        
        for sensor in speed_sensors
            # Calculate air density at sensor height
            air_density = calculate_air_density(sensor.height, air_density_config)
            
            # Get wind speed data
            wind_speeds = collect(skipmissing(mast.timeSeriesData.df[:, sensor.columnName]))
            
            if isempty(wind_speeds)
                continue
            end
            
            # Calculate energy content per bin
            energy_by_bin = zeros(length(bins)-1)
            hours_by_bin = zeros(length(bins)-1)
            
            for speed in wind_speeds
                bin_idx = min(floor(Int, speed) + 1, length(bins)-1)
                power = calculate_wind_power_density(speed, air_density)
                energy_by_bin[bin_idx] += power  # Energy = Power × Time (1 hour per measurement)
                hours_by_bin[bin_idx] += 1
            end
            
            total_energy = sum(energy_by_bin)
            energy_fraction = energy_by_bin ./ total_energy
            
            # Create results DataFrame
            energy_df = DataFrame(
                bin_center = bin_centers,
                hours = hours_by_bin,
                energy_content = energy_by_bin,
                energy_fraction = energy_fraction,
                cumulative_energy_fraction = cumsum(energy_fraction)
            )
            
            # Save to CSV
            CSV.write(joinpath(output_dir, "wind_energy_content_$(sensor.height)m.csv"), energy_df)
            
            # Create energy content plot
            p_energy = plot(energy_df,
                x=:bin_center, y=:energy_fraction,
                Geom.bar(),
                Guide.title("Wind Energy Content by Speed Bin - $(mast.name) ($(sensor.height)m)"),
                Guide.xlabel("Wind Speed (m/s)"),
                Guide.ylabel("Fraction of Total Energy"),
                Theme(background_color="white", default_color=colorant"darkgreen")
            )
            
            draw(SVG(joinpath(output_dir, "wind_energy_content_$(sensor.height)m.svg"), 10inch, 6inch), p_energy)
            
            mast_results["$(sensor.height)m_energy"] = energy_df
        end
        
        if !isempty(mast_results)
            results[mast.name] = mast_results
        end
    end
    
    return results
end

"""
    analyze_all_frequency(config::AnalyzeConfig)

Run all wind direction frequency analyses for all masts in the configuration.
"""
function analyze_all_frequency(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    results["power_frequency"] = analyze_wind_power_frequency(config)
    results["energy_content"] = analyze_wind_energy_content(config)
    
    return results
end

export analyze_wind_power_frequency, analyze_wind_energy_content, analyze_all_frequency

end # module 