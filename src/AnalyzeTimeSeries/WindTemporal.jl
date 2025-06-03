module WindTemporal

using DataFrames
using CSV
using Gadfly
using Statistics
using Dates
using ColorSchemes
using DataFramesMeta
using Compose

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, to_air_density_config, get_output_path, AirDensityConfig
import ..AirDensity: calculate_air_density, calculate_wind_power_density

"""
    analyze_wind_speed_timeseries(config::AnalyzeConfig)

Generate time series plots of wind speeds at all heights for all masts.
"""
function analyze_wind_speed_timeseries(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Prepare plotting data
        plot_df = select(mast.timeSeriesData.df, :timestamp)
        for sensor in speed_sensors
            plot_df[!, "$(sensor.height)m"] = mast.timeSeriesData.df[:, sensor.columnName]
        end
        
        # Save to CSV with mast name
        csv_path = joinpath(output_dir, "wind_speed_timeseries.csv")
        CSV.write(csv_path, plot_df)
        
        # Create plot
        p = plot(stack(plot_df, Not(:timestamp)),
            x=:timestamp, y=:value, color=:variable,
            Geom.line(),
            Guide.title("Wind Speed Time Series - $(mast.name)"),
            Guide.xlabel("Time"),
            Guide.ylabel("Wind Speed (m/s)"),
            Theme(background_color="white")
        )
        
        svg_path = joinpath(output_dir, "wind_speed_timeseries.svg")
        draw(SVG(svg_path, 12inch, 6inch), p)
        
        results[mast.name] = plot_df
        @info "Generated wind speed time series for mast $(mast.name)"
    end
    
    return results
end

"""
    analyze_daily_pattern(config::AnalyzeConfig)

Generate 24-hour daily averaged wind speed and power patterns for all masts.
"""
function analyze_daily_pattern(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        air_density_config = to_air_density_config(mast.airDensity)
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Add hour column
        hourly_df = copy(mast.timeSeriesData.df)
        hourly_df.hour = hour.(hourly_df.timestamp)
        
        # Calculate hourly averages for each height
        speed_results_df = DataFrame(hour = 0:23)
        power_results_df = DataFrame(hour = 0:23)
        
        for sensor in speed_sensors
            # Calculate wind speed hourly means
            hourly_means = combine(groupby(hourly_df, :hour), 
                sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
            speed_results_df[!, "$(sensor.height)m"] = hourly_means[:, "$(sensor.height)m"]
            
            # Calculate air density at sensor height
            air_density = calculate_air_density(sensor.height, air_density_config)
            
            # Add power column to hourly_df for this sensor
            power_col_name = "power_$(sensor.height)m"
            hourly_df[!, power_col_name] = [ismissing(ws) ? missing : 
                                           calculate_wind_power_density(ws, air_density) 
                                           for ws in hourly_df[!, sensor.columnName]]
            
            # Calculate power hourly means
            hourly_power = combine(groupby(hourly_df, :hour), 
                power_col_name => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
            power_results_df[!, "$(sensor.height)m"] = hourly_power[:, "$(sensor.height)m"]
        end
        
        # Save to CSV
        CSV.write(joinpath(output_dir, "daily_pattern.csv"), speed_results_df)
        CSV.write(joinpath(output_dir, "daily_power_pattern.csv"), power_results_df)
        
        # Create wind speed plot
        p_speed = plot(stack(speed_results_df, Not(:hour)),
            x=:hour, y=:value, color=:variable,
            Geom.line(),
            Guide.title("24-Hour Wind Speed Pattern - $(mast.name)"),
            Guide.xlabel("Hour of Day"),
            Guide.ylabel("Wind Speed (m/s)"),
            Scale.x_discrete(labels=i->string(i)),
            Coord.cartesian(xmin=0, xmax=23),
            Theme(background_color="white")
        )
        
        draw(SVG(joinpath(output_dir, "daily_pattern.svg"), 8inch, 6inch), p_speed)
        
        # Create wind power plot
        p_power = plot(stack(power_results_df, Not(:hour)),
            x=:hour, y=:value, color=:variable,
            Geom.line(),
            Guide.title("24-Hour Wind Power Density Pattern - $(mast.name)"),
            Guide.xlabel("Hour of Day"),
            Guide.ylabel("Wind Power Density (W/m²)"),
            Scale.x_discrete(labels=i->string(i)),
            Coord.cartesian(xmin=0, xmax=23),
            Theme(background_color="white")
        )
        
        draw(SVG(joinpath(output_dir, "daily_power_pattern.svg"), 8inch, 6inch), p_power)
        
        results[mast.name] = (speed = speed_results_df, power = power_results_df)
        @info "Generated daily patterns for mast $(mast.name)"
    end
    
    return results
end

"""
    analyze_monthly_pattern(config::AnalyzeConfig)

Analyze monthly wind speed and power patterns for all masts.
"""
function analyze_monthly_pattern(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        air_density_config = to_air_density_config(mast.airDensity)
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Add month column
        monthly_df = copy(mast.timeSeriesData.df)
        monthly_df.month = month.(monthly_df.timestamp)
        
        # Initialize results DataFrames with all months
        speed_results_df = DataFrame(month = 1:12)
        power_results_df = DataFrame(month = 1:12)
        
        for sensor in speed_sensors
            # Calculate monthly wind speed means
            monthly_means = combine(groupby(monthly_df, :month), 
                sensor.columnName => (x -> mean(skipmissing(x))) => "mean")
            
            # Create a full month series with possible missing values
            full_means = Vector{Union{Float64, Missing}}(missing, 12)
            for row in eachrow(monthly_means)
                full_means[row.month] = row.mean
            end
            
            # Add to results
            speed_results_df[!, "$(sensor.height)m"] = full_means
            
            # Calculate air density at sensor height
            air_density = calculate_air_density(sensor.height, air_density_config)
            
            # Add power column to monthly_df for this sensor
            power_col_name = "power_$(sensor.height)m"
            monthly_df[!, power_col_name] = [ismissing(ws) ? missing : 
                                            calculate_wind_power_density(ws, air_density) 
                                            for ws in monthly_df[!, sensor.columnName]]
            
            # Calculate monthly power means
            monthly_power = combine(groupby(monthly_df, :month), 
                power_col_name => (x -> mean(skipmissing(x))) => "mean")
            
            # Create a full month series for power with possible missing values
            full_power = Vector{Union{Float64, Missing}}(missing, 12)
            for row in eachrow(monthly_power)
                full_power[row.month] = row.mean
            end
            
            # Add to power results
            power_results_df[!, "$(sensor.height)m"] = full_power
        end
        
        # Save to CSV
        CSV.write(joinpath(output_dir, "monthly_pattern.csv"), speed_results_df)
        CSV.write(joinpath(output_dir, "monthly_power_pattern.csv"), power_results_df)
        
        # Create wind speed plot
        month_labels = Dates.monthabbr.(1:12)
        p_speed = plot(stack(speed_results_df, Not(:month)),
            x=:month, y=:value, color=:variable,
            Geom.line(),
            Guide.title("Monthly Wind Speed Pattern - $(mast.name)"),
            Guide.xlabel("Month"),
            Guide.ylabel("Wind Speed (m/s)"),
            Scale.x_discrete(labels=i->month_labels[i]),
            Theme(background_color="white")
        )
        
        draw(SVG(joinpath(output_dir, "monthly_pattern.svg"), 8inch, 6inch), p_speed)
        
        # Create wind power plot
        p_power = plot(stack(power_results_df, Not(:month)),
            x=:month, y=:value, color=:variable,
            Geom.line(),
            Guide.title("Monthly Wind Power Density Pattern - $(mast.name)"),
            Guide.xlabel("Month"),
            Guide.ylabel("Wind Power Density (W/m²)"),
            Scale.x_discrete(labels=i->month_labels[i]),
            Theme(background_color="white")
        )
        
        draw(SVG(joinpath(output_dir, "monthly_power_pattern.svg"), 8inch, 6inch), p_power)
        
        results[mast.name] = (speed = speed_results_df, power = power_results_df)
        @info "Generated monthly patterns for mast $(mast.name)"
    end
    
    return results
end

"""
    analyze_monthly_daily_wind(config::AnalyzeConfig)

Analyze daily wind speed patterns for each month and create combined 3x4 figures for all masts.
"""
function analyze_monthly_daily_wind(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Add hour and month columns
        hourly_df = copy(mast.timeSeriesData.df)
        hourly_df.hour = hour.(hourly_df.timestamp)
        hourly_df.month = month.(hourly_df.timestamp)
        
        # Month names for plot captions
        month_names = Dates.monthname.(1:12)
        
        # Initialize combined DataFrame for CSV output
        speed_results_df = DataFrame(hour = 0:23)
        
        # Create array to hold individual month plots
        speed_plots = []
        
        # Process each month
        for m in 1:12
            # Filter data for current month
            month_data = filter(row -> row.month == m, hourly_df)
            
            # Skip if no data for this month
            if nrow(month_data) == 0
                # Add placeholder plot
                push!(speed_plots, plot(Coord.cartesian(aspect_ratio=1),
                    Guide.title("$(month_names[m]) (No Data)"),
                    Theme(background_color="white")))
                continue
            end
            
            # Calculate hourly averages for each height - for this month
            month_speed_df = DataFrame(hour = 0:23)
            
            for sensor in speed_sensors
                # Calculate wind speed hourly means for this month
                hourly_means = combine(groupby(month_data, :hour), 
                    sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
                    
                # Ensure all hours are present by joining with the full hour range
                hourly_means = leftjoin(DataFrame(hour = 0:23), hourly_means, on = :hour, matchmissing = :equal)
                
                month_speed_df[!, "$(sensor.height)m"] = hourly_means[!, "$(sensor.height)m"]
                
                # Add column to master results for CSV export
                speed_results_df[!, "$(sensor.height)m_month$(m)"] = hourly_means[!, "$(sensor.height)m"]
            end
            
            # Create wind speed plot for this month
            p_speed = plot(stack(month_speed_df, Not(:hour)),
                x=:hour, y=:value, color=:variable,
                Geom.line(),
                Guide.title(month_names[m]),
                Guide.xlabel(nothing),
                Guide.ylabel(nothing),
                Scale.x_discrete(labels=i->i % 4 == 0 ? string(i) : ""),
                Scale.y_continuous(minvalue=0),
                Coord.cartesian(xmin=0, xmax=23),
                Theme(background_color="white", key_position=:none, plot_padding=[4mm, 2mm, 2mm, 4mm])
            )
            push!(speed_plots, p_speed)
        end
        
        # Create a proper matrix for gridstack (3 rows, 4 columns)
        plot_matrix = Matrix{Union{Gadfly.Plot,Compose.Context}}(undef, 3, 4)
        for row in 1:3
            for col in 1:4
                idx = (row-1)*4 + col
                plot_matrix[row, col] = idx <= length(speed_plots) ? speed_plots[idx] : Compose.context()
            end
        end
        
        # Arrange plots in a 3×4 grid
        speed_grid = gridstack(plot_matrix)
        
        # Save the grid
        img_path = joinpath(output_dir, "daily_wind_pattern_by_month.svg")
        draw(SVG(img_path, 14inch, 11inch), speed_grid)
        
        # Save CSV file with all data
        CSV.write(joinpath(output_dir, "daily_wind_pattern_by_month.csv"), speed_results_df)
        
        results[mast.name] = speed_results_df
        @info "Generated monthly-daily wind patterns for mast $(mast.name)"
    end
    
    return results
end

"""
    analyze_monthly_daily_windpower(config::AnalyzeConfig)

Analyze daily wind power patterns for each month and create combined 3x4 figures for all masts.
"""
function analyze_monthly_daily_windpower(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        air_density_config = to_air_density_config(mast.airDensity)
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Add hour and month columns
        hourly_df = copy(mast.timeSeriesData.df)
        hourly_df.hour = hour.(hourly_df.timestamp)
        hourly_df.month = month.(hourly_df.timestamp)
        
        # Month names for plot captions
        month_names = Dates.monthname.(1:12)
        
        # Initialize combined DataFrame for CSV output
        power_results_df = DataFrame(hour = 0:23)
        
        # Create array to hold individual month plots
        power_plots = []
        
        # Process each month
        for m in 1:12
            # Filter data for current month
            month_data = filter(row -> row.month == m, hourly_df)
            
            # Skip if no data for this month
            if nrow(month_data) == 0
                # Add placeholder plot
                push!(power_plots, plot(Coord.cartesian(aspect_ratio=1),
                    Guide.title("$(month_names[m]) (No Data)"),
                    Theme(background_color="white")))
                continue
            end
            
            # Calculate hourly averages for each height - for this month
            month_power_df = DataFrame(hour = 0:23)
            
            for sensor in speed_sensors
                # Calculate air density at sensor height
                air_density = calculate_air_density(sensor.height, air_density_config)
                
                # Add power column for this sensor
                power_col_name = "power_$(sensor.height)m"
                month_data[!, power_col_name] = [ismissing(ws) ? missing : 
                                              calculate_wind_power_density(ws, air_density) 
                                              for ws in month_data[!, sensor.columnName]]
                
                # Calculate power hourly means for this month
                hourly_power = combine(groupby(month_data, :hour), 
                    power_col_name => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
                    
                # Ensure all hours are present
                hourly_power = leftjoin(DataFrame(hour = 0:23), hourly_power, on = :hour, matchmissing = :equal)
                
                month_power_df[!, "$(sensor.height)m"] = hourly_power[!, "$(sensor.height)m"]
                
                # Add column to master results for CSV export
                power_results_df[!, "$(sensor.height)m_month$(m)"] = hourly_power[!, "$(sensor.height)m"]
            end
            
            # Create wind power plot for this month
            p_power = plot(stack(month_power_df, Not(:hour)),
                x=:hour, y=:value, color=:variable,
                Geom.line(),
                Guide.title(month_names[m]),
                Guide.xlabel(nothing),
                Guide.ylabel(nothing),
                Scale.x_discrete(labels=i->i % 4 == 0 ? string(i) : ""),
                Scale.y_continuous(minvalue=0),
                Coord.cartesian(xmin=0, xmax=23),
                Theme(background_color="white", key_position=:none, plot_padding=[4mm, 2mm, 2mm, 4mm])
            )
            push!(power_plots, p_power)
        end
        
        # Create a proper matrix for power plots (3 rows, 4 columns)
        power_matrix = Matrix{Union{Gadfly.Plot,Compose.Context}}(undef, 3, 4)
        for row in 1:3
            for col in 1:4
                idx = (row-1)*4 + col
                power_matrix[row, col] = idx <= length(power_plots) ? power_plots[idx] : Compose.context()
            end
        end
        
        # Arrange power plots in a 3×4 grid
        power_grid = gridstack(power_matrix)
        
        # Save the grid
        img_path = joinpath(output_dir, "daily_power_pattern_by_month.svg")
        draw(SVG(img_path, 14inch, 11inch), power_grid)
        
        # Save CSV file with all data
        CSV.write(joinpath(output_dir, "daily_power_pattern_by_month.csv"), power_results_df)
        
        results[mast.name] = power_results_df
        @info "Generated monthly-daily power patterns for mast $(mast.name)"
    end
    
    return results
end

"""
    analyze_all_temporal(config::AnalyzeConfig)

Run all temporal wind analyses for all masts in the configuration.
"""
function analyze_all_temporal(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    results["timeseries"] = analyze_wind_speed_timeseries(config)
    results["daily"] = analyze_daily_pattern(config)
    results["monthly"] = analyze_monthly_pattern(config)
    results["monthly_daily_wind"] = analyze_monthly_daily_wind(config)
    results["monthly_daily_power"] = analyze_monthly_daily_windpower(config)
    
    return results
end

export analyze_wind_speed_timeseries, analyze_daily_pattern, analyze_monthly_pattern,
       analyze_monthly_daily_wind, analyze_monthly_daily_windpower, analyze_all_temporal

end # module 