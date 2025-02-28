module Weibull

using DataFrames
using CSV
using Gadfly
using Statistics
using Distributions
using Optim
using ColorSchemes
using StatsBase
using DataFramesMeta
using Dates
using SpecialFunctions: gamma

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn

"""
    fit_weibull(data::Vector{Union{Missing, Float64}})::Union{Tuple{Float64, Float64}, Nothing}

Fit a Weibull distribution to wind speed data using maximum likelihood estimation.

# Arguments
- `data::Vector{Union{Missing, Float64}}`: Vector of wind speed values (must be positive), can contain missing values

# Returns
- `Tuple{Float64, Float64}`: Weibull shape (k) and scale (c) parameters
"""
function fit_weibull(data::Vector{Union{Missing, Float64}})::Union{Tuple{Float64, Float64}, Nothing} 
    # Filter out missing values and ensure positive values
    valid_data = [x for x in data if !ismissing(x) && x > 0]
    
    if length(valid_data) < 10
        # Not enough data for reliable fitting
        return nothing
    end
    
    # Initial parameter guesses
    k_init = 2.0  # Shape parameter (typical for wind)
    c_init = mean(valid_data) / gamma(1 + 1/k_init)  # Scale parameter
    
    # Negative log-likelihood function for Weibull distribution
    function neg_log_likelihood(params)
        k, c = params
        if k <= 0 || c <= 0
            return Inf  # Invalid parameters
        end
        
        # Weibull log-likelihood
        n = length(valid_data)
        sum_x_k = sum(x -> x^k, valid_data)
        sum_log_x = sum(log, valid_data)
        
        -n * log(k) + n * k * log(c) - k * sum_log_x + sum_x_k / c^k
    end
    
    # Optimize to find MLE parameters
    result = optimize(neg_log_likelihood, [k_init, c_init], LBFGS())
    
    if Optim.converged(result)
        k, c = Optim.minimizer(result)
        return (k, c)
    else
        # Fallback to method of moments if optimization fails
        mean_val = mean(valid_data)
        var_val = var(valid_data)
        
        # Method of moments estimators
        coef_var = sqrt(var_val) / mean_val
        k_mom = (0.9874 / coef_var)^1.0983  # Approximation
        c_mom = mean_val / gamma(1 + 1/k_mom)
        
        return (k_mom, c_mom)
    end
end

"""
    calculate_weibull_pdf(k::Float64, c::Float64, x::Vector{Float64})::Vector{Float64}

Calculate the Weibull probability density function for given parameters and x values.

# Arguments
- `k::Float64`: Shape parameter
- `c::Float64`: Scale parameter
- `x::Vector{Float64}`: Vector of x values to evaluate PDF at

# Returns
- `Vector{Float64}`: PDF values
"""
function calculate_weibull_pdf(k::Float64, c::Float64, x::Vector{Float64})::Vector{Float64}
    if isnan(k) || isnan(c) || k <= 0 || c <= 0
        return zeros(length(x))
    end
    
    pdf.(Distributions.Weibull(k, c), x)
end

"""
    analyze_weibull_distribution(data::TimeSeriesData, output_dir::String)

Analyze wind speed distributions by fitting Weibull distributions at each height.
Generates plots and CSV files with the distribution parameters.

# Arguments
- `data::TimeSeriesData`: Time series data with wind speed measurements
- `output_dir::String`: Directory to save output files

# Returns
- `DataFrame`: DataFrame with Weibull parameters for each height
"""
function analyze_weibull_distribution(data::TimeSeriesData, output_dir::String)
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", data.sensors)
    isempty(speed_sensors) && return nothing
    
    mkpath(output_dir)
    
    # Create results DataFrame
    results_df = DataFrame(
        height = Float64[],
        shape_k = Float64[],
        scale_c = Float64[],
        mean_speed = Float64[]
    )
    
    # Process each height
    for sensor in speed_sensors
        # Extract wind speed data
        wind_speeds = data.df[:, sensor.columnName]
        
        # Skip if insufficient valid data
        valid_speeds = Float64[x for x in wind_speeds if !ismissing(x) && x > 0]
        if length(valid_speeds) < 10
            continue
        end
        
        # Calculate mean speed
        mean_speed = mean(valid_speeds)
        
        # Fit Weibull distribution
        weibull_params = fit_weibull(Vector{Union{Missing, Float64}}(wind_speeds))
        
        # Skip if fitting failed
        if isnothing(weibull_params)
            continue
        end
        k,c = weibull_params
        
        # Add to results
        push!(results_df, (sensor.height, k, c, mean_speed))
        
        # Create histogram and fitted distribution
        hist_data = fit(Histogram, valid_speeds, nbins=20)
        bin_edges = hist_data.edges[1]
        bin_centers = [(bin_edges[i] + bin_edges[i+1])/2 for i in 1:length(bin_edges)-1]
        bin_widths = [bin_edges[i+1] - bin_edges[i] for i in 1:length(bin_edges)-1]
        
        # Normalize histogram to create probability density
        hist_density = hist_data.weights ./ (sum(hist_data.weights) * bin_widths)
        
        # Create DataFrame for plotting
        hist_df = DataFrame(
            speed = bin_centers,
            density = hist_density
        )
        
        # Calculate fitted Weibull PDF
        x_range = range(0, stop=maximum(valid_speeds) * 1.2, length=100)
        weibull_pdf = calculate_weibull_pdf(k, c, collect(x_range))
        
        fit_df = DataFrame(
            speed = collect(x_range),
            density = weibull_pdf
        )
        
        # Save data to CSV
        csv_filename = joinpath(output_dir, "weibull_$(Int(sensor.height))m.csv")
        CSV.write(csv_filename, DataFrame(
            bin_center = bin_centers,
            observed_density = hist_density,
            fitted_density = calculate_weibull_pdf(k, c, bin_centers)
        ))
        
        # Create plot
        p = plot(
            layer(fit_df, x=:speed, y=:density, Geom.line(), color=[colorant"red"]),
            layer(hist_df, x=:speed, y=:density, Geom.bar(position=:identity)),
            Guide.title("Wind Speed Distribution at $(Int(sensor.height))m\nWeibull: k=$(round(k, digits=2)), c=$(round(c, digits=2)) m/s"),
            Guide.xlabel("Wind Speed (m/s)"),
            Guide.ylabel("Probability Density"),
            Theme(background_color="white", bar_spacing=0mm)
        )
        
        # Save plot
        svg_filename = joinpath(output_dir, "weibull_$(Int(sensor.height))m.svg")
        draw(SVG(svg_filename, 8inch, 6inch), p)
    end
    
    # Save summary to CSV
    if !isempty(results_df)
        CSV.write(joinpath(output_dir, "weibull_parameters.csv"), results_df)
    end
    
    return results_df
end

export analyze_weibull_distribution

end # module 