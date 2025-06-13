module FiftyYearsExtremeWind

using DataFrames
using CSV
using Statistics
using Distributions
using Dates
using SummaryTables
using Optim

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path
import ..AirDensity: calculate_air_density

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
    try
        result = optimize(neg_log_likelihood, [μ_init, β_init], LBFGS())
        
        if Optim.converged(result)
            μ, β = Optim.minimizer(result)
            return (μ, β)
        else
            @warn "Gumbel optimization did not converge, using method of moments"
            return (μ_init, β_init)
        end
    catch e
        @warn "Gumbel fitting failed: $e, using method of moments"
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
        groups -> combine(groups, :wind_speed => maximum => :max_wind_speed) |>
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
    analyze_method1_five_times_average(mast::MastAnalyzeConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}

Analyze extreme wind speed using Method 1: 5 times average wind speed.

# Arguments
- `mast::MastAnalyzeConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Average wind speed sensor (statType="avg")
- `air_density::Float64`: Air density at sensor height

# Returns
- `NamedTuple`: Results containing extreme wind speeds and related data, or Nothing if analysis fails
"""
function analyze_method1_five_times_average(mast::MastAnalyzeConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}
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
                extreme_speed = 5.0 * avg_speed
                extreme_speed_1225 = convert_to_standard_air_density(extreme_speed, air_density)
                
                (
                    height = sensor.height,
                    method = "5倍平均风速法",
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
    analyze_method2_five_day_maxima(mast::MastAnalyzeConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}

Analyze extreme wind speed using Method 2: 5-day maximum wind speed method with Gumbel distribution.

# Arguments
- `mast::MastAnalyzeConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Maximum wind speed sensor (statType="max")
- `air_density::Float64`: Air density at sensor height

# Returns
- `NamedTuple`: Results containing extreme wind speeds and Gumbel parameters, or Nothing if analysis fails
"""
function analyze_method2_five_day_maxima(mast::MastAnalyzeConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}
    # Extract wind speed data
    wind_speeds = mast.timeSeriesData.df[:, sensor.columnName]
    timestamps = mast.timeSeriesData.df[:, :timestamp]
    
    # Extract 5-day maxima
    five_day_maxima = extract_five_day_maxima(wind_speeds, timestamps)
    
    if length(five_day_maxima) < 5
        @warn "Insufficient 5-day maximum samples ($(length(five_day_maxima))) for $(sensor.height)m"
        return nothing
    end
    
    @info "Found $(length(five_day_maxima)) five-day maximum samples for $(sensor.height)m"
    
    # Fit Gumbel distribution
    gumbel_params = fit_gumbel_distribution(five_day_maxima)
    
    if isnothing(gumbel_params)
        @warn "Failed to fit Gumbel distribution for $(sensor.height)m"
        return nothing
    end
    
    μ, β = gumbel_params
    
    # Calculate 50-year return period wind speed
    extreme_speed = calculate_gumbel_return_period_wind_speed(μ, β, 50.0)
    extreme_speed_1225 = convert_to_standard_air_density(extreme_speed, air_density)
    
    # Calculate sample statistics
    sample_mean = mean(five_day_maxima)
    sample_std = std(five_day_maxima)
    
    return (
        height = sensor.height,
        method = "五日最大风速法",
        extreme_wind_speed = extreme_speed,
        extreme_wind_speed_1225_density = extreme_speed_1225,
        air_density = air_density,
        gumbel_location = μ,
        gumbel_scale = β,
        sample_count = length(five_day_maxima),
        sample_mean = sample_mean,
        sample_std = sample_std
    )
end

"""
    analyze_method3_ewm(mast::MastAnalyzeConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}

Analyze extreme wind speed using Method 3: Extreme Wind Model (EWM) method based on GB/T 18451.1-2022.
This method calculates 50-year return period wind speed as 1.25 times the observed maximum wind speed.

# Arguments
- `mast::MastAnalyzeConfig`: Mast configuration with time series data
- `sensor::SensorColumn`: Maximum wind speed sensor (statType="max")
- `air_density::Float64`: Air density at sensor height

