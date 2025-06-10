module WindTemporal

using DataFrames
using CSV
using AlgebraOfGraphics, CairoMakie
using Statistics
using Dates
using DataFramesMeta
using SummaryTables

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path, AirDensityConfig
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
        sort!(speed_sensors, by = s -> s.height, rev=true)
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
        stacked_df = stack(plot_df, Not(:timestamp))
        fig = data(stacked_df) * 
              mapping(:timestamp, :value, color=:variable => presorted) * 
              visual(Lines) |> 
              draw(axis=(title="Wind Speed Time Series - $(mast.name)",
                         xlabel="Time", 
                         ylabel="Wind Speed (m/s)"))
        
        svg_path = joinpath(output_dir, "wind_speed_timeseries.svg")
        save(svg_path, fig)
        
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
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        sort!(speed_sensors, by = s -> s.height, rev=true)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Add hour column
        hourly_df = copy(mast.timeSeriesData.df)
        hourly_df.hour = hour.(hourly_df.timestamp)
        
        # Calculate hourly averages for each height
        speed_results_df = DataFrame(hour = 0:23)
        power_results_df = isnothing(mast.airDensity) ? nothing : DataFrame(hour = 0:23)
        
        for sensor in speed_sensors
            # Calculate wind speed hourly means
            hourly_means = combine(groupby(hourly_df, :hour), 
                sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
            speed_results_df[!, "$(sensor.height)m"] = hourly_means[:, "$(sensor.height)m"]
            
            # Calculate power only if air density is available
            if !isnothing(mast.airDensity)
                # Calculate air density at sensor height
                air_density = calculate_air_density(sensor.height, mast.airDensity)
                
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
        end
        
        # Save to CSV
        CSV.write(joinpath(output_dir, "daily_pattern.csv"), speed_results_df)
        
        # Create wind speed plot
        stacked_speed = stack(speed_results_df, Not(:hour))
        fig_speed = data(stacked_speed) * 
                    mapping(:hour, :value, color=:variable => presorted) * 
                    visual(Lines) |> 
                    draw(axis=(title="24-Hour Wind Speed Pattern - $(mast.name)",
                               xlabel="Hour of Day", 
                               ylabel="Wind Speed (m/s)",
                               xticks=0:2:23))
        
        save(joinpath(output_dir, "daily_pattern.svg"), fig_speed)
        
        # Handle power analysis only if air density is available
        if !isnothing(mast.airDensity) && !isnothing(power_results_df)
            CSV.write(joinpath(output_dir, "daily_power_pattern.csv"), power_results_df)
            
            # Create wind power plot
            stacked_power = stack(power_results_df, Not(:hour))
            fig_power = data(stacked_power) * 
                        mapping(:hour, :value, color=:variable => presorted) * 
                        visual(Lines) |> 
                        draw(axis=(title="24-Hour Wind Power Density Pattern - $(mast.name)",
                                   xlabel="Hour of Day", 
                                   ylabel="Wind Power Density (W/m²)",
                                   xticks=0:2:23))
            
            save(joinpath(output_dir, "daily_power_pattern.svg"), fig_power)
            results[mast.name] = (speed = speed_results_df, power = power_results_df)
        else
            results[mast.name] = (speed = speed_results_df, power = nothing)
        end
        @info "Generated daily patterns for mast $(mast.name)"
    end
    
    return results
end

struct MonthlyPattern
    speed_df::DataFrame
    power_df::DataFrame
end

"""
    analyze_monthly_pattern(config::AnalyzeConfig)

Analyze monthly wind speed and power patterns for all masts.
"""
function analyze_monthly_pattern(config::AnalyzeConfig) :: Dict{String, MonthlyPattern}
    results = Dict{String, MonthlyPattern}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        sort!(speed_sensors, by = s -> s.height, rev=true)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Prepare base DataFrame with month column
        base_df = @transform mast.timeSeriesData.df :month = month.(:timestamp)
        
        # Initialize results DataFrames with all months
        speed_results_df = DataFrame(month = 1:12)

        pairs = map(speed_sensors) do sensor
            sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m"
        end
        speed_results_df = combine(groupby(base_df, :month), pairs...)
        sort!(speed_results_df, :month)
        
        # Calculate power only if air density is available
        power_results_df = nothing
        if !isnothing(mast.airDensity)
            power_results_df = DataFrame(month = 1:12)
            
            # First, add all power columns to base_df
            power_df = copy(base_df)
            for sensor in speed_sensors
                air_density = calculate_air_density(sensor.height, mast.airDensity)
                power_col = "power_$(sensor.height)m"
                power_df[!, power_col] = [ismissing(ws) ? missing : calculate_wind_power_density(ws, air_density) 
                                         for ws in power_df[!, sensor.columnName]]
            end
            
            # Then use functional approach for groupby operations
            power_pairs = map(speed_sensors) do sensor
                air_density = calculate_air_density(sensor.height, mast.airDensity)
                power_col = "power_$(sensor.height)m"
                Symbol(power_col) => (x -> mean(skipmissing(x))) => "$(sensor.height)m"
            end
            power_results_df = combine(groupby(power_df, :month), power_pairs...)
            sort!(power_results_df, :month)
        end
        
        # Save to CSV
        CSV.write(joinpath(output_dir, "monthly_pattern.csv"), speed_results_df)
        
        # Create wind speed plot
        month_labels = Dates.monthabbr.(1:12)
        stacked_speed = stack(speed_results_df, Not(:month))
        # stacked_speed.month_label = month_labels[stacked_speed.month]
        
        fig_speed = data(stacked_speed) * 
                    mapping(:month => nonnumeric, :value, dodge=:variable=>presorted, color=:variable=>presorted) *
                    visual(BarPlot) |> 
                    draw(axis=(title="Monthly Wind Speed Pattern - $(mast.name)",
                               xlabel="Month", 
                               ylabel="Wind Speed (m/s)"))
        
        save(joinpath(output_dir, "monthly_pattern.svg"), fig_speed, size=(800, 600))
        
        # Handle power outputs only if air density is available
        if !isnothing(mast.airDensity) && !isnothing(power_results_df)
            CSV.write(joinpath(output_dir, "monthly_power_pattern.csv"), power_results_df)
            
            # Create wind power plot
            stacked_power = stack(power_results_df, Not(:month))
            # stacked_power.month_label = month_labels[stacked_power.month]
            
            fig_power = data(stacked_power) * 
                        mapping(:month => nonnumeric, :value, dodge=:variable=>presorted, color=:variable=>presorted) * 
                        visual(BarPlot) |> 
                        draw(axis=(title="Monthly Wind Power Density Pattern - $(mast.name)",
                                   xlabel="Month", 
                                   ylabel="Wind Power Density (W/m²)"))
            
            save(joinpath(output_dir, "monthly_power_pattern.svg"), fig_power, size=(800, 600))
            results[mast.name] = MonthlyPattern(speed_results_df, power_results_df)
        else
            # Create MonthlyPattern with empty DataFrame for power
            results[mast.name] = MonthlyPattern(speed_results_df, DataFrame())
        end
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
        
        # Prepare data with hour and month columns
        hourly_df = @transform mast.timeSeriesData.df :hour = hour.(:timestamp) :month = month.(:timestamp)
        
        # Get month names for faceting
        month_names = Dates.monthname.(1:12)
        
        # Create complete DataFrame for all months and hours
        all_data = DataFrame()
        for m in 1:12
            month_data = filter(row -> row.month == m, hourly_df)
            
            if nrow(month_data) > 0
                # Calculate hourly means for this month
                for sensor in speed_sensors
                    hourly_means = combine(groupby(month_data, :hour), 
                        sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
                    
                    # Add month info and stack the data
                    hourly_means.month .= m
                    hourly_means.month_name .= month_names[m]
                    stacked_month = stack(hourly_means, Not([:hour, :month, :month_name]), 
                                        variable_name=:height, value_name=:wind_speed)
                    
                    append!(all_data, stacked_month)
                end
            end
        end
        
        # Remove duplicates (since we're adding same data for each sensor)
        unique!(all_data, [:hour, :month, :height])
        
        # Create faceted plot
        if nrow(all_data) > 0
            fig = data(all_data) * 
                  mapping(:hour, :wind_speed, color=:height, layout=:month_name => presorted) * 
                  visual(Lines) |> 
                  draw(facet=(; linkyaxes=:none),
                       axis=(ylabel="Wind Speed (m/s)",
                             xlabel="Hour"))
            
            save(joinpath(output_dir, "daily_wind_pattern_by_month.svg"), fig, size=(1200, 900))
        end
        
        # Save CSV - create format similar to original
        speed_results_df = DataFrame(hour = 0:23)
        for m in 1:12
            month_data = filter(row -> row.month == m, hourly_df)
            if nrow(month_data) > 0
                for sensor in speed_sensors
                    hourly_means = combine(groupby(month_data, :hour), 
                        sensor.columnName => (x -> mean(skipmissing(x))) => "$(sensor.height)m_month$(m)")
                    hourly_means = leftjoin(DataFrame(hour = 0:23), hourly_means, on = :hour, matchmissing = :equal)
                    speed_results_df[!, "$(sensor.height)m_month$(m)"] = hourly_means[!, "$(sensor.height)m_month$(m)"]
                end
            end
        end
        
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
        # Skip power analysis if air density is not configured
        if isnothing(mast.airDensity)
            @info "Skipping power analysis for mast $(mast.name) - no air density configured"
            results[mast.name] = nothing
            continue
        end
        
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
        if isempty(speed_sensors)
            @warn "No wind speed sensors found for mast $(mast.name)"
            continue
        end
        
        # Prepare data with hour and month columns
        hourly_df = @transform mast.timeSeriesData.df :hour = hour.(:timestamp) :month = month.(:timestamp)
        
        # Get month names for faceting
        month_names = Dates.monthname.(1:12)
        
        # Create complete DataFrame for all months and hours
        all_data = DataFrame()
        for m in 1:12
            month_data = filter(row -> row.month == m, hourly_df)
            
            if nrow(month_data) > 0
                # Calculate hourly power means for this month
                for sensor in speed_sensors
                    air_density = calculate_air_density(sensor.height, mast.airDensity)
                    power_col = "power_$(sensor.height)m"
                    
                    # Add power column
                    month_data[!, power_col] = [ismissing(ws) ? missing : 
                                              calculate_wind_power_density(ws, air_density) 
                                              for ws in month_data[!, sensor.columnName]]
                    
                    hourly_power = combine(groupby(month_data, :hour), 
                        Symbol(power_col) => (x -> mean(skipmissing(x))) => "$(sensor.height)m")
                    
                    # Add month info and stack the data
                    hourly_power.month .= m
                    hourly_power.month_name .= month_names[m]
                    stacked_month = stack(hourly_power, Not([:hour, :month, :month_name]), 
                                        variable_name=:height, value_name=:wind_power)
                    
                    append!(all_data, stacked_month)
                end
            end
        end
        
        # Remove duplicates
        unique!(all_data, [:hour, :month, :height])
        
        # Create faceted plot
        if nrow(all_data) > 0
            fig = data(all_data) * 
                  mapping(:hour, :wind_power, color=:height, layout=:month_name => presorted) * 
                  visual(Lines) |> 
                  draw(facet=(; linkyaxes=:none),
                       axis=(ylabel="Wind Power Density (W/m²)",
                             xlabel="Hour"))
            
            save(joinpath(output_dir, "daily_power_pattern_by_month.svg"), fig, size=(1200, 900))
        end
        
        # Save CSV - create format similar to original
        power_results_df = DataFrame(hour = 0:23)
        for m in 1:12
            month_data = filter(row -> row.month == m, hourly_df)
            if nrow(month_data) > 0
                for sensor in speed_sensors
                    air_density = calculate_air_density(sensor.height, mast.airDensity)
                    power_col = "power_$(sensor.height)m"
                    month_data[!, power_col] = [ismissing(ws) ? missing : 
                                              calculate_wind_power_density(ws, air_density) 
                                              for ws in month_data[!, sensor.columnName]]
                    
                    hourly_power = combine(groupby(month_data, :hour), 
                        Symbol(power_col) => (x -> mean(skipmissing(x))) => "$(sensor.height)m_month$(m)")
                    hourly_power = leftjoin(DataFrame(hour = 0:23), hourly_power, on = :hour, matchmissing = :equal)
                    power_results_df[!, "$(sensor.height)m_month$(m)"] = hourly_power[!, "$(sensor.height)m_month$(m)"]
                end
            end
        end
        
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
    generate_typst_monthly_report(config)
    
    return results
end

"""
    generate_typst_monthly_report(config::AnalyzeConfig)

Generate a Typst report with monthly wind speed and wind power patterns for all masts.
Wind speeds are formatted to 2 decimal places, wind power to 0 decimal places.
"""
function generate_typst_monthly_report(config::AnalyzeConfig)
    # Get monthly pattern data
    monthly_data = analyze_monthly_pattern(config)
    # Get daily pattern data
    daily_data = analyze_daily_pattern(config)
    
    for mast in config.masts
        if !haskey(monthly_data, mast.name)
            @warn "No monthly data available for mast $(mast.name)"
            continue
        end
        
        if !haskey(daily_data, mast.name)
            @warn "No daily data available for mast $(mast.name)"
            continue
        end
        
        output_dir = get_output_path(config, mast.name, "wind-temporal")
        typst_path = joinpath(output_dir, "wind-temporal.typ")
        
        # Get the data for this mast
        speed_df = monthly_data[mast.name].speed_df
        power_df = monthly_data[mast.name].power_df
        daily_speed_df = daily_data[mast.name].speed
        daily_power_df = daily_data[mast.name].power
        
        # Check if power analysis is available
        has_power_data = !isnothing(mast.airDensity) && !isnothing(daily_power_df) && !isempty(power_df)
        
        # Prepare data for monthly tables
        month_names = ["一月", "二月", "三月", "四月", "五月", "六月", 
                      "七月", "八月", "九月", "十月", "十一月", "十二月"]
        
        # Create formatted speed DataFrame
        speed_table_df = copy(speed_df)
        sort!(speed_table_df, :month)
        speed_table_df[!, "month"] = map(speed_table_df[!, "month"]) do month
            month_names[month]
        end
        
        # Create formatted power DataFrame only if power data is available
        power_table_df = nothing
        if has_power_data
            power_table_df = copy(power_df)
            sort!(power_table_df, :month)
            power_table_df[!, "month"] = map(power_table_df[!, "month"]) do month
                month_names[month]
            end
            for col in names(power_df)
                if col != "month"
                    # Format to 0 decimal places, handle missing values
                    formatted_values = [ismissing(v) ? "-" : string(round(Int, v)) 
                                      for v in power_df[!, col]]
                    power_table_df[!, col] = formatted_values
                end
            end
        end
        
        # Prepare data for daily tables
        daily_speed_table_df = copy(daily_speed_df)
        daily_speed_table_df[!, "hour"] = map(daily_speed_table_df[!, "hour"]) do h
            string(h) * ":00"
        end
        
        daily_power_table_df = nothing
        avg_power_subheaders = nothing
        if has_power_data
            daily_power_table_df = copy(daily_power_df)
            daily_power_table_df[!, "hour"] = map(daily_power_table_df[!, "hour"]) do h
                string(h) * ":00"
            end
            for col in names(daily_power_df)
                if col != "hour"
                    # Format to 0 decimal places, handle missing values
                    formatted_values = [ismissing(v) ? "-" : string(round(Int, v)) 
                                      for v in daily_power_df[!, col]]
                    daily_power_table_df[!, col] = formatted_values
                end
            end
            avg_power_subheaders = ["平均", [string(round(Int,mean(skipmissing(daily_power_df[!, col])))) for col in names(daily_power_df) if col != "hour"]...]
        end

        avg_speed_subheaders = ["平均", [string(round(mean(skipmissing(daily_speed_df[!, col])), digits=2)) for col in names(daily_speed_df) if col != "hour"]...]
        
        # Create SummaryTables tables
        cols = map(propertynames(speed_df)) do col
            if col === :month
                return :month => "月份"
            end
            return col => String(col)
        end
        speed_table = simple_table(speed_table_df,cols, subheaders=avg_speed_subheaders, round_digits=3)
        
        # Create daily tables
        daily_cols = map(propertynames(daily_speed_df)) do col
            if col === :hour
                return :hour => "小时"
            end
            return col => String(col)
        end
        daily_speed_table = simple_table(daily_speed_table_df, daily_cols, subheaders=avg_speed_subheaders, round_digits=3)
        
        # Create power tables only if power data is available
        power_table = nothing
        daily_power_table = nothing
        if has_power_data
            power_table = simple_table(power_table_df,cols, subheaders=avg_power_subheaders, round_digits=0)
            daily_power_table = simple_table(daily_power_table_df, daily_cols, subheaders=avg_power_subheaders, round_digits=0)
        end
        
        # Write Typst report
        open(typst_path, "w") do io
            println(io, "= 风速时序分析报告")
            
            # Include all available SVG figures
            println(io, "== 图表分析")
            
            # Monthly wind speed pattern
            monthly_pattern_svg = joinpath(output_dir, "monthly_pattern.svg")
            if isfile(monthly_pattern_svg)
                println(io, "#figure(")
                println(io, "  image(\"monthly_pattern.svg\"),")
                println(io, "  caption: [$(mast.name)测风塔各月份风速分布图],")
                println(io, ")")
                println(io)
            end
            
            # Monthly wind power pattern (if available)
            if has_power_data
                monthly_power_svg = joinpath(output_dir, "monthly_power_pattern.svg")
                if isfile(monthly_power_svg)
                    println(io, "#figure(")
                    println(io, "  image(\"monthly_power_pattern.svg\"),")
                    println(io, "  caption: [$(mast.name)测风塔各月份风功率密度分布图],")
                    println(io, ")")
                    println(io)
                end
            end
            
            # Daily wind speed pattern
            daily_pattern_svg = joinpath(output_dir, "daily_pattern.svg")
            if isfile(daily_pattern_svg)
                println(io, "#figure(")
                println(io, "  image(\"daily_pattern.svg\"),")
                println(io, "  caption: [$(mast.name)测风塔24小时风速变化图],")
                println(io, ")")
                println(io)
            end
            
            # Daily wind power pattern (if available)
            if has_power_data
                daily_power_svg = joinpath(output_dir, "daily_power_pattern.svg")
                if isfile(daily_power_svg)
                    println(io, "#figure(")
                    println(io, "  image(\"daily_power_pattern.svg\"),")
                    println(io, "  caption: [$(mast.name)测风塔24小时风功率密度变化图],")
                    println(io, ")")
                    println(io)
                end
            end
            
            # Monthly-daily wind speed pattern
            monthly_daily_wind_svg = joinpath(output_dir, "daily_wind_pattern_by_month.svg")
            if isfile(monthly_daily_wind_svg)
                println(io, "#figure(")
                println(io, "  image(\"daily_wind_pattern_by_month.svg\"),")
                println(io, "  caption: [$(mast.name)测风塔各月份24小时风速变化对比图],")
                println(io, ")")
                println(io)
            end
            
            # Monthly-daily wind power pattern (if available)
            if has_power_data
                monthly_daily_power_svg = joinpath(output_dir, "daily_power_pattern_by_month.svg")
                if isfile(monthly_daily_power_svg)
                    println(io, "#figure(")
                    println(io, "  image(\"daily_power_pattern_by_month.svg\"),")
                    println(io, "  caption: [$(mast.name)测风塔各月份24小时风功率密度变化对比图],")
                    println(io, ")")
                    println(io)
                end
            end
            
            println(io, "== 数据表格")
            println(io, "表格：$(mast.name)各月份不同高度平均风速")
            # Write speed table in Typst format
            show(io, MIME"text/typst"(), speed_table)

            println(io, "表格：$(mast.name)各小时不同高度平均风速")
            # Write daily speed table in Typst format
            show(io, MIME"text/typst"(), daily_speed_table)
            
            # Write power tables only if power data is available
            if has_power_data
                println(io, "表格：$(mast.name)各月份不同高度平均风功率密度")
                # Write power table in Typst format
                show(io, MIME"text/typst"(), power_table)
                
                println(io, "表格：$(mast.name)各小时不同高度平均风功率密度")
                # Write daily power table in Typst format
                show(io, MIME"text/typst"(), daily_power_table)
            end
            
            # Add summary statistics
            println(io, "== 统计摘要")
            
            # Calculate annual averages
            speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.timeSeriesData.sensors)
            sort!(speed_sensors, by = s -> s.height, rev=true)
            
            for sensor in speed_sensors
                height_col = "$(sensor.height)m"
                if height_col in names(speed_df)
                    annual_speed = mean(skipmissing(speed_df[!, height_col]))
                    println(io, "- $(sensor.height)m高度年平均风速为$(round(annual_speed, digits=2))m/s")
                    
                    if has_power_data && height_col in names(power_df)
                        annual_power = mean(skipmissing(power_df[!, height_col]))
                        println(io, "- $(sensor.height)m高度年平均风功率密度为$(round(Int, annual_power))W/m²")
                    end
                end
            end
            
        end
        
        @info "Generated Typst report for mast $(mast.name) at $(typst_path)"
    end
    
    return nothing
end

export analyze_wind_speed_timeseries, analyze_daily_pattern, analyze_monthly_pattern,
       analyze_monthly_daily_wind, analyze_monthly_daily_windpower, analyze_all_temporal,
       generate_typst_monthly_report

end # module 