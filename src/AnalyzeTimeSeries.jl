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

import ..Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ..Types.CleanMastConfig: AirDensityConfig

# Include Weibull module
include("AnalyzeTimeSeries/Weibull.jl")
import .Weibull: analyze_weibull_distribution

# Include AirDensity module
include("AnalyzeTimeSeries/AirDensity.jl")
import .AirDensity: calculate_air_density, calculate_wind_power_density

"""
Generate time series plot of wind speeds at all heights
"""
function analyze_wind_speed_timeseries(data::TimeSeriesData, output_dir::String)
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
    
    # Create plot
    p = plot(stack(plot_df, Not(:timestamp)),
        x=:timestamp, y=:value, color=:variable,
        Geom.line(),
        Guide.title("Wind Speed Time Series"),
        Guide.xlabel("Time"),
        Guide.ylabel("Wind Speed (m/s)"),
        Theme(background_color="white")
    )
    
    draw(SVG(joinpath(output_dir, "wind_speed_timeseries.svg"), 12inch, 6inch), p)
    
    return plot_df
end

"""
Generate 24-hour daily averaged wind speed patterns
"""
function analyze_daily_pattern(data::TimeSeriesData, output_dir::String, air_density_config::AirDensityConfig)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Add hour column
    hourly_df = copy(data.df)
    hourly_df.hour = hour.(hourly_df.timestamp)
    
    # Calculate hourly averages for each height
    results_df = DataFrame(hour = 0:23)
    power_df = DataFrame(hour = 0:23)
    
    for sensor in speed_sensors
        # Calculate wind speed hourly means
        hourly_means = combine(groupby(hourly_df, :hour), 
            sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
        results_df[!, "$(sensor.height)m"] = hourly_means[:, "$(sensor.height)m"]
        
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
        power_df[!, "$(sensor.height)m"] = hourly_power[:, "$(sensor.height)m"]
    end
    
    # Save to CSV
    CSV.write(joinpath(output_dir, "daily_pattern.csv"), results_df)
    CSV.write(joinpath(output_dir, "daily_power_pattern.csv"), power_df)
    
    # Create wind speed plot
    p_speed = plot(stack(results_df, Not(:hour)),
        x=:hour, y=:value, color=:variable,
        Geom.line(),
        Guide.title("24-Hour Wind Speed Pattern"),
        Guide.xlabel("Hour of Day"),
        Guide.ylabel("Wind Speed (m/s)"),
        Scale.x_discrete(labels=i->string(i)),  # Ensure discrete x-axis with hour labels
        Coord.cartesian(xmin=0, xmax=23),  # Explicitly set x-axis range
        Theme(background_color="white")
    )
    
    draw(SVG(joinpath(output_dir, "daily_pattern.svg"), 8inch, 6inch), p_speed)
    
    # Create wind power plot
    p_power = plot(stack(power_df, Not(:hour)),
        x=:hour, y=:value, color=:variable,
        Geom.line(),
        Guide.title("24-Hour Wind Power Density Pattern"),
        Guide.xlabel("Hour of Day"),
        Guide.ylabel("Wind Power Density (W/m²)"),
        Scale.x_discrete(labels=i->string(i)),  # Ensure discrete x-axis with hour labels
        Coord.cartesian(xmin=0, xmax=23),  # Explicitly set x-axis range
        Theme(background_color="white")
    )
    
    draw(SVG(joinpath(output_dir, "daily_power_pattern.svg"), 8inch, 6inch), p_power)
    
    return (speed = results_df, power = power_df)
end

"""
Analyze vertical wind speed profile with power law fitting
"""
function analyze_vertical_profile(data::TimeSeriesData, output_dir::String)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Calculate mean wind speeds at each height
    results_df = DataFrame(
        height = Float64[s.height for s in speed_sensors],
        speed = Float64[mean(skipmissing(data.df[:, s.columnName])) for s in speed_sensors]
    )
    
    # Skip if any speeds are missing or NaN
    if any(isnan, results_df.speed) || any(ismissing, results_df.speed)
        @warn "Invalid speed data for vertical profile analysis"
        return nothing
    end
    
    # Fit power law
    model_df = DataFrame(
        log_height = log.(results_df.height),
        log_speed = log.(results_df.speed)
    )
    
    model = lm(@formula(log_speed ~ log_height), model_df)
    α = coef(model)[2]  # Power law exponent
    
    # Generate fitted line
    height_range = range(minimum(results_df.height), maximum(results_df.height), length=100)
    reference_speed = results_df.speed[1]
    reference_height = results_df.height[1]
    fitted_speeds = reference_speed .* (height_range ./ reference_height).^α
    
    fit_df = DataFrame(height=height_range, speed=fitted_speeds)
    
    # Save to CSV
    CSV.write(joinpath(output_dir, "vertical_profile.csv"), results_df)
    
    # Create plot
    p = plot(layer(results_df, x=:speed, y=:height, Geom.point()),
            layer(fit_df, x=:speed, y=:height, Geom.line()),
            Guide.title("Vertical Wind Speed Profile (α = $(round(α, digits=3)))"),
            Guide.xlabel("Wind Speed (m/s)"),
            Guide.ylabel("Height (m)"),
            Theme(background_color="white"))
    
    draw(SVG(joinpath(output_dir, "vertical_profile.svg"), 6inch, 8inch), p)
    
    return results_df
end

"""
Analyze monthly wind speed patterns
"""
function analyze_monthly_pattern(data::TimeSeriesData, output_dir::String, air_density_config::AirDensityConfig)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Add month column
    monthly_df = copy(data.df)
    monthly_df.month = month.(monthly_df.timestamp)
    
    # Initialize results DataFrames with all months
    results_df = DataFrame(month = 1:12)
    power_df = DataFrame(month = 1:12)
    
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
        results_df[!, "$(sensor.height)m"] = full_means
        
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
        power_df[!, "$(sensor.height)m"] = full_power
    end
    
    # Save to CSV
    CSV.write(joinpath(output_dir, "monthly_pattern.csv"), results_df)
    CSV.write(joinpath(output_dir, "monthly_power_pattern.csv"), power_df)
    
    # Create wind speed plot
    month_labels = Dates.monthabbr.(1:12)  # Pre-compute month labels
    p_speed = plot(stack(results_df, Not(:month)),
        x=:month, y=:value, color=:variable,
        Geom.line(),
        Guide.title("Monthly Wind Speed Pattern"),
        Guide.xlabel("Month"),
        Guide.ylabel("Wind Speed (m/s)"),
        Scale.x_discrete(labels=i->month_labels[i]),  # Use discrete scale with pre-computed labels
        Theme(background_color="white")
    )
    
    draw(SVG(joinpath(output_dir, "monthly_pattern.svg"), 8inch, 6inch), p_speed)
    
    # Create wind power plot
    p_power = plot(stack(power_df, Not(:month)),
        x=:month, y=:value, color=:variable,
        Geom.line(),
        Guide.title("Monthly Wind Power Density Pattern"),
        Guide.xlabel("Month"),
        Guide.ylabel("Wind Power Density (W/m²)"),
        Scale.x_discrete(labels=i->month_labels[i]),  # Use discrete scale with pre-computed labels
        Theme(background_color="white")
    )
    
    draw(SVG(joinpath(output_dir, "monthly_power_pattern.svg"), 8inch, 6inch), p_power)
    
    return (speed = results_df, power = power_df)
end

"""
Analyze daily wind speed patterns for each month and create a combined 3x4 figure
"""
function analyze_monthly_daily_wind(data::TimeSeriesData, output_dir::String)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Add hour and month columns
    hourly_df = copy(data.df)
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
            Guide.title(month_names[m]),  # Simplified title format
            Guide.xlabel(nothing),  # Remove x-label for grid layout
            Guide.ylabel(nothing),  # Remove y-label for grid layout
            # Show fewer hour labels to prevent overlapping
            Scale.x_discrete(labels=i->i % 4 == 0 ? string(i) : ""),
            # Ensure consistent y-axis scaling across months
            Scale.y_continuous(minvalue=0),
            Coord.cartesian(xmin=0, xmax=23),
            # Add more space around the plot
            Theme(background_color="white", key_position=:none, plot_padding=[4mm, 2mm, 2mm, 4mm])
        )
        push!(speed_plots, p_speed)
    end
    
    # Create a common legend for wind speed plot
    sensor_heights = ["$(s.height)m" for s in speed_sensors]
    
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
    
    # -------------------------------------------------------------
    # NOTE ABOUT SPACING: 
    # Gadfly adds default padding between elements which creates
    # excessive spacing. Using the basic approach with minimal
    # customization for compatibility with older Gadfly versions.
    # -------------------------------------------------------------
    
    # Create a basic set of elements
    sensor_heights = ["$(s.height)m" for s in speed_sensors]
    colors = [ColorSchemes.viridis[i] for i in range(0, 1, length=length(sensor_heights))]
    
    # Add small title using basic plot
    title_plot = plot(Guide.title("24-Hour Wind Speed Pattern by Month"))
    
    # Create a legend as a proper plot, not just a guide
    legend_plot = plot(
        Guide.manual_color_key("Height", sensor_heights, colors)
    )
    
    # Save the grid separately
    img_grid = SVG(joinpath(output_dir, "daily_wind_pattern_by_month.svg"), 14inch, 11inch)
    draw(img_grid, speed_grid)
    
    # Save CSV file with all data
    CSV.write(joinpath(output_dir, "daily_wind_pattern_by_month.csv"), speed_results_df)
    
    return speed_results_df