# Returns
- `NamedTuple`: Results containing extreme wind speeds, or Nothing if analysis fails
"""
function analyze_method3_ewm(mast::MastAnalyzeConfig, sensor::SensorColumn, air_density::Float64)::Union{NamedTuple, Nothing}
    # Extract and process maximum wind speed data using functional pipeline
    result = mast.timeSeriesData.df[:, sensor.columnName] |>
        speeds -> filter(x -> !ismissing(x) && !isnan(x) && x > 0, speeds) |>
        valid_speeds -> begin
            if isempty(valid_speeds)
                @warn "No valid maximum wind speed data found at $(sensor.height)m for Method 3 (EWM)"
                nothing
            else
                # Calculate Method 3 (EWM) results
                observed_max = maximum(valid_speeds)
                extreme_speed = 1.25 * observed_max  # V_e50 = 1.25 * V_max
                extreme_speed_1225 = convert_to_standard_air_density(extreme_speed, air_density)
                
                @info "Method 3 (EWM) for $(sensor.height)m: Max observed = $(round(observed_max, digits=2)) m/s, 50-year = $(round(extreme_speed, digits=2)) m/s"
                
                (
                    height = sensor.height,
                    method = "极端风速模型法",
                    extreme_wind_speed = extreme_speed,
                    extreme_wind_speed_1225_density = extreme_speed_1225,
                    air_density = air_density,
                    observed_max = observed_max,
                    sample_count = length(valid_speeds)
                )
            end
        end
    
    return result
end

"""
    analyze_fifty_years_extreme_wind(config::AnalyzeConfig)

Analyze 50-year extreme wind speeds using two methods for all masts.
All results include conversion to standard air density (1.225 kg/m³) according to IEC standards.

# Arguments
- `config::AnalyzeConfig`: Analysis configuration with multiple masts

