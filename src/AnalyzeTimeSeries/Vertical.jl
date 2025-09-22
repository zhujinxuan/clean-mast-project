module Vertical

using DataFrames
using CSV
using AlgebraOfGraphics, CairoMakie
using Statistics
using GLM
using SummaryTables

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path

"""
    analyze_vertical_profile(config::AnalyzeConfig)

Analyze vertical wind speed profile with power law fitting for all masts.
"""
function analyze_vertical_profile(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "vertical-profile")
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        sort!(speed_sensors, by = s -> s.height, rev = true)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Calculate mean wind speeds at each height
        heights = Float64[s.height for s in speed_sensors]
        speeds = map(speed_sensors) do sensor
            mean(skipmissing(mast.timeSeriesData.df[:, sensor.columnName]))
        end
        
        results_df = DataFrame(
            height = heights,
            speed = speeds
        )
        
        # Skip if any speeds are missing or NaN
        if any(isnan, results_df.speed) || any(ismissing, results_df.speed)
            @warn "Invalid speed data for vertical profile analysis in mast $(mast.name)"
            continue
        end
        
        # Fit power law: v = v_ref * (h / h_ref)^α
        # Taking log: log(v) = log(v_ref) + α * log(h/h_ref)
        model_df = DataFrame(
            log_height = log.(results_df.height),
            log_speed = log.(results_df.speed)
        )
        
        model = lm(@formula(log_speed ~ log_height), model_df)
        α = coef(model)[2]  # Power law exponent
        intercept = coef(model)[1]
        
        # Generate fitted line
        height_range = range(minimum(results_df.height), maximum(results_df.height), length=100)
        reference_height = results_df.height[1]
        reference_speed = results_df.speed[1]
        fitted_speeds = reference_speed .* (height_range ./ reference_height).^α
        
        fit_df = DataFrame(height=height_range, speed=fitted_speeds)
        
        # Add R-squared value
        r_squared = r2(model)
        
        # Save to CSV with metadata
        metadata_df = DataFrame(
            parameter = ["alpha", "reference_height", "reference_speed", "r_squared"],
            value = [α, reference_height, reference_speed, r_squared]
        )
        
        CSV.write(joinpath(output_dir, "vertical_profile.csv"), results_df)
        CSV.write(joinpath(output_dir, "vertical_profile_metadata.csv"), metadata_df)
        
        # Create plot using AlgebraOfGraphics
        points_layer = data(results_df) * mapping(:speed, :height) * visual(Scatter, color=:blue, markersize=12)
        line_layer = data(fit_df) * mapping(:speed, :height) * visual(Lines, color=:red, linewidth=3)
        
        plt = points_layer + line_layer
        
        fig = draw(plt, axis=(
            xlabel="Wind Speed (m/s)",
            ylabel="Height (m)",
            title="Vertical Wind Speed Profile - $(mast.name) (α = $(round(α, digits=3)), R² = $(round(r_squared, digits=3)))"
        ))
        
        save(joinpath(output_dir, "vertical_profile.svg"), fig)
        
        results[mast.name] = Dict(
            "data" => results_df,
            "fit" => fit_df,
            "alpha" => α,
            "r_squared" => r_squared
        )
        @info "Generated vertical profile for mast $(mast.name) with α = $(round(α, digits=3))"
    end
    
    return results
end

"""
    analyze_wind_shear(config::AnalyzeConfig)

Analyze wind shear between different height pairs for all masts.
"""
function analyze_wind_shear(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "vertical-profile")
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if length(speed_sensors) < 2
            @warn "Need at least 2 wind speed sensors for shear analysis in mast $(mast.name)"
            continue
        end
        
        # Sort sensors by height
        sort!(speed_sensors, by = s -> s.height)
        
        # Calculate shear between consecutive height pairs
        shear_results = DataFrame()
        
        for i in 1:(length(speed_sensors)-1)
            lower_sensor = speed_sensors[i]
            upper_sensor = speed_sensors[i+1]
            
            # Get wind speeds
            lower_speeds = skipmissing(mast.timeSeriesData.df[:, lower_sensor.columnName])
            upper_speeds = skipmissing(mast.timeSeriesData.df[:, upper_sensor.columnName])
            
            # Calculate power law exponent for each timestamp
            # α = ln(v2/v1) / ln(h2/h1)
            height_ratio = upper_sensor.height / lower_sensor.height
            ln_height_ratio = log(height_ratio)
            
            shear_values = Float64[]
            for (v1, v2) in zip(lower_speeds, upper_speeds)
                if v1 > 0 && v2 > 0
                    α = log(v2/v1) / ln_height_ratio
                    push!(shear_values, α)
                end
            end
            
            if !isempty(shear_values)
                mean_shear = mean(shear_values)
                std_shear = std(shear_values)
                
                # Add to results
                push!(shear_results, (
                    height_pair = "$(lower_sensor.height)m-$(upper_sensor.height)m",
                    mean_alpha = mean_shear,
                    std_alpha = std_shear,
                    min_alpha = minimum(shear_values),
                    max_alpha = maximum(shear_values),
                    count = length(shear_values)
                ))
            end
        end
        
        if !isempty(shear_results)
            CSV.write(joinpath(output_dir, "wind_shear_analysis.csv"), shear_results)
            results[mast.name] = shear_results
            @info "Generated wind shear analysis for mast $(mast.name)"
        end
    end
    
    return results
end