end

"""
Analyze daily wind power patterns for each month and create a combined 3x4 figure
"""
function analyze_monthly_daily_windpower(data::TimeSeriesData, output_dir::String, air_density_config::AirDensityConfig)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Add hour and month columns
    hourly_df = copy(data.df)
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
            Guide.title(month_names[m]),  # Simplified title format
            Guide.xlabel(nothing),  # Remove x-label for grid layout
            Guide.ylabel(nothing),  # Remove y-label for grid layout
            # Show fewer hour labels to prevent overlapping
            Scale.x_discrete(labels=i->i % 4 == 0 ? string(i) : ""),
            # Ensure consistent y-axis scaling across months
            Scale.y_continuous(minvalue=0),
            Coord.cartesian(xmin=0, xmax=23),
            # Add more space around the plot
            Theme(background_color="white", key_position=:none, plot_padding=[4mm, 2mm, 2mm, 4mm])
        )
        push!(power_plots, p_power)
    end
    
    # Create a common legend
    sensor_heights = ["$(s.height)m" for s in speed_sensors]
    
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
    
    # -------------------------------------------------------------
    # NOTE ABOUT SPACING: 
    # Gadfly adds default padding between elements which creates
    # excessive spacing. Using the basic approach with minimal
    # customization for compatibility with older Gadfly versions.
    # -------------------------------------------------------------
    
    # Create a basic set of elements
    sensor_heights = ["$(s.height)m" for s in speed_sensors]
    colors = [ColorSchemes.viridis[i] for i in range(0, 1, length=length(sensor_heights))]
    
    # Add small title using basic plot
    title_plot = plot(Guide.title("24-Hour Wind Power Density Pattern by Month"))
    
    # Create a legend as a proper plot, not just a guide
    legend_plot = plot(
        Guide.manual_color_key("Height", sensor_heights, colors)
    )
    
    # Save the grid separately 
    img_grid = SVG(joinpath(output_dir, "daily_power_pattern_by_month.svg"), 14inch, 11inch)
    draw(img_grid, power_grid)
    
    # Save CSV file with all data
    CSV.write(joinpath(output_dir, "daily_power_pattern_by_month.csv"), power_results_df)
    
    return power_results_df
