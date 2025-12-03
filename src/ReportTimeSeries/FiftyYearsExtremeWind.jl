module FiftyYearsExtremeWind

using DataFrames
using CSV
using Statistics
using Distributions
using Dates
using SummaryTables
using Optim
using CairoMakie
using AlgebraOfGraphics

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.ReportTimeSeriesConfiguration: ReportTimeSeriesConfig, MastReportTimeSeriesConfig, get_output_path
import ..AirDensity: calculate_air_density
import ..Utils: format_height

# IEC 61400-1 standard air density (kg/m³)
const STANDARD_AIR_DENSITY = 1.225

"""
    fit_gumbel_distribution(data::Vector{Float64})::Union{Tuple{Float64, Float64}, Nothing}

Fit a Gumbel distribution to extreme wind speed data using maximum likelihood estimation.

# Arguments
- `data::Vector{Float64}`: Vector of extreme wind speed values (5-day maxima)

# Returns
- `Tuple{Float64, Float64}`: Gumbel location (μ) and scale (β) parameters, or Nothing if fitting fails
"""
function fit_gumbel_distribution(data::Vector{Float64})::Union{Tuple{Float64, Float64}, Nothing}
    # Filter and validate data using functional pipeline
    valid_data = data |>
        values -> filter(x -> !isnan(x) && !isinf(x) && x > 0, values)
    
    if length(valid_data) < 5
        @warn "Insufficient data for Gumbel fitting: $(length(valid_data)) samples"
        return nothing
    end
    
    # Method of moments estimators as initial guess
    sample_mean = mean(valid_data)
    sample_std = std(valid_data)
    
    # Method of moments for Gumbel distribution
    β_init = sample_std * sqrt(6) / π  # Scale parameter
    μ_init = sample_mean - β_init * Base.MathConstants.γ  # Location parameter (γ is Euler-Mascheroni constant)
    
    # Negative log-likelihood function for Gumbel distribution
    function neg_log_likelihood(params)
        μ, β = params
        if β <= 0
            return Inf  # Invalid parameters
        end
        
        # Gumbel negative log-likelihood
        n = length(valid_data)
        z = (valid_data .- μ) ./ β
        
        # Check for numerical stability
        if any(z .> 700)  # Prevent overflow in exp
            return Inf
        end
        
        # -log L = n*log(β) + sum(z) + sum(exp(-z))
        n * log(β) + sum(z) + sum(exp.(-z))
    end
    
    # Optimize to find MLE parameters
    result = optimize(neg_log_likelihood, [μ_init, β_init], LBFGS())

    if Optim.converged(result)
        μ, β = Optim.minimizer(result)
        return (μ, β)
    else
        # If optimization doesn't converge, use method of moments
        return (μ_init, β_init)
    end
end

"""
    calculate_gumbel_return_period_wind_speed(μ::Float64, β::Float64, return_period_years::Float64, sampling_period_days::Float64=5.0)::Float64

Calculate wind speed for a given return period using fitted Gumbel distribution.
Since the Gumbel distribution is fitted to 5-day maxima, the return period calculation
must account for the number of sampling periods per year.

# Arguments
- `μ::Float64`: Gumbel location parameter
- `β::Float64`: Gumbel scale parameter  
- `return_period_years::Float64`: Return period in years
- `sampling_period_days::Float64`: Sampling period in days (default: 5.0)

# Returns
- `Float64`: Wind speed corresponding to the return period
"""
function calculate_gumbel_return_period_wind_speed(μ::Float64, β::Float64, return_period_years::Float64, sampling_period_days::Float64=5.0)::Float64
    # Calculate total number of sampling periods in the return period
    # For 50-year return period with 5-day sampling: T = 50 * 365 / 5 = 3650 periods
    total_periods = return_period_years * 365.0 / sampling_period_days
    
    # For Gumbel distribution: x = μ - β * ln(-ln(1 - 1/T))
    # where T is the return period in terms of sampling periods
    probability = 1.0 - 1.0 / total_periods
    
    # Avoid numerical issues
    if probability >= 1.0
        probability = 0.999999
    end
    
    return μ - β * log(-log(probability))
end

"""
    extract_five_day_maxima(wind_speeds::Vector{Union{Missing, Float64}}, timestamps::Vector{DateTime})::Vector{Float64}

Extract 5-day maximum wind speeds from time series data.

# Arguments
- `wind_speeds::Vector{Union{Missing, Float64}}`: Time series of wind speed measurements
- `timestamps::Vector{DateTime}`: Corresponding timestamps

# Returns
- `Vector{Float64}`: Vector of 5-day maximum wind speeds
"""
function extract_five_day_maxima(wind_speeds::Vector{Union{Missing, Float64}}, timestamps::Vector{DateTime})::Vector{Float64}
    # Create DataFrame and clean data using functional pipeline
    df = DataFrame(timestamp = timestamps, wind_speed = wind_speeds) |>
        data -> dropmissing(data) |>
        data -> sort!(data, :timestamp)
    
    if nrow(df) == 0
        return Float64[]
    end
    
    # Add 5-day period grouping column using functional approach
    first_timestamp = df.timestamp[1]
    
    df_with_periods = df |>
        data -> transform(data, :timestamp => 
            (timestamps -> floor.(Int, (timestamps .- first_timestamp) ./ Day(5))) => :five_day_period)
    
    # Extract 5-day maxima using groupby and combine
    five_day_maxima = df_with_periods |>
        data -> groupby(data, :five_day_period) |>
        groups -> combine(groups, :wind_speed => maximum => :max_wind_speed; threads=false) |>
        result -> result.max_wind_speed |>
        maxima -> filter(speed -> !isnan(speed) && !isinf(speed), maxima)
    
    return five_day_maxima
end

"""
    convert_to_standard_air_density(wind_speed::Float64, actual_density::Float64)::Float64

Convert wind speed to equivalent wind speed at standard air density (1.225 kg/m³) using IEC formula.

# Arguments
- `wind_speed::Float64`: Wind speed at actual air density (m/s)
- `actual_density::Float64`: Actual air density (kg/m³)

# Returns
- `Float64`: Equivalent wind speed at standard air density of 1.225 kg/m³ (m/s)
"""
function convert_to_standard_air_density(wind_speed::Float64, actual_density::Float64)::Float64
    # Using IEC formula: v_1225 = v_actual * sqrt(ρ_actual / ρ_1225)
    # This maintains constant kinetic energy: 1/2 * ρ * v²
    # where ρ_1225 = 1.225 kg/m³ (standard air density)
    return wind_speed * sqrt(actual_density / STANDARD_AIR_DENSITY)
end

"""
    analyze_method1_sustained_and_extreme(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}

Analyze wind speeds using Method 1: 5 times average wind speed method.
Calculates both 50-year maximum sustained wind speed and 50-year extreme gust wind speed.

# Arguments
- `mast::MastReportTimeSeriesConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Average wind speed sensor (statType="avg")
- `air_density::Float64`: Air density at sensor height

# Returns
- `NamedTuple`: Results containing both sustained and extreme wind speeds, or Nothing if analysis fails
"""
function analyze_method1_sustained_and_extreme(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}
    # Extract and process wind speed data using functional pipeline
    result = mast.timeSeriesData.df[:, sensor.columnName] |>
        speeds -> filter(x -> !ismissing(x) && !isnan(x) && x > 0, speeds) |>
        valid_speeds -> begin
            if isempty(valid_speeds)
                @warn "No valid average wind speed data found at $(sensor.height)m for Method 1"
                nothing
            else
                # Calculate Method 1 results
                avg_speed = mean(valid_speeds)
                
                # 50年最大持续风速 (50-year maximum sustained wind speed)
                sustained_speed = 5.0 * avg_speed
                sustained_speed_1225 = convert_to_standard_air_density(sustained_speed, air_density)
                
                # 50年极大极端风速 (50-year extreme gust wind speed)
                extreme_speed = 1.4 * sustained_speed  # IEC formula: V_extreme = 1.4 * V_sustained
                extreme_speed_1225 = convert_to_standard_air_density(extreme_speed, air_density)
                
                @info "Method 1 for $(sensor.height)m: Sustained = $(round(sustained_speed, digits=2)) m/s, Extreme = $(round(extreme_speed, digits=2)) m/s"
                
                (
                    height = sensor.height,
                    method = "5倍平均风速法",
                    sustained_wind_speed = sustained_speed,
                    sustained_wind_speed_1225_density = sustained_speed_1225,
                    extreme_wind_speed = extreme_speed,
                    extreme_wind_speed_1225_density = extreme_speed_1225,
                    air_density = air_density,
                    average_wind_speed = avg_speed
                )
            end
        end
    
    return result