# Returns
- `Dict{String, Dict}`: Dictionary mapping mast names to their extreme wind analysis results
"""
function analyze_fifty_years_extreme_wind(config::AnalyzeConfig)
    # Process all masts using functional approach
    mast_results = config.masts |>
        masts -> map(masts) do mast
        output_dir = get_output_path(config, mast.name, "fifty-years")
        
        # Find average wind speed sensors for Method 1 (heights >= 120m)
        avg_speed_sensors = filter(s -> s.sensorType == "WindSpeed" && 
                                       s.statType == "avg" && 
                                       s.height >= 120.0, 
                                  mast.timeSeriesData.sensors)
        
        # Find maximum wind speed sensors for Method 2 (heights >= 120m)
        max_speed_sensors = filter(s -> s.sensorType == "WindSpeed" && 
                                       s.statType == "max" && 
                                       s.height >= 120.0, 
                                  mast.timeSeriesData.sensors)
        
        if isempty(avg_speed_sensors) && isempty(max_speed_sensors)
            @warn "No wind speed sensors found at heights >= 120m for mast $(mast.name)"
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
            extreme_wind_speed = Float64[],
            extreme_wind_speed_1225_density = Float64[],
            air_density = Float64[],
            average_wind_speed = Float64[]
        )
        
        method2_results_df = DataFrame(
            height = Float64[],
            method = String[],
            extreme_wind_speed = Float64[],
            extreme_wind_speed_1225_density = Float64[],
            air_density = Float64[],
            gumbel_location = Float64[],
            gumbel_scale = Float64[],
            sample_count = Int[],
            sample_mean = Float64[],
            sample_std = Float64[]
        )
        
        method3_results_df = DataFrame(
            height = Float64[],
            method = String[],
            extreme_wind_speed = Float64[],
            extreme_wind_speed_1225_density = Float64[],
            air_density = Float64[],
            observed_max = Float64[],
            sample_count = Int[]
        )
        
        # Process Method 1: 5 times average wind speed using functional approach
        method1_results = avg_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 1 (5倍平均风速法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method1_five_times_average(mast, sensor, air_density)
            end |>
            results -> filter(!isnothing, results)
        
        # Add results to DataFrame
        for result in method1_results
            push!(method1_results_df, result)
        end
        
        # Process Method 2: 五日最大风速法 using functional approach
        method2_results = max_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 2 (五日最大风速法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method2_five_day_maxima(mast, sensor, air_density)
            end |>
            results -> filter(!isnothing, results)
        
        # Add results to DataFrame
        for result in method2_results
            push!(method2_results_df, result)
        end
        
        # Process Method 3: EWM method using functional approach
        method3_results = max_speed_sensors |> 
            sensors -> map(sensors) do sensor
                @info "Processing Method 3 (极端风速模型法) for mast $(mast.name) at $(sensor.height)m"
                
                # Calculate air density at sensor height
                air_density = has_air_density ? 
                              calculate_air_density(sensor.height, mast.airDensity) : 
                              STANDARD_AIR_DENSITY
                
                analyze_method3_ewm(mast, sensor, air_density)
            end |>
            results -> filter(!isnothing, results)
        
        # Add results to DataFrame
        for result in method3_results
            push!(method3_results_df, result)
        end
        
                    # Return results for this mast
            if !isempty(method1_results_df) || !isempty(method2_results_df) || !isempty(method3_results_df)
                # Save detailed results to separate CSV files
                if !isempty(method1_results_df)
                    CSV.write(joinpath(output_dir, "method1_five_times_average.csv"), method1_results_df)
                end
                if !isempty(method2_results_df)
                    CSV.write(joinpath(output_dir, "method2_five_day_maxima.csv"), method2_results_df)
                end
                if !isempty(method3_results_df)
                    CSV.write(joinpath(output_dir, "method3_ewm.csv"), method3_results_df)
                end
                
                # Generate summary table for typst report
                generate_fifty_years_report(method1_results_df, method2_results_df, method3_results_df, mast.name, output_dir, config)
                
                @info "Generated 50-year extreme wind analysis for mast $(mast.name)"
                
                # Return mast result
                (
                    name = mast.name,
                    data = Dict(
                        "method1" => method1_results_df,
                        "method2" => method2_results_df,
                        "method3" => method3_results_df
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
    generate_fifty_years_report(method1_results_df::DataFrame, method2_results_df::DataFrame, method3_results_df::DataFrame, mast_name::String, output_dir::String, config::AnalyzeConfig)

Generate a comprehensive 50-year extreme wind analysis report including tables in typst format.

# Arguments
- `method1_results_df::DataFrame`: DataFrame containing Method 1 (5倍平均风速法) results
- `method2_results_df::DataFrame`: DataFrame containing Method 2 (五日最大风速法) results
- `method3_results_df::DataFrame`: DataFrame containing Method 3 (极端风速模型法) results
- `mast_name::String`: Name of the mast
- `output_dir::String`: Directory to save the report
- `config::AnalyzeConfig`: Analysis configuration
"""
function generate_fifty_years_report(method1_results_df::DataFrame, method2_results_df::DataFrame, method3_results_df::DataFrame, mast_name::String, output_dir::String, config::AnalyzeConfig)
    if isempty(method1_results_df) && isempty(method2_results_df) && isempty(method3_results_df)
        @warn "No extreme wind analysis data provided for report generation"
        return nothing
    end
    
    typst_path = joinpath(output_dir, "fifty-years.typ")
    if isfile(typst_path)
        rm(typst_path)
    end
    
    # Create the Gumbel parameters table for Method 2 if data exists
    gumbel_table_df = if !isempty(method2_results_df)
        gumbel_df = DataFrame()
        for height in sort(unique(method2_results_df.height), rev=true)
            method2_data = filter(row -> row.height == height, method2_results_df)
            if nrow(method2_data) > 0
                push!(gumbel_df, (
                    height = height,
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
        println(io, "= 50年一遇最大风速")
        println(io, "")
        
        # Method 1 Section
        if !isempty(method1_results_df)
            println(io, "== 方法一：5倍平均风速法")
            println(io, "")
            println(io, "根据IEC61400-1标准，50年一遇最大风速约为年平均风速的5~7倍，本阶段暂采用测风塔代表年平均风速的五倍推求本风电场五十年一遇最大风速。")
            println(io, "")
            println(io, "计算公式：")
            println(io, raw"$V_{\"extreme\"} = 5 times V_{\"avg\"}$")
            println(io, "")
            println(io, "其中：")
            println(io, raw"- $V_{\"extreme\"}$：50年一遇最大风速")
            println(io, raw"- $V_{\"avg\"}$：观测期间平均风速")
            println(io, "")
            
            # Create Method 1 table
            method1_table_df = DataFrame()
            for height in sort(unique(method1_results_df.height), rev=true)
                method1_data = filter(row -> row.height == height, method1_results_df)
                if nrow(method1_data) > 0
                    push!(method1_table_df, (
                        height = height,
                        extreme_wind_speed = round(method1_data[1, :extreme_wind_speed], digits=2),
                        extreme_wind_speed_1225 = round(method1_data[1, :extreme_wind_speed_1225_density], digits=2)
                    ))
                end
            end
            
            rename!(method1_table_df,
                :height => "高度(m)",
                :extreme_wind_speed => "5倍平均风速(m/s)",
                :extreme_wind_speed_1225 => "标准密度风速(m/s)"
            )
            
            method1_table = simple_table(method1_table_df)
            println(io, "表格：测风塔$(mast_name) 方法一结果")
            println(io, "")
            show(io, MIME"text/typst"(), method1_table)
            println(io, "")
        end
        
        # Method 2 Section
        if !isempty(method2_results_df)
            println(io, "== 方法二：五日最大风速法（Gumbel分布）")
            println(io, "")
            println(io, "根据 《NB/T 31147-2018 风电场工程风能资源测量与评估技术规范》，风速分布遵循 Gumbel 分布。五日风速最大法将观测数据按5天为周期进行分组，提取每个周期内的最大风速，")
            println(io, "然后对这些极值样本拟合Gumbel分布，最后外推至50年重现期。")
            println(io, "")
            println(io, "=== 统计学原理")
            println(io, "")
            println(io, "本方法的统计学基础：")
            println(io, "- *采样周期*：5天")
            println(io, "- *目标重现期*：50年")
            println(io, "- *样本数量*：观测年数 × 73个5天周期/年")
            println(io, "- *统计重现期*：T = 50年 × 365天/年 ÷ 5天/周期 = 3650个5天周期")
            println(io, "- *概率计算*：P = 1 - 1/3650 = 99.973%（不超越概率）")
            println(io, "")
            println(io, "=== 理论基础")
            println(io, "")
            println(io, "Gumbel分布的累积分布函数为：")
            println(io, raw"$F(x) = exp(-exp(-(x-mu)/beta))$")
            println(io, "")
            println(io, "50年重现期风速计算公式：")
            println(io, raw"$V_{50} = mu - beta ln(-ln(1 - 1/T))$")
            println(io, "")
            println(io, "其中：")
            println(io, raw"- $mu$：Gumbel分布位置参数")
            println(io, raw"- $beta$：Gumbel分布尺度参数")
            println(io, raw"- $T = 50 times 365/5 = 3650$：重现期（5天周期数）")
            println(io, raw"- $V_{50}$：50年一遇最大风速")
            println(io, "")
            println(io, "*重要说明*：由于Gumbel分布基于5天极值样本拟合，计算50年重现期时，")
            println(io, "重现期T应为5天周期数（3650个），而非年数（50年）。")
            println(io, "这确保了统计计算的正确性，最终结果仍为标准50年重现期风速。")
            println(io, "")
            
            # Create Method 2 table
            method2_table_df = DataFrame()
            for height in sort(unique(method2_results_df.height), rev=true)
                method2_data = filter(row -> row.height == height, method2_results_df)
                if nrow(method2_data) > 0
                    push!(method2_table_df, (
                        height = height,
                        extreme_wind_speed = round(method2_data[1, :extreme_wind_speed], digits=2),
                        extreme_wind_speed_1225 = round(method2_data[1, :extreme_wind_speed_1225_density], digits=2)
                    ))
                end
            end
            
            rename!(method2_table_df,
                :height => "高度(m)",
                :extreme_wind_speed => "五日最大风速法(m/s)",
                :extreme_wind_speed_1225 => "标准密度风速(m/s)"
            )
            
            method2_table = simple_table(method2_table_df)
            println(io, "表格：测风塔$(mast_name) 方法二结果")
            println(io, "")
            show(io, MIME"text/typst"(), method2_table)
            println(io, "")
            
            # Gumbel parameters table
            if !isempty(gumbel_table_df)
                gumbel_table = simple_table(gumbel_table_df)
                println(io, "表格：测风塔$(mast_name) Gumbel分布拟合参数")
                println(io, "")
                show(io, MIME"text/typst"(), gumbel_table)
                println(io, "")
            end
        end
        
        # Method 3 Section
        if !isempty(method3_results_df)
            println(io, "== 方法三：极端风速模型（EWM）法")
            println(io, "")
            println(io, "根据《风力发电机组设计要求》（GB/T 18451.1-2022）推荐的方法，对于稳态极端风速模型，")
            println(io, "风电场50年一遇最大（极大）风速可按一年一遇最大（极大）风速的1.25倍计算。")
            println(io, "")
            println(io, "计算公式：")
            println(io, raw"$V_{\"e50\"} = 1.25 times V_{\"max\"}$")
            println(io, "")
            println(io, "其中：")
            println(io, raw"- $V_{\"e50\"}$：50年一遇最大风速")
            println(io, raw"- $V_{\"max\"}$：观测期内最大风速")
            println(io, "")
            println(io, "本方法直接采用观测期间的最大风速作为代表值，")
            println(io, "乘以1.25系数得到50年重现期风速。")
            println(io, "")
            
            # Create Method 3 table
            method3_table_df = DataFrame()
            for height in sort(unique(method3_results_df.height), rev=true)
                method3_data = filter(row -> row.height == height, method3_results_df)
                if nrow(method3_data) > 0
                    push!(method3_table_df, (
                        height = height,
                        observed_max = round(method3_data[1, :observed_max], digits=2),
                        extreme_wind_speed = round(method3_data[1, :extreme_wind_speed], digits=2),
                        extreme_wind_speed_1225 = round(method3_data[1, :extreme_wind_speed_1225_density], digits=2)
                    ))
                end
            end
            
            rename!(method3_table_df,
                :height => "高度(m)",
                :observed_max => "观测最大风速(m/s)",
                :extreme_wind_speed => "50年重现期风速(m/s)",
                :extreme_wind_speed_1225 => "标准密度风速(m/s)"
            )
            
            method3_table = simple_table(method3_table_df)
            println(io, "表格：测风塔$(mast_name) 方法三结果")
            println(io, "")
            show(io, MIME"text/typst"(), method3_table)
            println(io, "")
        end
        
        # Comparison section if multiple methods have results
        if (!isempty(method1_results_df) && !isempty(method2_results_df)) || 
           (!isempty(method1_results_df) && !isempty(method3_results_df)) ||
           (!isempty(method2_results_df) && !isempty(method3_results_df))
            
            # Create comparison table
            comparison_df = DataFrame()
            all_heights_comparison = Float64[]
            if !isempty(method1_results_df)
                append!(all_heights_comparison, method1_results_df.height)
            end
            if !isempty(method2_results_df)
                append!(all_heights_comparison, method2_results_df.height)
            end
            if !isempty(method3_results_df)
                append!(all_heights_comparison, method3_results_df.height)
            end
            heights_comparison = sort(unique(all_heights_comparison), rev=true)
            
            for height in heights_comparison
                method1_data = filter(row -> row.height == height, method1_results_df)
                method2_data = filter(row -> row.height == height, method2_results_df)
                method3_data = filter(row -> row.height == height, method3_results_df)
                
                method1_value = nrow(method1_data) > 0 ? round(method1_data[1, :extreme_wind_speed_1225_density], digits=2) : missing
                method2_value = nrow(method2_data) > 0 ? round(method2_data[1, :extreme_wind_speed_1225_density], digits=2) : missing
                method3_value = nrow(method3_data) > 0 ? round(method3_data[1, :extreme_wind_speed_1225_density], digits=2) : missing
                
                push!(comparison_df, (
                    height = height,
                    method1_1225 = method1_value,
                    method2_1225 = method2_value,
                    method3_1225 = method3_value
                ))
            end
            
            rename!(comparison_df,
                :height => "高度(m)",
                :method1_1225 => "5倍平均风速法(m/s)",
                :method2_1225 => "五日最大风速法(m/s)",
                :method3_1225 => "极端风速模型法(m/s)"
            )
            
            comparison_table = simple_table(comparison_df)
            println(io, "表格：测风塔$(mast_name) 标准密度风速对比")
            println(io, "")
            show(io, MIME"text/typst"(), comparison_table)
        end
    end
    
    @info "Generated 50-year extreme wind report for mast $(mast_name) at $(typst_path)"
end

export analyze_fifty_years_extreme_wind, analyze_method1_five_times_average, analyze_method2_five_day_maxima, analyze_method3_ewm, generate_fifty_years_report

end # module 