end

"""
Analyze wind power frequency distribution across wind speed bins
"""
function analyze_wind_power_frequency(data::TimeSeriesData, output_dir::String, air_density_config::AirDensityConfig)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    # Use wind-power-frequency directory instead of power_frequency
    output_dir = joinpath(output_dir, "wind-power-frequency")
    mkpath(output_dir)
    
    # Define wind speed bins (0 to 28 m/s, 1 m/s increments)
    bins = 0:1:28
    bin_centers = 0.5:1:27.5
    
    for sensor in speed_sensors
        # Calculate air density at sensor height
        air_density = calculate_air_density(sensor.height, air_density_config)
        
        # Get wind speed data for this sensor
        wind_speeds = collect(skipmissing(data.df[!, sensor.columnName]))
        
        # Skip if no valid data
        isempty(wind_speeds) && continue
        
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
        
        # Save to CSV
        CSV.write(joinpath(output_dir, "wind_power_frequency_$(sensor.height)m.csv"), results_df)
        
        # Create a combined plot with both frequency distributions using group
        # First reshape the data for grouped bar plot
        plot_df = DataFrame(
            bin_center = repeat(bin_centers, 2),
            value = [frequency; power_frequency],
            type = repeat(["Wind Speed Frequency", "Wind Power Frequency"], inner=length(bin_centers))
        )
        
        p_combined = plot(plot_df,
            x=:bin_center, y=:value, color=:type, group=:type,
            Geom.bar(position=:dodge),
            Guide.title("Wind Speed and Power Frequency Distribution ($(sensor.height)m)"),
            Guide.xlabel("Wind Speed (m/s)"),
            Guide.ylabel("Frequency"),
            Scale.color_discrete_manual(colorant"steelblue", colorant"darkred"),
            Theme(background_color="white")
        )
        
        draw(SVG(joinpath(output_dir, "wind_frequency_distribution_$(sensor.height)m.svg"), 12inch, 7inch), p_combined)
    end
end

"""
Run all analysis functions on the given time series data
"""
function analyze_all(data::TimeSeriesData, output_dir::String, air_density_config::AirDensityConfig)
    analyze_wind_speed_timeseries(data, output_dir)
    analyze_daily_pattern(data, output_dir, air_density_config)
    analyze_vertical_profile(data, output_dir)
    analyze_monthly_pattern(data, output_dir, air_density_config)
    analyze_monthly_daily_wind(data, output_dir)
    analyze_monthly_daily_windpower(data, output_dir, air_density_config)
    analyze_weibull_distribution(data, joinpath(output_dir, "weibull"))
    analyze_wind_power_frequency(data, output_dir, air_density_config)
end

export analyze_all, analyze_wind_speed_timeseries,
       analyze_daily_pattern, analyze_vertical_profile, 
       analyze_monthly_pattern, analyze_monthly_daily_wind,
       analyze_monthly_daily_windpower, analyze_weibull_distribution,
       analyze_wind_power_frequency

end # module 