end

"""
    analyze_method2_sustained(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64, output_dir::String)::Union{NamedTuple, Nothing}

Analyze 50-year maximum sustained wind speed using Method 2: 5-day maximum method with Gumbel distribution applied to average wind speed data.

# Arguments
- `mast::MastReportTimeSeriesConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Average wind speed sensor (statType="avg")
- `air_density::Float64`: Air density at sensor height
- `output_dir::String`: Directory to save Q-Q plots

# Returns
- `NamedTuple`: Results containing sustained wind speeds, Gumbel parameters, and Q-Q plot path, or Nothing if analysis fails
"""
function analyze_method2_sustained(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64, output_dir::String)::Union{NamedTuple, Nothing}
    # Extract wind speed data (average wind speed for sustained calculation)
    wind_speeds = mast.timeSeriesData.df[:, sensor.columnName]
    timestamps = mast.timeSeriesData.df[:, :timestamp]
    
    # Extract 5-day maxima from average wind speed data
    five_day_maxima = extract_five_day_maxima(Vector{Union{Missing, Float64}}(wind_speeds), timestamps)
    
    if length(five_day_maxima) < 5
        @warn "Insufficient 5-day maximum samples ($(length(five_day_maxima))) for sustained analysis at $(sensor.height)m"
        return nothing
    end
    
    @info "Found $(length(five_day_maxima)) five-day maximum samples for sustained analysis at $(sensor.height)m"
    
    # Fit Gumbel distribution
    gumbel_params = fit_gumbel_distribution(five_day_maxima)
    
    if isnothing(gumbel_params)
        @warn "Failed to fit Gumbel distribution for sustained analysis at $(sensor.height)m"
        return nothing
    end
    
    μ, β = gumbel_params
    
    # Calculate 50-year return period sustained wind speed
    sustained_speed = calculate_gumbel_return_period_wind_speed(μ, β, 50.0)
    sustained_speed_1225 = convert_to_standard_air_density(sustained_speed, air_density)
    
    # Calculate sample statistics
    sample_mean = mean(five_day_maxima)
    sample_std = std(five_day_maxima)
    
    # Generate Q-Q plot to verify Gumbel distribution fit
    qq_plot_path = generate_gumbel_qq_plot(five_day_maxima, μ, β, sensor.height, mast.name, output_dir, "sustained")
    
    return (
        height = sensor.height,
        method = "五日最大风速法（持续风速）",
        wind_speed_type = "sustained",
        wind_speed = sustained_speed,
        wind_speed_1225_density = sustained_speed_1225,
        air_density = air_density,
        gumbel_location = μ,
        gumbel_scale = β,
        sample_count = length(five_day_maxima),
        sample_mean = sample_mean,
        sample_std = sample_std,
        qq_plot_path = qq_plot_path
    )
end

"""
    analyze_method2_extreme(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64, output_dir::String)::Union{NamedTuple, Nothing}

Analyze 50-year extreme gust wind speed using Method 2: 5-day maximum method with Gumbel distribution applied to maximum wind speed data.

# Arguments
- `mast::MastReportTimeSeriesConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Maximum wind speed sensor (statType="max")
- `air_density::Float64`: Air density at sensor height
- `output_dir::String`: Directory to save Q-Q plots

# Returns
- `NamedTuple`: Results containing extreme wind speeds, Gumbel parameters, and Q-Q plot path, or Nothing if analysis fails
"""
function analyze_method2_extreme(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64, output_dir::String)::Union{NamedTuple, Nothing}
    # Extract wind speed data (maximum wind speed for extreme calculation)
    wind_speeds = mast.timeSeriesData.df[:, sensor.columnName]
    timestamps = mast.timeSeriesData.df[:, :timestamp]
    
    # Extract 5-day maxima from maximum wind speed data
    five_day_maxima = extract_five_day_maxima(Vector{Union{Missing, Float64}}(wind_speeds), timestamps)
    
    if length(five_day_maxima) < 5
        @warn "Insufficient 5-day maximum samples ($(length(five_day_maxima))) for extreme analysis at $(sensor.height)m"
        return nothing
    end
    
    @info "Found $(length(five_day_maxima)) five-day maximum samples for extreme analysis at $(sensor.height)m"
    
    # Fit Gumbel distribution
    gumbel_params = fit_gumbel_distribution(five_day_maxima)
    
    if isnothing(gumbel_params)
        @warn "Failed to fit Gumbel distribution for extreme analysis at $(sensor.height)m"
        return nothing
    end
    
    μ, β = gumbel_params
    
    # Calculate 50-year return period extreme wind speed
    extreme_speed = calculate_gumbel_return_period_wind_speed(μ, β, 50.0)
    extreme_speed_1225 = convert_to_standard_air_density(extreme_speed, air_density)
    
    # Calculate sample statistics
    sample_mean = mean(five_day_maxima)
    sample_std = std(five_day_maxima)
    
    # Generate Q-Q plot to verify Gumbel distribution fit
    qq_plot_path = generate_gumbel_qq_plot(five_day_maxima, μ, β, sensor.height, mast.name, output_dir, "extreme")
    
    return (
        height = sensor.height,
        method = "五日最大风速法（极端风速）",
        wind_speed_type = "extreme",
        wind_speed = extreme_speed,
        wind_speed_1225_density = extreme_speed_1225,
        air_density = air_density,
        gumbel_location = μ,
        gumbel_scale = β,
        sample_count = length(five_day_maxima),
        sample_mean = sample_mean,
        sample_std = sample_std,
        qq_plot_path = qq_plot_path
    )
end

"""
    analyze_method3_sustained(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}

Analyze 50-year maximum sustained wind speed using Method 3: Extreme Wind Model (EWM) method applied to average wind speed data.

# Arguments
- `mast::MastReportTimeSeriesConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Average wind speed sensor (statType="avg")
- `air_density::Float64`: Air density at sensor height

# Returns
- `NamedTuple`: Results containing sustained wind speeds, or Nothing if analysis fails
"""
function analyze_method3_sustained(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}
    # Extract and process average wind speed data using functional pipeline
    result = mast.timeSeriesData.df[:, sensor.columnName] |>
        speeds -> filter(x -> !ismissing(x) && !isnan(x) && x > 0, speeds) |>
        valid_speeds -> begin
            if isempty(valid_speeds)
                @warn "No valid average wind speed data found at $(sensor.height)m for Method 3 (EWM) sustained analysis"
                nothing
            else
                # Calculate Method 3 (EWM) sustained results
                observed_max = maximum(valid_speeds)
                sustained_speed = 1.25 * observed_max  # V_sustained = 1.25 * V_max_avg
                sustained_speed_1225 = convert_to_standard_air_density(sustained_speed, air_density)
                
                @info "Method 3 (EWM) sustained for $(sensor.height)m: Max observed avg = $(round(observed_max, digits=2)) m/s, 50-year sustained = $(round(sustained_speed, digits=2)) m/s"
                
                (
                    height = sensor.height,
                    method = "极端风速模型法（持续风速）",
                    wind_speed_type = "sustained",
                    wind_speed = sustained_speed,
                    wind_speed_1225_density = sustained_speed_1225,
                    air_density = air_density,
                    observed_max = observed_max,
                    sample_count = length(valid_speeds)
                )
            end
        end
    
    return result