"""
    analyze_all_vertical(config::AnalyzeConfig)

Run all vertical profile analyses for all masts in the configuration.
"""
function analyze_all_vertical(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    results["profile"] = analyze_vertical_profile(config)
    results["shear"] = analyze_wind_shear(config)
    results["ratio_table"] = create_wind_speed_ratio_table(config)
    
    return results
end

"""
    create_wind_speed_ratio_table(config::AnalyzeConfig)

Create a wind shear exponent (风切变指数) table showing alpha values between different heights.
The alpha values are calculated using the power law: α = ln(v2/v1) / ln(h2/h1)
Saves results as CSV and Typst files using SummaryTables.jl.
"""
function create_wind_speed_ratio_table(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "vertical-profile")
        
        # Get all wind speed sensors (average values only)
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Sort sensors by height (descending for table display)
        sort!(speed_sensors, by = s -> s.height, rev = true)
        
        # Calculate mean wind speeds at each height
        heights = [s.height for s in speed_sensors]
        speeds = map(speed_sensors) do sensor
            mean(skipmissing(mast.timeSeriesData.df[:, sensor.columnName]))
        end
        
        # Create DataFrame for wind shear exponents
        n = length(heights)
        height_labels = ["$(h)m" for h in heights]
        
        # Initialize DataFrame with height and wind speed columns
        shear_df = DataFrame()
        shear_df[!, :测风高度] = height_labels
        shear_df[!, :风速] = round.(speeds, digits=3)
        
        # Add columns for each height showing wind shear exponents
        for (j, target_height) in enumerate(heights)
            col_name = Symbol("$(target_height)m")
            
            # Use map instead of for loop with push!
            alpha_col = map(enumerate(heights)) do (i, source_height)
                if i == j
                    "◦"  # Same height
                elseif speeds[i] <= 0 || speeds[j] <= 0 || source_height <= 0 || target_height <= 0
                    "◦"  # Invalid data
                else
                    # Calculate wind shear exponent: α = ln(v_source/v_target) / ln(h_source/h_target)
                    alpha = log(speeds[i] / speeds[j]) / log(source_height / target_height)
                    string(round(alpha, digits=3))
                end
            end
            
            shear_df[!, col_name] = alpha_col
        end
        
        # Save as CSV
        CSV.write(joinpath(output_dir, "wind_shear_exponent_table.csv"), shear_df)
        
        # Create SummaryTables formatted table
        summary_table = simple_table(shear_df)
        
        # Save as Typst
        typst_path = joinpath(output_dir, "wind_shear_exponent.typ")
        open(typst_path, "w") do io
            println(io, "// Wind Shear Exponent Table for $(mast.name)")
            println(io, "// Generated by CleanMastProject.jl")
            println(io, "// Alpha values calculated using: α = ln(v2/v1) / ln(h2/h1)")
            println(io, "")
            println(io, "== 风切变指数表")
            show(io, MIME"text/typst"(), summary_table)
            println(io, "")
            println(io, "")
            
            # Add vertical wind profile image if it exists
            vertical_profile_svg = joinpath(output_dir, "vertical_profile.svg")
            if isfile(vertical_profile_svg)
                println(io, "== 垂直风剖面图")
                println(io, "")
                println(io, "=== $(mast.name) 垂直风速剖面拟合")
                println(io, "")
                
                # Try to read metadata for enhanced caption
                metadata_path = joinpath(output_dir, "vertical_profile_metadata.csv")
                caption_text = "$(mast.name) 垂直风速剖面与幂律拟合图"
                
                if isfile(metadata_path)
                    try
                        metadata = CSV.read(metadata_path, DataFrame)
                        α = metadata[metadata.parameter .== "alpha", :value][1]
                        r_squared = metadata[metadata.parameter .== "r_squared", :value][1]
                        caption_text = "$(mast.name) 垂直风速剖面与幂律拟合 (α = $(round(α, digits=3)), R² = $(round(r_squared, digits=3)))"
                    catch
                        # Fall back to simple caption if metadata reading fails
                    end
                end
                
                println(io, "#figure(")
                println(io, "  image(\"vertical_profile.svg\", width: 80%),")
                println(io, "  caption: [$caption_text]")
                println(io, ")")
                println(io, "")
            end
        end
        
        
        # Create summary statistics
        stats_df = DataFrame(
            height = heights,
            height_label = height_labels,
            mean_wind_speed = speeds
        )
        
        # Add alpha relative to reference heights
        if length(heights) >= 2
            ref_height_low = heights[end]    # Lowest height
            ref_height_high = heights[1]     # Highest height
            ref_speed_low = speeds[end]
            ref_speed_high = speeds[1]
            
            alpha_to_low = Float64[]
            alpha_to_high = Float64[]
            
            for (h, s) in zip(heights, speeds)
                if h != ref_height_low && s > 0 && ref_speed_low > 0
                    alpha_low = log(s / ref_speed_low) / log(h / ref_height_low)
                    push!(alpha_to_low, alpha_low)
                else
                    push!(alpha_to_low, NaN)
                end
                
                if h != ref_height_high && s > 0 && ref_speed_high > 0
                    alpha_high = log(s / ref_speed_high) / log(h / ref_height_high)
                    push!(alpha_to_high, alpha_high)
                else
                    push!(alpha_to_high, NaN)
                end
            end
            
            stats_df[!, "alpha_to_$(ref_height_low)m"] = alpha_to_low
            stats_df[!, "alpha_to_$(ref_height_high)m"] = alpha_to_high
        end
        
        CSV.write(joinpath(output_dir, "wind_shear_summary.csv"), stats_df)
        
        results[mast.name] = Dict(
            "shear_table" => shear_df,
            "summary_table" => summary_table,
            "summary" => stats_df,
            "heights" => heights,
            "speeds" => speeds,
        )
        
        @info "Generated wind shear exponent table for mast $(mast.name) with $(length(heights)) heights"
        @info "Saved Typst file: $typst_path"
    end
    
    return results
end

export analyze_vertical_profile, analyze_wind_shear, analyze_all_vertical, create_wind_speed_ratio_table

end # module 