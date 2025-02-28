module AnalyzeTimeSeries

using DataFrames
using CSV
using Gadfly
using Statistics
using Dates
using ColorSchemes
using DataFramesMeta
using GLM
using StatsBase

import ..Types.MastTimeSeries: TimeSeriesData, SensorColumn

# Include Weibull module
include("AnalyzeTimeSeries/Weibull.jl")
import .Weibull: analyze_weibull_distribution

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
function analyze_daily_pattern(data::TimeSeriesData, output_dir::String)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Add hour column
    hourly_df = copy(data.df)
    hourly_df.hour = hour.(hourly_df.timestamp)
    
    # Calculate hourly averages for each height
    results_df = DataFrame(hour = 0:23)
    
    for sensor in speed_sensors
        hourly_means = combine(groupby(hourly_df, :hour), 
            sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
        results_df[!, "$(sensor.height)m"] = hourly_means[:, "$(sensor.height)m"]
    end
    
    # Save to CSV
    CSV.write(joinpath(output_dir, "daily_pattern.csv"), results_df)
    
    # Create plot
    p = plot(stack(results_df, Not(:hour)),
        x=:hour, y=:value, color=:variable,
        Geom.line(),
        Guide.title("24-Hour Wind Speed Pattern"),
        Guide.xlabel("Hour of Day"),
        Guide.ylabel("Wind Speed (m/s)"),
        Theme(background_color="white")
    )
    
    draw(SVG(joinpath(output_dir, "daily_pattern.svg"), 8inch, 6inch), p)
    
    return results_df
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
function analyze_monthly_pattern(data::TimeSeriesData, output_dir::String)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Add month column
    monthly_df = copy(data.df)
    monthly_df.month = month.(monthly_df.timestamp)
    
    # Initialize results DataFrame with all months
    results_df = DataFrame(month = 1:12)
    
    for sensor in speed_sensors
        # Calculate monthly means
        monthly_means = combine(groupby(monthly_df, :month), 
            sensor.columnName => (x -> mean(skipmissing(x))) => "mean")
        
        # Create a full month series with possible missing values
        full_means = Vector{Union{Float64, Missing}}(missing, 12)
        for row in eachrow(monthly_means)
            full_means[row.month] = row.mean
        end
        
        # Add to results
        results_df[!, "$(sensor.height)m"] = full_means
    end
    
    # Save to CSV
    CSV.write(joinpath(output_dir, "monthly_pattern.csv"), results_df)
    
    # Create plot
    month_labels = Dates.monthabbr.(1:12)  # Pre-compute month labels
    p = plot(stack(results_df, Not(:month)),
        x=:month, y=:value, color=:variable,
        Geom.line(),
        Guide.title("Monthly Wind Speed Pattern"),
        Guide.xlabel("Month"),
        Guide.ylabel("Wind Speed (m/s)"),
        Scale.x_discrete(labels=i->month_labels[i]),  # Use discrete scale with pre-computed labels
        Theme(background_color="white")
    )
    
    draw(SVG(joinpath(output_dir, "monthly_pattern.svg"), 8inch, 6inch), p)
    
    return results_df
end

"""
Run all analysis functions on the given time series data
"""
function analyze_all(data::TimeSeriesData, output_dir::String)
    analyze_wind_speed_timeseries(data, output_dir)
    analyze_daily_pattern(data, output_dir)
    analyze_vertical_profile(data, output_dir)
    analyze_monthly_pattern(data, output_dir)
    analyze_weibull_distribution(data, joinpath(output_dir, "weibull"))
end

export analyze_all, analyze_wind_speed_timeseries,
       analyze_daily_pattern, analyze_vertical_profile, 
       analyze_monthly_pattern, analyze_weibull_distribution

end # module 