end

"""
    analyze_method3_extreme(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}

Analyze 50-year extreme gust wind speed using Method 3: Extreme Wind Model (EWM) method applied to maximum wind speed data.

# Arguments
- `mast::MastReportTimeSeriesConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Maximum wind speed sensor (statType="max")
- `air_density::Float64`: Air density at sensor height

# Returns
- `NamedTuple`: Results containing extreme wind speeds, or Nothing if analysis fails
"""
function analyze_method3_extreme(mast::MastReportTimeSeriesConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}
    # Extract and process maximum wind speed data using functional pipeline
    result = mast.timeSeriesData.df[:, sensor.columnName] |>
        speeds -> filter(x -> !ismissing(x) && !isnan(x) && x > 0, speeds) |>
        valid_speeds -> begin
            if isempty(valid_speeds)
                @warn "No valid maximum wind speed data found at $(sensor.height)m for Method 3 (EWM) extreme analysis"
                nothing
            else
                # Calculate Method 3 (EWM) extreme results
                observed_max = maximum(valid_speeds)
                extreme_speed = 1.25 * observed_max  # V_extreme = 1.25 * V_max_max
                extreme_speed_1225 = convert_to_standard_air_density(extreme_speed, air_density)
                
                @info "Method 3 (EWM) extreme for $(sensor.height)m: Max observed max = $(round(observed_max, digits=2)) m/s, 50-year extreme = $(round(extreme_speed, digits=2)) m/s"
                
                (
                    height = sensor.height,
                    method = "极端风速模型法（极端风速）",
                    wind_speed_type = "extreme",
                    wind_speed = extreme_speed,
                    wind_speed_1225_density = extreme_speed_1225,
                    air_density = air_density,
                    observed_max = observed_max,
                    sample_count = length(valid_speeds)
                )
            end
        end
    
    return result
end

"""
    generate_gumbel_qq_plot(data::Vector{Float64}, μ::Float64, β::Float64, height::Float64, mast_name::String, output_dir::String, wind_speed_type::String)::String

Generate a Q-Q plot comparing empirical quantiles with fitted Gumbel distribution quantiles,
including 95% confidence bands generated through Monte Carlo simulation.

# Arguments
- `wind_data::Vector{Float64}`: 5-day maximum wind speed data
- `μ::Float64`: Gumbel location parameter
- `β::Float64`: Gumbel scale parameter  
- `height::Float64`: Sensor height
- `mast_name::String`: Mast name for plot title
- `output_dir::String`: Directory to save the plot
- `wind_speed_type::String`: Type of wind speed (sustained or extreme)

# Returns
- `String`: Path to the saved Q-Q plot file
"""
function generate_gumbel_qq_plot(wind_data::Vector{Float64}, μ::Float64, β::Float64, height::Float64, mast_name::String, output_dir::String, wind_speed_type::String)::String
    # Sort data for empirical quantiles
    sorted_data = sort(wind_data)
    n = length(sorted_data)
    
    # Calculate empirical quantiles (plotting positions)
    empirical_probs = collect(1:n) ./ (n + 1)  # Using (i)/(n+1) plotting position
    
    # Calculate theoretical Gumbel quantiles
    # For Gumbel distribution: x = μ - β * ln(-ln(p))
    # Break down the calculation to avoid nested broadcasting issues
    neg_log_probs = -log.(empirical_probs)
    log_neg_log_probs = log.(neg_log_probs)
    theoretical_quantiles = μ .- β .* log_neg_log_probs
    
    # Generate 95% confidence bands using Monte Carlo simulation
    n_monte_carlo = 1000
    ci_df = generate_qq_monte_carlo_bands(empirical_probs, μ, β, n, n_monte_carlo)
    # Add confidence bands using ribbon
    confidence_ribbon = data(ci_df) * mapping(:quantiles, :lower, :upper, color=:category) * visual(Band, alpha=0.3, color=:lightgray)
    
    # Create Q-Q plot data
    qq_df = DataFrame(
        theoretical = theoretical_quantiles,
        empirical = sorted_data,
        category = "empirical quantiles"
    )
    
    # Create the Q-Q plot components
    qq_points = data(qq_df) * mapping(:theoretical, :empirical, color=:category) * visual(Scatter, markersize=8, color=:blue)
    
    # Add diagonal reference line
    min_val = minimum([minimum(theoretical_quantiles), minimum(sorted_data)])
    max_val = maximum([maximum(theoretical_quantiles), maximum(sorted_data)])
    diagonal_line = data(DataFrame(x=[min_val, max_val], y=[min_val, max_val])) * 
                   mapping(:x, :y) * visual(Lines, linestyle=:dash, linewidth=2, color=:red)
    
    # Combine all plot elements
    combined_plot = confidence_ribbon + diagonal_line + qq_points
    
    fig = draw(combined_plot,
        axis=(
            title="Q-Q Plot: Gumbel Distribution Fit\n$(mast_name) - $(height)m (μ=$(round(μ, digits=3)), β=$(round(β, digits=3)))",
            xlabel="Theoretical Gumbel Quantiles (m/s)",
            ylabel="Empirical Quantiles (m/s)",
            aspect=DataAspect()
        ),
        figure=(size=(600, 600),)
    )
    
    # Save the plot
    height_str = format_height(height)
    plot_path = joinpath(output_dir, "gumbel_qq_plot_$(height_str)m_$(wind_speed_type).png")
    save(plot_path, fig, size=(1000, 1000))

    @info "Generated Gumbel Q-Q plot with 95% Monte Carlo confidence bands for $(mast_name) at $(height)m: $(plot_path)"
    return plot_path
end

"""
    generate_qq_monte_carlo_bands(empirical_probs::Vector{Float64}, μ::Float64, β::Float64, n::Int, n_monte_carlo::Int=1000)::DataFrame

Generate 95% confidence bands for Q-Q plot using Monte Carlo simulation from fitted Gumbel distribution.

# Arguments
- `empirical_probs::Vector{Float64}`: Empirical probabilities for plotting positions
- `μ::Float64`: Gumbel location parameter
- `β::Float64`: Gumbel scale parameter
- `n::Int`: Original sample size
- `n_monte_carlo::Int`: Number of Monte Carlo samples (default: 1000)

# Returns
- `DataFrame`: Contains `probs`, `quantiles`, `lower`, `upper`, and `category` columns
"""
function generate_qq_monte_carlo_bands(empirical_probs::Vector{Float64}, μ::Float64, β::Float64, n::Int, n_monte_carlo::Int=1000)::DataFrame
    # Create Gumbel distribution object
    gumbel_dist = Gumbel(μ, β)
    
    # Initialize Monte Carlo quantile storage
    monte_carlo_quantiles = Matrix{Float64}(undef, length(empirical_probs), n_monte_carlo)
    
    # Generate Monte Carlo samples
    for i in 1:n_monte_carlo
        # Generate n random samples from fitted Gumbel distribution
        monte_carlo_sample = rand(gumbel_dist, n)
        
        # Sort Monte Carlo sample
        sorted_monte_carlo = sort(monte_carlo_sample)
        
        # Store quantiles corresponding to empirical probabilities
        for (j, prob) in enumerate(empirical_probs)
            # Use linear interpolation to get quantile at exact probability
            quantile_idx = prob * (n - 1) + 1
            lower_idx = floor(Int, quantile_idx)
            upper_idx = ceil(Int, quantile_idx)
            
            if lower_idx == upper_idx
                monte_carlo_quantiles[j, i] = sorted_monte_carlo[lower_idx]
            else
                # Linear interpolation between adjacent order statistics
                weight = quantile_idx - lower_idx
                monte_carlo_quantiles[j, i] = (1 - weight) * sorted_monte_carlo[lower_idx] + 
                                            weight * sorted_monte_carlo[upper_idx]
            end
        end
    end
    
    # Calculate confidence intervals (2.5% and 97.5% quantiles)
    lower_ci = [quantile(monte_carlo_quantiles[i, :], 0.025) for i in 1:length(empirical_probs)]
    upper_ci = [quantile(monte_carlo_quantiles[i, :], 0.975) for i in 1:length(empirical_probs)]

    neg_log_probs = -log.(empirical_probs)
    log_neg_log_probs = log.(neg_log_probs)
    theoretical_quantiles = μ .- β .* log_neg_log_probs
    
    return DataFrame(probs = empirical_probs, quantiles = theoretical_quantiles, lower = lower_ci, upper = upper_ci, category = "95% confidence bands")
end

"""
    calculate_qq_grid_layout(n_heights::Int)::@NamedTuple{cols::Int, rows::Int, size::Tuple{Int, Int}}

Calculate optimal grid layout configuration for Q-Q plots based on number of heights.

# Arguments
- `n_heights::Int`: Number of heights to display

# Returns
- `@NamedTuple{cols::Int, rows::Int, size::Tuple{Int, Int}}`: Layout configuration with fields (cols, rows, size)
"""
function calculate_qq_grid_layout(n_heights::Int)::@NamedTuple{cols::Int, rows::Int, size::Tuple{Int, Int}}
    # Predefined optimal layouts for small numbers
    layout_configs = Dict(
        1 => (cols=1, rows=1, size=(800, 800)),      # Single large plot
        2 => (cols=2, rows=1, size=(1000, 500)),     # Side by side
        3 => (cols=3, rows=1, size=(1200, 400)),     # Horizontal row
        4 => (cols=2, rows=2, size=(800, 800))       # Square grid
    )
    
    if haskey(layout_configs, n_heights)
        return layout_configs[n_heights]
    else
        # For 5+ heights, use dynamic calculation
        n_cols = min(4, n_heights)  # Max 4 columns
        n_rows = ceil(Int, n_heights / n_cols)
        figure_size = (n_cols * 350, n_rows * 350)
        return (cols=n_cols, rows=n_rows, size=figure_size)
    end
end

"""
    generate_detailed_qq_plots_from_raw_data(wind_data_dict::Dict, mast_name::String, output_dir::String, wind_speed_type::String)::Union{String, Nothing}

Generate a detailed grid plot of Q-Q plots using the actual 5-day maxima data.

# Arguments
- `wind_data_dict::Dict`: Dictionary mapping heights to their 5-day maxima data and Gumbel parameters
- `mast_name::String`: Mast name for plot title
- `output_dir::String`: Directory to save the plot
- `wind_speed_type::String`: Type of wind speed (sustained or extreme)

# Returns
- `String`: Path to the saved grid plot file, or Nothing if no data
"""
function generate_detailed_qq_plots_from_raw_data(wind_data_dict::Dict, mast_name::String, output_dir::String, wind_speed_type::String)::Union{String, Nothing}
    if isempty(wind_data_dict)
        return nothing
    end
    
    # Get heights and sort them
    heights = sort(collect(keys(wind_data_dict)), rev=true)
    n_heights = length(heights)
    
    if n_heights == 0
        return nothing
    end
    
    # Calculate optimal grid layout
    layout = calculate_qq_grid_layout(n_heights)
    n_cols, n_rows, figure_size = layout.cols, layout.rows, layout.size
    
    @info "Creating detailed $(n_rows)×$(n_cols) grid plot for $(n_heights) heights ($(wind_speed_type) wind speed) - size: $(figure_size)"
    
    # Create figure with optimized size
    fig = Figure(size=figure_size)
    
    # Generate individual Q-Q plots for each height
    for (idx, height) in enumerate(heights)
        # Calculate subplot position
        row = ceil(Int, idx / n_cols)
        col = ((idx - 1) % n_cols) + 1
        
        # Get data for this height
        height_info = wind_data_dict[height]
        five_day_maxima = height_info[:data]
        μ, β = height_info[:gumbel_params]
        
        # Sort data for empirical quantiles
        sorted_data = sort(five_day_maxima)
        n = length(sorted_data)
        
        # Calculate empirical quantiles (plotting positions)
        empirical_probs = collect(1:n) ./ (n + 1)
        
        # Calculate theoretical Gumbel quantiles
        neg_log_probs = -log.(empirical_probs)
        log_neg_log_probs = log.(neg_log_probs)
        theoretical_quantiles = μ .- β .* log_neg_log_probs
        
        # Generate 95% confidence bands using simplified method
        n_monte_carlo = 200  # Reduced for grid plot performance
        ci_df = generate_qq_monte_carlo_bands(empirical_probs, μ, β, n, n_monte_carlo)
        
        # Create subplot axis
        height_str = format_height(height)
        ax = Axis(fig[row, col],
            title="$(height_str)m (n=$(n))",
            xlabel=row == n_rows ? "Theoretical" : "",
            ylabel=col == 1 ? "Empirical" : "",
            titlesize=11,
            xlabelsize=9,
            ylabelsize=9
        )
        
        # Add confidence bands using native CairoMakie
        band!(ax, ci_df.quantiles, ci_df.lower, ci_df.upper, color=(:lightgray, 0.3))
        
        # Add diagonal reference line
        min_val = minimum([minimum(theoretical_quantiles), minimum(sorted_data)])
        max_val = maximum([maximum(theoretical_quantiles), maximum(sorted_data)])
        lines!(ax, [min_val, max_val], [min_val, max_val], linestyle=:dash, linewidth=2, color=:red)
        
        # Plot Q-Q points
        scatter!(ax, theoretical_quantiles, sorted_data, markersize=5, color=:blue)
    end
    
    # Add overall title
    wind_type_chinese = wind_speed_type == "sustained" ? "持续风速" : "极端风速"
    Label(fig[0, :], "$(mast_name) - $(wind_type_chinese)Gumbel分布Q-Q图网格 (95%置信带)", 
          fontsize=14, font="bold")
    
    # Save the plot
    plot_path = joinpath(output_dir, "gumbel_qq_detailed_grid_$(wind_speed_type).png")
    save(plot_path, fig, size=(1000, 1000))

    @info "Generated detailed Gumbel Q-Q grid plot for $(mast_name) $(wind_speed_type) wind speeds: $(plot_path)"
    return plot_path
end

"""
    analyze_fifty_years_extreme_wind(config::ReportTimeSeriesConfig)

Analyze 50-year extreme wind speeds using three methods for all masts.
Calculates both 50年最大持续风速 (sustained) and 50年极大极端风速 (extreme) according to IEC standards.
All results include conversion to standard air density (1.225 kg/m³).

# Arguments
- `config::ReportTimeSeriesConfig`: Analysis configuration with multiple masts

# Returns
- `Dict{String, Dict}`: Dictionary mapping mast names to their extreme wind analysis results
"""
function analyze_fifty_years_extreme_wind(config::ReportTimeSeriesConfig)
    # Process all masts using functional approach
    mast_results = config.masts |>
        masts -> map(masts) do mast
        output_dir = get_output_path(config, mast.name, "fifty-years")
        
        # Find average wind speed sensors (heights >= min_plot_height)
        avg_speed_sensors = filter(s -> s.sensorType == "WindSpeed" &&
                                       s.statType == "avg" &&
                                       s.height >= config.min_plot_height,
                                  mast.timeSeriesData.sensors)

        # Find maximum wind speed sensors (heights >= min_plot_height)
        max_speed_sensors = filter(s -> s.sensorType == "WindSpeed" &&
                                       s.statType == "max" &&
                                       s.height >= config.min_plot_height,
                                  mast.timeSeriesData.sensors)

        if isempty(avg_speed_sensors) && isempty(max_speed_sensors)
            @warn "No wind speed sensors found at heights >= $(config.min_plot_height)m for mast $(mast.name)"
            return nothing
        end
        
        # Check if air density is available for standard density conversion
        has_air_density = !isnothing(mast.airDensity)
        if !has_air_density
            @warn "No air density configuration found for mast $(mast.name). Using standard air density for all calculations."
        end
        
        # Create separate results DataFrames for each method
        method1_results_df = DataFrame(
            height = Float64[],
            method = String[],
            sustained_wind_speed = Float64[],
            sustained_wind_speed_1225_density = Float64[],
            extreme_wind_speed = Float64[],
            extreme_wind_speed_1225_density = Float64[],
            air_density = Float64[],
            average_wind_speed = Float64[]
        )
        
        method2_sustained_results_df = DataFrame(
            height = Float64[],
            method = String[],
            wind_speed_type = String[],
            wind_speed = Float64[],
            wind_speed_1225_density = Float64[],
            air_density = Float64[],
            gumbel_location = Float64[],
            gumbel_scale = Float64[],
            sample_count = Int[],
            sample_mean = Float64[],
            sample_std = Float64[],
            qq_plot_path = String[]
        )
        
        method2_extreme_results_df = DataFrame(
            height = Float64[],
            method = String[],
            wind_speed_type = String[],
            wind_speed = Float64[],
            wind_speed_1225_density = Float64[],
            air_density = Float64[],
            gumbel_location = Float64[],
            gumbel_scale = Float64[],
            sample_count = Int[],
            sample_mean = Float64[],
            sample_std = Float64[],
            qq_plot_path = String[]
        )
        
        method3_sustained_results_df = DataFrame(
            height = Float64[],
            method = String[],
            wind_speed_type = String[],
            wind_speed = Float64[],
            wind_speed_1225_density = Float64[],
            air_density = Float64[],
            observed_max = Float64[],
            sample_count = Int[]
        )
        
        method3_extreme_results_df = DataFrame(
            height = Float64[],
            method = String[],
            wind_speed_type = String[],
            wind_speed = Float64[],
            wind_speed_1225_density = Float64[],
            air_density = Float64[],
            observed_max = Float64[],
            sample_count = Int[]
        )
        
        # Process Method 1: 5 times average wind speed (calculates both sustained and extreme)
        method1_results = avg_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 1 (5倍平均风速法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method1_sustained_and_extreme(mast, sensor, air_density)
            end |>
            results -> filter(!isnothing, results)
        
        # Add Method 1 results to DataFrame
        for result in method1_results
            push!(method1_results_df, result)
        end
        
        # Process Method 2 for sustained wind speeds (using average wind speed sensors)
        method2_sustained_results = avg_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 2 sustained (五日最大风速法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method2_sustained(mast, sensor, air_density, output_dir)
            end |>
            results -> filter(!isnothing, results)
        
        # Collect 5-day maxima data for sustained grid plot
        method2_sustained_raw_data = Dict{Float64, Dict{Symbol, Any}}()
        for sensor in avg_speed_sensors
            wind_speeds = mast.timeSeriesData.df[:, sensor.columnName]
            timestamps = mast.timeSeriesData.df[:, :timestamp]
            five_day_maxima = extract_five_day_maxima(Vector{Union{Missing, Float64}}(wind_speeds), timestamps)
            
            if length(five_day_maxima) >= 5
                gumbel_params = fit_gumbel_distribution(five_day_maxima)
                if !isnothing(gumbel_params)
                    method2_sustained_raw_data[sensor.height] = Dict(
                        :data => five_day_maxima,
                        :gumbel_params => gumbel_params
                    )
                end
            end
        end
        
        # Add Method 2 sustained results to DataFrame
        for result in method2_sustained_results
            push!(method2_sustained_results_df, result)
        end
        
        # Process Method 2 for extreme wind speeds (using maximum wind speed sensors)
        method2_extreme_results = max_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 2 extreme (五日最大风速法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method2_extreme(mast, sensor, air_density, output_dir)
            end |>
            results -> filter(!isnothing, results)
        
        # Collect 5-day maxima data for extreme grid plot
        method2_extreme_raw_data = Dict{Float64, Dict{Symbol, Any}}()
        for sensor in max_speed_sensors
            wind_speeds = mast.timeSeriesData.df[:, sensor.columnName]
            timestamps = mast.timeSeriesData.df[:, :timestamp]
            five_day_maxima = extract_five_day_maxima(Vector{Union{Missing, Float64}}(wind_speeds), timestamps)
            
            if length(five_day_maxima) >= 5
                gumbel_params = fit_gumbel_distribution(five_day_maxima)
                if !isnothing(gumbel_params)
                    method2_extreme_raw_data[sensor.height] = Dict(
                        :data => five_day_maxima,
                        :gumbel_params => gumbel_params
                    )
                end
            end
        end
        
        # Add Method 2 extreme results to DataFrame
        for result in method2_extreme_results
            push!(method2_extreme_results_df, result)
        end
        
        # Generate grid plots for Method 2
        method2_sustained_grid_plot_path = nothing
        method2_extreme_grid_plot_path = nothing
        
        if !isempty(method2_sustained_raw_data)
            method2_sustained_grid_plot_path = generate_detailed_qq_plots_from_raw_data(
                method2_sustained_raw_data, mast.name, output_dir, "sustained"
            )
        end
        
        if !isempty(method2_extreme_raw_data)
            method2_extreme_grid_plot_path = generate_detailed_qq_plots_from_raw_data(
                method2_extreme_raw_data, mast.name, output_dir, "extreme"
            )
        end
        
        # Process Method 3 for sustained wind speeds (using average wind speed sensors)
        method3_sustained_results = avg_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 3 sustained (极端风速模型法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method3_sustained(mast, sensor, air_density)
            end |>
            results -> filter(!isnothing, results)
        
        # Add Method 3 sustained results to DataFrame
        for result in method3_sustained_results
            push!(method3_sustained_results_df, result)
        end
        
        # Process Method 3 for extreme wind speeds (using maximum wind speed sensors)
        method3_extreme_results = max_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 3 extreme (极端风速模型法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method3_extreme(mast, sensor, air_density)
            end |>
            results -> filter(!isnothing, results)
        
        # Add Method 3 extreme results to DataFrame
        for result in method3_extreme_results
            push!(method3_extreme_results_df, result)
        end
        
        # Return results for this mast
        if (!isempty(method1_results_df) || !isempty(method2_sustained_results_df) || 
            !isempty(method2_extreme_results_df) || !isempty(method3_sustained_results_df) || 
            !isempty(method3_extreme_results_df))
            
            # Save detailed results to separate CSV files
            if !isempty(method1_results_df)
                CSV.write(joinpath(output_dir, "method1_sustained_and_extreme.csv"), method1_results_df)
            end
            if !isempty(method2_sustained_results_df)
                CSV.write(joinpath(output_dir, "method2_sustained.csv"), method2_sustained_results_df)
            end
            if !isempty(method2_extreme_results_df)
                CSV.write(joinpath(output_dir, "method2_extreme.csv"), method2_extreme_results_df)
            end
            if !isempty(method3_sustained_results_df)
                CSV.write(joinpath(output_dir, "method3_sustained.csv"), method3_sustained_results_df)
            end
            if !isempty(method3_extreme_results_df)
                CSV.write(joinpath(output_dir, "method3_extreme.csv"), method3_extreme_results_df)
            end
            
            # Generate summary table for typst report
            generate_fifty_years_report(method1_results_df, method2_sustained_results_df, method2_extreme_results_df, 
                                      method3_sustained_results_df, method3_extreme_results_df, mast.name, output_dir, config,
                                      method2_sustained_grid_plot_path, method2_extreme_grid_plot_path)
            
            @info "Generated 50-year extreme wind analysis for mast $(mast.name)"
            
            # Return mast result
            (
                name = mast.name,
                data = Dict(
                    "method1" => method1_results_df,
                    "method2_sustained" => method2_sustained_results_df,
                    "method2_extreme" => method2_extreme_results_df,
                    "method3_sustained" => method3_sustained_results_df,
                    "method3_extreme" => method3_extreme_results_df
                )
            )
        else
            @warn "No extreme wind results generated for mast $(mast.name)"
            nothing
        end
    end |>
    results -> filter(!isnothing, results)
    
    # Convert to final results dictionary
    results = mast_results |>
        mast_list -> Dict(result.name => result.data for result in mast_list)
    
    return results
end

"""
    generate_fifty_years_report(method1_results_df::DataFrame, method2_sustained_results_df::DataFrame, method2_extreme_results_df::DataFrame, method3_sustained_results_df::DataFrame, method3_extreme_results_df::DataFrame, mast_name::String, output_dir::String, config::ReportTimeSeriesConfig, method2_sustained_grid_plot_path::Union{String, Nothing}, method2_extreme_grid_plot_path::Union{String, Nothing})

Generate a comprehensive 50-year extreme wind analysis report including tables in typst format.

# Arguments
- `method1_results_df::DataFrame`: DataFrame containing Method 1 (5倍平均风速法) results with both sustained and extreme
- `method2_sustained_results_df::DataFrame`: DataFrame containing Method 2 sustained wind speed results
- `method2_extreme_results_df::DataFrame`: DataFrame containing Method 2 extreme wind speed results
- `method3_sustained_results_df::DataFrame`: DataFrame containing Method 3 sustained wind speed results
- `method3_extreme_results_df::DataFrame`: DataFrame containing Method 3 extreme wind speed results
- `mast_name::String`: Name of the mast
- `output_dir::String`: Directory to save the report
- `config::ReportTimeSeriesConfig`: Analysis configuration
- `method2_sustained_grid_plot_path::Union{String, Nothing}`: Path to sustained wind speed grid plot
- `method2_extreme_grid_plot_path::Union{String, Nothing}`: Path to extreme wind speed grid plot
"""
function generate_fifty_years_report(method1_results_df::DataFrame, method2_sustained_results_df::DataFrame, method2_extreme_results_df::DataFrame, method3_sustained_results_df::DataFrame, method3_extreme_results_df::DataFrame, mast_name::String, output_dir::String, config::ReportTimeSeriesConfig, method2_sustained_grid_plot_path::Union{String, Nothing}, method2_extreme_grid_plot_path::Union{String, Nothing})
    if (isempty(method1_results_df) && isempty(method2_sustained_results_df) && 
        isempty(method2_extreme_results_df) && isempty(method3_sustained_results_df) && 
        isempty(method3_extreme_results_df))
        @warn "No extreme wind analysis data provided for report generation"
        return nothing
    end
    
    typst_path = joinpath(output_dir, "fifty-years.typ")
    if isfile(typst_path)
        rm(typst_path)
    end
    
    # Create the Gumbel parameters table for Method 2 if data exists
    gumbel_sustained_table_df = if !isempty(method2_sustained_results_df)
        gumbel_df = DataFrame()
        for height in sort(unique(method2_sustained_results_df.height), rev=true)
            method2_data = filter(row -> row.height == height, method2_sustained_results_df)
            if nrow(method2_data) > 0
                push!(gumbel_df, (
                    height = height,
                    wind_speed_type = "持续风速",
                    gumbel_location = round(method2_data[1, :gumbel_location], digits=3),
                    gumbel_scale = round(method2_data[1, :gumbel_scale], digits=3),
                    sample_count = method2_data[1, :sample_count],
                    sample_mean = round(method2_data[1, :sample_mean], digits=2),
                    sample_std = round(method2_data[1, :sample_std], digits=2)
                ))
            end
        end
        
        rename!(gumbel_df,
            :height => "高度(m)",
            :wind_speed_type => "风速类型",
            :gumbel_location => "Gumbel位置参数(μ)",
            :gumbel_scale => "Gumbel尺度参数(β)",
            :sample_count => "样本数量",
            :sample_mean => "样本均值(m/s)",
            :sample_std => "样本标准差(m/s)"
        )
        
        gumbel_df
    else
        DataFrame()
    end
    
    gumbel_extreme_table_df = if !isempty(method2_extreme_results_df)
        gumbel_df = DataFrame()
        for height in sort(unique(method2_extreme_results_df.height), rev=true)
            method2_data = filter(row -> row.height == height, method2_extreme_results_df)
            if nrow(method2_data) > 0
                push!(gumbel_df, (
                    height = height,
                    wind_speed_type = "极端风速",
                    gumbel_location = round(method2_data[1, :gumbel_location], digits=3),
                    gumbel_scale = round(method2_data[1, :gumbel_scale], digits=3),
                    sample_count = method2_data[1, :sample_count],
                    sample_mean = round(method2_data[1, :sample_mean], digits=2),
                    sample_std = round(method2_data[1, :sample_std], digits=2)
                ))
            end
        end
        
        rename!(gumbel_df,
            :height => "高度(m)",
            :wind_speed_type => "风速类型",
            :gumbel_location => "Gumbel位置参数(μ)",
            :gumbel_scale => "Gumbel尺度参数(β)",
            :sample_count => "样本数量",
            :sample_mean => "样本均值(m/s)",
            :sample_std => "样本标准差(m/s)"
        )
        
        gumbel_df
    else
        DataFrame()
    end
    
    open(typst_path, "w") do io
        println(io, "== 测风塔$(mast_name) 50年一遇最大风速")
        println(io, "")
        println(io, "根据IEC 61400-1标准，50年重现期风速分为两类：")
        println(io, raw"- 50年最大持续风速 $ V_{\"ref\"} $ ：50年重现期10分钟平均风速")
        println(io, raw"- 50年极大极端风速 $ V_{\"e50\"} $ ：50年重现期10分钟最大风速")
        println(io, "")
        println(io, raw"两者之间的关系为：$ V_{\"e50\"} = 1.4 times V_{\"ref\"} $")
        println(io, "")
        
        # Method 1 Section
        if !isempty(method1_results_df)
            println(io, "== 方法一：5倍平均风速法")
            println(io, "")
            println(io, "根据IEC61400-1标准，50年一遇最大持续风速约为年平均风速的5倍。")
            println(io, "50年极大极端风速则在此基础上乘以1.4系数。")
            println(io, "")
            println(io, "计算公式：")
            println(io, raw"$V_{\"ref\"} = 5 times V_{\"avg\"}$")
            println(io, raw"$V_{\"e50\"} = 1.4 times V_{\"ref\"} = 7 times V_{\"avg\"}$")
            println(io, "")
            println(io, "其中：")
            println(io, raw"- $V_{\"ref\"}$：50年最大持续风速")
            println(io, raw"- $V_{\"e50\"}$：50年极大极端风速")
            println(io, raw"- $V_{\"avg\"}$：观测期间平均风速")
            println(io, "")
            
            # Create Method 1 table
            method1_table_df = DataFrame()
            for height in sort(unique(method1_results_df.height), rev=true)
                method1_data = filter(row -> row.height == height, method1_results_df)
                if nrow(method1_data) > 0
                    push!(method1_table_df, (
                        height = height,
                        sustained_wind_speed = round(method1_data[1, :sustained_wind_speed], digits=2),
                        sustained_wind_speed_1225 = round(method1_data[1, :sustained_wind_speed_1225_density], digits=2),
                        extreme_wind_speed = round(method1_data[1, :extreme_wind_speed], digits=2),
                        extreme_wind_speed_1225 = round(method1_data[1, :extreme_wind_speed_1225_density], digits=2)
                    ))
                end
            end
            
            rename!(method1_table_df,
                :height => "高度(m)",
                :sustained_wind_speed => "50年最大持续风速(m/s)",
                :sustained_wind_speed_1225 => "标准密度持续风速(m/s)",
                :extreme_wind_speed => "50年极大极端风速(m/s)",
                :extreme_wind_speed_1225 => "标准密度极端风速(m/s)"
            )
            
            method1_table = simple_table(method1_table_df)
            println(io, "表格：测风塔$(mast_name) 方法一结果")
            println(io, "")
            show(io, MIME"text/typst"(), method1_table)
            println(io, "")
        end
        
        # Method 2 Section
        if !isempty(method2_sustained_results_df) || !isempty(method2_extreme_results_df)
            println(io, "== 方法二：五日最大风速法（Gumbel分布）")
            println(io, "")
            println(io, "根据 《NB/T 31147-2018 风电场工程风能资源测量与评估技术规范》，风速分布遵循 Gumbel 分布。五日风速最大法将观测数据按5天为周期进行分组，提取每个周期内的平均值通道的最大值（持续风速）和最大值通道（极端风速）的最大值， 然后对这些极值样本拟合Gumbel分布，最后外推至50年重现期。")
            println(io, "")
            println(io, "- 50年最大持续风速：对平均风速数据应用五日最大法")
            println(io, "- 50年极大极端风速：对最大风速数据应用五日最大法")
            println(io, "")
            println(io, "Gumbel分布的累积分布函数为：")
            println(io, "")
            println(io, raw"$ F(x) = exp(-exp(-(x-mu)/beta)) $")
            println(io, "")
            println(io, "50年重现期风速计算公式：")
            println(io, "")
            println(io, raw"$ V_{50} = mu - beta ln(-ln(1 - 1/T)) $")
            println(io, "")
            println(io, "其中：")
            println(io, raw"- $mu$：Gumbel分布位置参数")
            println(io, raw"- $beta$：Gumbel分布尺度参数")
            println(io, raw"- $T = 50 times 365/5 = 3650$：重现期（5天周期数）")
            println(io, raw"- $V_{50}$：50年重现期风速")
            println(io, "")
            
            # Create combined Method 2 table for both sustained and extreme
            method2_combined_table_df = DataFrame()
            
            # Add sustained results
            if !isempty(method2_sustained_results_df)
                for height in sort(unique(method2_sustained_results_df.height), rev=true)
                    method2_data = filter(row -> row.height == height, method2_sustained_results_df)
                    if nrow(method2_data) > 0
                        push!(method2_combined_table_df, (
                            height = height,
                            wind_speed_type = "50年最大持续风速",
                            wind_speed = round(method2_data[1, :wind_speed], digits=2),
                            wind_speed_1225 = round(method2_data[1, :wind_speed_1225_density], digits=2)
                        ))
                    end
                end
            end
            
            # Add extreme results
            if !isempty(method2_extreme_results_df)
                for height in sort(unique(method2_extreme_results_df.height), rev=true)
                    method2_data = filter(row -> row.height == height, method2_extreme_results_df)
                    if nrow(method2_data) > 0
                        push!(method2_combined_table_df, (
                            height = height,
                            wind_speed_type = "50年极大极端风速",
                            wind_speed = round(method2_data[1, :wind_speed], digits=2),
                            wind_speed_1225 = round(method2_data[1, :wind_speed_1225_density], digits=2)
                        ))
                    end
                end
            end
            
            if !isempty(method2_combined_table_df)
                rename!(method2_combined_table_df,
                    :height => "高度(m)",
                    :wind_speed_type => "风速类型",
                    :wind_speed => "五日最大风速法(m/s)",
                    :wind_speed_1225 => "标准密度风速(m/s)"
                )
                
                method2_table = simple_table(method2_combined_table_df)
                println(io, "表格：测风塔$(mast_name) 方法二结果")
                println(io, "")
                show(io, MIME"text/typst"(), method2_table)
                println(io, "")
            end
            
            # Gumbel parameters table for sustained
            if !isempty(gumbel_sustained_table_df)
                gumbel_table = simple_table(gumbel_sustained_table_df)
                println(io, "表格：测风塔$(mast_name) Gumbel分布拟合参数（持续风速）")
                println(io, "")
                show(io, MIME"text/typst"(), gumbel_table)
                println(io, "")
            end
            
            # Gumbel parameters table for extreme
            if !isempty(gumbel_extreme_table_df)
                gumbel_table = simple_table(gumbel_extreme_table_df)
                println(io, "表格：测风塔$(mast_name) Gumbel分布拟合参数（极端风速）")
                println(io, "")
                show(io, MIME"text/typst"(), gumbel_table)
                println(io, "")
            end
            
            # Q-Q plots section
            println(io, "=== Gumbel分布拟合检验（Q-Q图网格）")
            println(io, "")
            println(io, "Q-Q图（分位数-分位数图）用于检验数据是否符合理论分布。图中包含通过蒙特卡洛模拟生成的95%置信带，")
            println(io, "用于评估拟合优度。如果数据点位于置信带内，")
            println(io, "说明数据与Gumbel分布拟合良好；如果数据点显著偏离置信带，则表明分布假设可能不合适。")
            println(io, "")
            println(io, "*95%置信带检验指标*：")
            println(io, "- 数据点大部分位于灰色置信带内：拟合良好")
            println(io, "- 数据点系统性超出置信带：可能存在分布偏差")
            println(io, "- 尾部数据点显著超出置信带：极值预测需谨慎")
            println(io, "")
            println(io, "为便于对比分析，将所有高度的Q-Q图整合为网格布局显示。")
            println(io, "")
            
            # Include grid plot for sustained analysis
            if !isnothing(method2_sustained_grid_plot_path)
                println(io, "")
                println(io, "#figure(")
                println(io, "  image(\"./gumbel_qq_detailed_grid_sustained.png\", width: 85%),")
                println(io, "  caption: [测风塔$(mast_name) 最大持续风速Gumbel分布Q-Q图网格检验（95%置信带）]")
                println(io, ")")
                println(io, "")
            end
            
            # Include grid plot for extreme analysis
            if !isnothing(method2_extreme_grid_plot_path)
                println(io, "==== 极端风速Q-Q图网格")
                println(io, "")
                println(io, "#figure(")
                println(io, "  image(\"./gumbel_qq_detailed_grid_extreme.png\", width: 85%),")
                println(io, "  caption: [测风塔$(mast_name) 极大极端风速Gumbel分布Q-Q图网格检验（95%置信带）]")
                println(io, ")")
                println(io, "")
            end
        end
        
        # Method 3 Section
        if !isempty(method3_sustained_results_df) || !isempty(method3_extreme_results_df)
            println(io, "== 方法三：极端风速模型（EWM）法")
            println(io, "")
            println(io, "根据《风力发电机组设计要求》（GB/T 18451.1-2022）推荐的方法，对于稳态极端风速模型，")
            println(io, "风电场50年重现期风速可按观测期最大风速的1.25倍计算。")
            println(io, "")
            println(io, raw"- 50年最大持续风速：$ V_{\"ref\"} = 1.25 times V_{\"max avg\"} $")
            println(io, raw"- 50年极大极端风速：$ V_{\"e50\"} = 1.25 times V_{\"max max\"} $")
            println(io, "")
            println(io, "计算公式：")
            println(io, raw"$V_{\"50\"} = 1.25 times V_{\"annual max\"}$")
            println(io, "")
            println(io, "其中：")
            println(io, raw"- $V_{\"50\"}$：50年重现期风速")
            println(io, raw"- $V_{\"annual max\"}$：观测期内相应类型的最大风速")
            println(io, "")
            println(io, "本方法分别对平均风速和最大风速的观测期最大值")
            println(io, "乘以1.25系数得到对应的50年重现期风速。")
            println(io, "")
            
            # Create combined Method 3 table for both sustained and extreme
            method3_combined_table_df = DataFrame()
            
            # Add sustained results
            if !isempty(method3_sustained_results_df)
                for height in sort(unique(method3_sustained_results_df.height), rev=true)
                    method3_data = filter(row -> row.height == height, method3_sustained_results_df)
                    if nrow(method3_data) > 0
                        push!(method3_combined_table_df, (
                            height = height,
                            wind_speed_type = "50年最大持续风速",
                            observed_max = round(method3_data[1, :observed_max], digits=2),
                            wind_speed = round(method3_data[1, :wind_speed], digits=2),
                            wind_speed_1225 = round(method3_data[1, :wind_speed_1225_density], digits=2)
                        ))
                    end
                end
            end
            
            # Add extreme results
            if !isempty(method3_extreme_results_df)
                for height in sort(unique(method3_extreme_results_df.height), rev=true)
                    method3_data = filter(row -> row.height == height, method3_extreme_results_df)
                    if nrow(method3_data) > 0
                        push!(method3_combined_table_df, (
                            height = height,
                            wind_speed_type = "50年极大极端风速",
                            observed_max = round(method3_data[1, :observed_max], digits=2),
                            wind_speed = round(method3_data[1, :wind_speed], digits=2),
                            wind_speed_1225 = round(method3_data[1, :wind_speed_1225_density], digits=2)
                        ))
                    end
                end
            end
            
            if !isempty(method3_combined_table_df)
                rename!(method3_combined_table_df,
                    :height => "高度(m)",
                    :wind_speed_type => "风速类型",
                    :observed_max => "观测最大值(m/s)",
                    :wind_speed => "50年重现期风速(m/s)",
                    :wind_speed_1225 => "标准密度风速(m/s)"
                )
                
                method3_table = simple_table(method3_combined_table_df)
                println(io, "表格：测风塔$(mast_name) 方法三结果")
                println(io, "")
                show(io, MIME"text/typst"(), method3_table)
                println(io, "")
            end
        end
        
        # Comparison section if multiple methods have results
        println(io, "== 测风塔$(mast_name)方法对比")
        println(io, "")
        
        # Create sustained wind speed comparison table
        if (!isempty(method1_results_df) || !isempty(method2_sustained_results_df) || !isempty(method3_sustained_results_df))
            println(io, "=== 测风塔$(mast_name) 50年最大持续风速对比")
            println(io, "")
            
            sustained_comparison_df = DataFrame()
            all_heights_sustained = Float64[]
            if !isempty(method1_results_df)
                append!(all_heights_sustained, method1_results_df.height)
            end
            if !isempty(method2_sustained_results_df)
                append!(all_heights_sustained, method2_sustained_results_df.height)
            end
            if !isempty(method3_sustained_results_df)
                append!(all_heights_sustained, method3_sustained_results_df.height)
            end
            heights_sustained = sort(unique(all_heights_sustained), rev=true)
            
            for height in heights_sustained
                method1_data = filter(row -> row.height == height, method1_results_df)
                method2_data = filter(row -> row.height == height, method2_sustained_results_df)
                method3_data = filter(row -> row.height == height, method3_sustained_results_df)
                
                method1_value = nrow(method1_data) > 0 ? round(method1_data[1, :sustained_wind_speed_1225_density], digits=2) : missing
                method2_value = nrow(method2_data) > 0 ? round(method2_data[1, :wind_speed_1225_density], digits=2) : missing
                method3_value = nrow(method3_data) > 0 ? round(method3_data[1, :wind_speed_1225_density], digits=2) : missing
                
                push!(sustained_comparison_df, (
                    height = height,
                    method1_1225 = method1_value,
                    method2_1225 = method2_value,
                    method3_1225 = method3_value
                ))
            end
            
            rename!(sustained_comparison_df,
                :height => "高度(m)",
                :method1_1225 => "5倍平均风速法(m/s)",
                :method2_1225 => "五日最大风速法(m/s)",
                :method3_1225 => "极端风速模型法(m/s)"
            )
            
            sustained_comparison_table = simple_table(sustained_comparison_df)
            println(io, "表格：测风塔$(mast_name) 50年最大持续风速对比（标准密度）")
            println(io, "")
            show(io, MIME"text/typst"(), sustained_comparison_table)
            println(io, "")
        end
        
        # Create extreme wind speed comparison table
        if (!isempty(method1_results_df) || !isempty(method2_extreme_results_df) || !isempty(method3_extreme_results_df))
            println(io, "=== 测风塔$(mast_name) 50年极大极端风速对比")
            println(io, "")
            
            extreme_comparison_df = DataFrame()
            all_heights_extreme = Float64[]
            if !isempty(method1_results_df)
                append!(all_heights_extreme, method1_results_df.height)
            end
            if !isempty(method2_extreme_results_df)
                append!(all_heights_extreme, method2_extreme_results_df.height)
            end
            if !isempty(method3_extreme_results_df)
                append!(all_heights_extreme, method3_extreme_results_df.height)
            end
            heights_extreme = sort(unique(all_heights_extreme), rev=true)
            
            for height in heights_extreme
                method1_data = filter(row -> row.height == height, method1_results_df)
                method2_data = filter(row -> row.height == height, method2_extreme_results_df)
                method3_data = filter(row -> row.height == height, method3_extreme_results_df)
                
                method1_value = nrow(method1_data) > 0 ? round(method1_data[1, :extreme_wind_speed_1225_density], digits=2) : missing
                method2_value = nrow(method2_data) > 0 ? round(method2_data[1, :wind_speed_1225_density], digits=2) : missing
                method3_value = nrow(method3_data) > 0 ? round(method3_data[1, :wind_speed_1225_density], digits=2) : missing
                
                push!(extreme_comparison_df, (
                    height = height,
                    method1_1225 = method1_value,
                    method2_1225 = method2_value,
                    method3_1225 = method3_value
                ))
            end
            
            rename!(extreme_comparison_df,
                :height => "高度(m)",
                :method1_1225 => "5倍平均风速法(m/s)",
                :method2_1225 => "五日最大风速法(m/s)",
                :method3_1225 => "极端风速模型法(m/s)"
            )
            
            extreme_comparison_table = simple_table(extreme_comparison_df)
            println(io, "表格：测风塔$(mast_name) 50年极大极端风速对比（标准密度）")
            println(io, "")
            show(io, MIME"text/typst"(), extreme_comparison_table)
            println(io, "")
        end
        
        # Add IEC reference values section
        println(io, "")
        println(io, "== IEC 61400-1标准参考值")
        println(io, "")
        println(io, "根据IEC 61400-1风力发电机组设计标准，不同风区等级对应的50年一遇极端风速参考值如下：")
        println(io, "")
        
        # Create IEC reference table
        iec_reference_df = DataFrame(
            wind_class = ["I类风区", "II类风区", "III类风区", "S类风区"],
            vref = [50.0, 42.5, 37.5, "场址专用"],
            ve50 = [70.0, 59.5, 52.5, "场址专用"],
        )
        
        rename!(iec_reference_df,
            :wind_class => "风区等级",
            :vref => "最大持续风速Vref(m/s)",
            :ve50 => "极大极端风速Ve50(m/s)",
        )
        
        iec_table = simple_table(iec_reference_df)
        println(io, "表格：IEC 61400-1风区等级与50年极端风速对照")
        println(io, "")
        show(io, MIME"text/typst"(), iec_table)
        println(io, "")
        println(io, "*说明*：")
        println(io, "- Vref为轮毂高度处的参考风速（50年重现期）")
        println(io, raw"- Ve50 = 1.4 × Vref（极端风速模型）")
        println(io, "- 上表数值为IEC标准在海平面、标准大气密度条件下的参考值")
        println(io, "- 实际工程应用中需根据具体场址条件进行修正")
    end
    
    @info "Generated 50-year extreme wind report for mast $(mast_name) at $(typst_path)"
end

export analyze_fifty_years_extreme_wind, analyze_method1_sustained_and_extreme, analyze_method2_sustained, analyze_method2_extreme, analyze_method3_sustained, analyze_method3_extreme, generate_fifty_years_report, generate_detailed_qq_plots_from_raw_data

end # module 