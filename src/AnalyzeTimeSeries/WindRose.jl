module WindRose

using DataFrames
using CSV
using CairoMakie
using Statistics
using Dates
using SummaryTables

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path
import ..AirDensity: calculate_air_density, calculate_wind_power_density

"""
    get_wind_sector(direction::Float64, num_sectors::Int=16) -> Int

Convert wind direction to sector index (1 to num_sectors).
Direction 0° is North (sector 1), sectors are centered on cardinal directions.
"""
function get_wind_sector(direction::Float64, num_sectors::Int=16)::Int
    sector_width = 360.0 / num_sectors
    # Normalize direction to 0-360 range
    normalized_dir = mod(direction, 360.0)
    # Adjust to center first sector on North (0°)
    # Add half sector width to shift, then find sector
    adjusted_dir = mod(normalized_dir + sector_width/2, 360.0)
    sector = floor(Int, adjusted_dir / sector_width) + 1
    return min(sector, num_sectors)  # Ensure sector is within bounds
end

"""
    get_sector_info(num_sectors::Int=16) -> (Vector{String}, Vector{Float64})

Get sector labels and center angles for wind rose plotting.
Returns sector labels and their corresponding center angles in degrees.
"""
function get_sector_info(num_sectors::Int=16)
    # Standard 16-sector labels (can be extended for more sectors)
    if num_sectors == 16
        sector_labels = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                         "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    elseif num_sectors == 8
        sector_labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    else
        # Generate generic labels for other sector counts
        sector_labels = ["$(round(Int, (i-1) * 360.0 / num_sectors))°" for i in 1:num_sectors]
    end
    
    # Calculate sector center angles - first sector (N) is at 0°
    sector_angles = [(i-1) * 360.0 / num_sectors for i in 1:num_sectors]
    
    return sector_labels, sector_angles
end

"""
    calculate_sector_statistics(df::DataFrame, speed_col::Symbol, dir_col::Symbol, 
                              air_density::Union{Float64, Nothing}=nothing, num_sectors::Int=16)

Calculate wind direction frequency and power statistics for each sector using functional programming approach.
If air_density is nothing, only frequency statistics are calculated (no power calculations).
"""
function calculate_sector_statistics(df::DataFrame, speed_col::Symbol, dir_col::Symbol, 
                                   air_density::Union{Float64, Nothing}=nothing, num_sectors::Int=16)
    # Create a copy of the dataframe for processing
    df_work = copy(df)
    
    # Filter out missing values and invalid wind speeds
    df_clean = df_work |>
        df -> filter(row -> !ismissing(row[speed_col]) && 
                           !ismissing(row[dir_col]) && 
                           row[speed_col] >= 0, df)
    
    # Add sector column using map operations
    df_clean[!,:sector] = map(dir -> get_wind_sector(dir, num_sectors), df_clean[!, dir_col])
    
    # Add power column only if air density is provided
    if !isnothing(air_density)
        df_clean[!,:power] = map(speed -> calculate_wind_power_density(speed, air_density), df_clean[!, speed_col])
        
        # Group by sector and calculate statistics including power
        sector_stats = df_clean |>
            df -> groupby(df, :sector) |>
            gdf -> combine(gdf,
                nrow => :count,
                speed_col => mean => :avg_speed,
                :power => mean => :avg_power,
                :power => sum => :total_power,  # Add total power for power frequency calculation
            )
    else
        # Group by sector and calculate statistics without power
        sector_stats = df_clean |>
            df -> groupby(df, :sector) |>
            gdf -> combine(gdf,
                nrow => :count,
                speed_col => mean => :avg_speed,
            )
    end
    
    # Get sector labels and angles
    sector_labels, sector_angles = get_sector_info(num_sectors)
    
    # Create complete sector range (1 to num_sectors)
    all_sectors = DataFrame(
        sector = 1:num_sectors,
        label = sector_labels,
        angle = sector_angles
    )
    
    # Left join to ensure all sectors are represented, fill missing with zeros
    result = leftjoin(all_sectors, sector_stats, on=:sector)
    
    # Replace missing values with appropriate defaults using broadcasting
    result.count = coalesce.(result.count, 0)
    result.avg_speed = coalesce.(result.avg_speed, 0.0)
    
    # Calculate frequencies using broadcasting
    result.frequency = result.count ./ sum(result.count)
    
    # Add power-related columns only if air density was provided
    if !isnothing(air_density)
        result.avg_power = coalesce.(result.avg_power, 0.0)
        result.total_power = coalesce.(result.total_power, 0.0)
        
        # Calculate power frequency (power contribution proportion)
        total_power_all = sum(result.total_power)
        if total_power_all > 0
            result.power_frequency = result.total_power ./ total_power_all
        else
            result.power_frequency = zeros(nrow(result))
        end
    else
        # Add placeholder columns with zeros when no air density
        result.avg_power = zeros(nrow(result))
        result.total_power = zeros(nrow(result))
        result.power_frequency = zeros(nrow(result))
    end
    
    # Sort by sector angles
    sort!(result, :angle)
    
    # Select and reorder columns
    select!(result, :sector, :label, :angle, :frequency, :avg_speed, :avg_power, :power_frequency, :total_power, :count)
    
    return result
end

"""
    create_wind_rose_plot(stats::DataFrame, title::String, value_col::Symbol=:frequency)

Create a single wind rose plot using CairoMakie with polar coordinates.
"""
function create_wind_rose_plot(stats::DataFrame, title::String, value_col::Symbol=:frequency)
    # Create figure and polar axis with North at top
    fig = Figure(size=(600, 600))
    ax = PolarAxis(fig[1, 1], title=title, titlesize=16, 
                   theta_0=-π/2,  # Rotate axis to put North (0°) at top
                   direction=-1)   # Counterclockwise direction (standard for meteorology)
    
    # Convert angles to radians (no manual rotation needed now)
    angles = deg2rad.(stats.angle)
    
    # Replace zero values with small value to maintain complete rose pattern
    values = copy(stats[!, value_col])
    values[values .== 0] .= 0.01
    
    # Create closed polygon for filled rose - use separate theta,r arguments
    angles_closed = vcat(angles, angles[1])
    values_closed = vcat(values, values[1])
    
    # Create the filled wind rose using lines instead of poly
    lines!(ax, angles_closed, values_closed, 
           linewidth=2, color=:blue)
    
    # Set up radial and angular ticks
    # Filter sectors with data for tick labels
    data_sectors = findall(stats.count .> 0)
    tick_angles = deg2rad.(stats.angle[data_sectors])
    tick_labels = stats.label[data_sectors]
    
    # Set angular ticks
    ax.thetaticks = (tick_angles, tick_labels)
    ax.thetaticklabelsize = 12
    
    # Set grid properties for both radial and angular grids
    ax.rgridcolor = (:gray, 0.3)
    ax.thetagridcolor = (:gray, 0.3)
    ax.rgridwidth = 1
    ax.thetagridwidth = 1
    
    return fig
end

"""
    create_multi_height_wind_rose(stats_by_height::Dict, title::String, value_col::Symbol=:frequency)

Create a wind rose plot with lines for multiple heights using CairoMakie.
"""
function create_multi_height_wind_rose(stats_by_height::Dict, title::String, value_col::Symbol=:frequency)
    # Create figure and polar axis with North at top
    fig = Figure(size=(1000, 800))  # Wider to accommodate external legend
    ax = PolarAxis(fig[1, 1], title=title, titlesize=16,
                   theta_0=-π/2,  # Rotate axis to put North (0°) at top
                   direction=-1)   # Clockwise direction (standard for meteorology)
    
    # Get sector info from first height for axis labels
    first_stats = first(values(stats_by_height))
    
    # Set up angular ticks using first stats (no manual rotation needed)
    tick_angles = deg2rad.(first_stats.angle)
    tick_labels = first_stats.label
    ax.thetaticks = (tick_angles, tick_labels)
    ax.thetaticklabelsize = 12
    
    # Set grid properties
    ax.rgridcolor = (:gray, 0.3)
    ax.thetagridcolor = (:gray, 0.3)
    ax.rgridwidth = 1
    ax.thetagridwidth = 1
    
    # Define colors for different heights
    colors = [:blue, :red, :green, :orange, :purple, :cyan, :brown, :pink]
    color_idx = 1
    
    # Filter heights >= 100m and sort by height (descending)
    height_stats_filtered = filter(p -> p[1] >= 100.0, collect(stats_by_height))
    height_stats_sorted = sort(height_stats_filtered, by = p -> p[1], rev = true)
    
    # Store line objects and labels for legend
    line_objects = []
    line_labels = String[]
    
    # Plot each height as a separate line
    for (height, stats) in height_stats_sorted
        # Convert angles to radians (no manual rotation needed)
        angles = deg2rad.(stats.angle)
        
        # Replace zero values with small value to maintain complete rose pattern
        values = copy(stats[!, value_col])
        values[values .== 0] .= 0.01
        
        # Create closed line
        angles_closed = vcat(angles, angles[1])
        values_closed = vcat(values, values[1])
        
        # Plot line for this height and store for legend - use separate theta,r arguments
        line_obj = lines!(ax, angles_closed, values_closed,
                         linewidth=3, color=colors[color_idx])
        
        push!(line_objects, line_obj)
        push!(line_labels, "$(height)m")
        
        color_idx = (color_idx % length(colors)) + 1
    end
    
    # Create external legend
    Legend(fig[1, 2], line_objects, line_labels,
           framevisible=true, backgroundcolor=(:white, 0.9),
           titletext="Height", titlesize=14)
    
    # Add center annotation for value type
    if value_col == :frequency
        text!(ax, 0, 0, text="Wind Direction\nFrequency (%)", 
              align=(:center, :center), fontsize=10)
    elseif value_col == :avg_power
        text!(ax, 0, 0, text="Power Density\n(W/m²)", 
              align=(:center, :center), fontsize=10)
    elseif value_col == :power_frequency
        text!(ax, 0, 0, text="Power\nFrequency (%)", 
              align=(:center, :center), fontsize=10)
    end
    
    return fig
end

"""
    degreeMean(a::Float64, b::Float64, weight1::Float64) -> Float64

Calculate the mean of two angles in degrees.
"""
function degreeMean(a::Union{Float64, Missing}, b::Union{Float64, Missing}, weight1::Union{Float64, Missing}) :: Union{Float64, Missing}
    if ismissing(a) || ismissing(b) || ismissing(weight1)
        return missing
    end
    diff = mod(180.0 + b - a, 360.0) - 180.0
    return mod(a + diff*(1-weight1) + 360.0, 360.0)
end

"""
    get_direction_data_for_speed_sensor(speed_sensor::SensorColumn, ts ::TimeSeriesData) -> (DataFrame, Symbol)

Get the appropriate dataframe and direction column for a given speed sensor.
If direction sensors at exact height exist, use original data.
Otherwise, interpolate between closest sensors above and below.
"""
function get_direction_data_for_speed_sensor(speed_sensor::SensorColumn, ts ::TimeSeriesData)
    dir_sensors = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", 
                        ts.sensors)
                        
    # Find closest direction sensors above and below the speed sensor height
    dir_below = filter(s -> s.height <= speed_sensor.height, dir_sensors)
    dir_above = filter(s -> s.height >= speed_sensor.height, dir_sensors)
    
    # Get the closest sensors
    dir1_sensor = isempty(dir_below) ? nothing :
                  argmin(s -> abs(s.height - speed_sensor.height), dir_below)
    dir2_sensor = isempty(dir_above) ? nothing :
                  argmin(s -> abs(s.height - speed_sensor.height), dir_above)
    
    if isnothing(dir1_sensor) 
        return (ts.df, dir2_sensor.columnName)
    end

    if isnothing(dir2_sensor) 
        return (ts.df, dir1_sensor.columnName)
    end

    # If same sensor or only one available, use original data
    if dir1_sensor.height == dir2_sensor.height
        return (ts.df, dir1_sensor.columnName)
    end

    # Create interpolated direction data
    df_interpolated = copy(ts.df)
    interpolated_column = Symbol("WD-$(speed_sensor.height)")
    
    # Calculate interpolation weight
    weight = (speed_sensor.height - dir2_sensor.height) / (dir1_sensor.height - dir2_sensor.height)

    # Interpolate wind direction using angular mean
    df_interpolated[!, interpolated_column] = degreeMean.(
        df_interpolated[!, dir1_sensor.columnName],
        df_interpolated[!, dir2_sensor.columnName],
        weight
    )

    return (df_interpolated, interpolated_column)
end

"""
    analyze_wind_rose(config::AnalyzeConfig)

Analyze wind rose patterns for all masts, including overall and monthly analysis.
"""
function analyze_wind_rose(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "wind-rose")
        
        # Check if air density is configured for power analysis
        has_air_density = !isnothing(mast.airDensity)
        if !has_air_density
            @info "Wind rose power analysis unavailable for mast $(mast.name) - no air density configured. Performing frequency analysis only."
        end
        ts = mast.timeSeriesData
        
        # Find wind speed and direction sensors
        speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", 
                              ts.sensors)
        
        
        mast_results = Dict{String, Any}()
        stats_by_height_freq = Dict{Float64, DataFrame}()
        stats_by_height_power = Dict{Float64, DataFrame}()
        
        # Process each height
        for speed_sensor in speed_sensors
            # Find closest direction sensor by height from below
            (df, dir_columnName) = get_direction_data_for_speed_sensor(speed_sensor, ts)
            
            # Calculate air density at sensor height (if available)
            air_density = has_air_density ? calculate_air_density(speed_sensor.height, mast.airDensity) : nothing
            
            # Overall wind rose analysis
            overall_stats = calculate_sector_statistics(
                df, 
                speed_sensor.columnName, 
                dir_columnName,
                air_density
            )
            
            # Store for multi-height plots
            stats_by_height_freq[speed_sensor.height] = overall_stats
            stats_by_height_power[speed_sensor.height] = overall_stats
            
            # Save overall statistics
            CSV.write(joinpath(output_dir, "wind_rose_stats_$(speed_sensor.height)m.csv"), overall_stats)
            
            # Create individual wind roses for each height
            freq_plot = create_wind_rose_plot(overall_stats, 
                "Wind Direction Frequency Rose - $(mast.name) ($(speed_sensor.height)m)", :frequency)
            save(joinpath(output_dir, "direction_frequency_rose_$(speed_sensor.height)m.svg"), freq_plot)
            
            # Create power-related plots only if air density is available
            if has_air_density
                power_plot = create_wind_rose_plot(overall_stats, 
                    "Wind Power Rose - $(mast.name) ($(speed_sensor.height)m)", :avg_power)
                save(joinpath(output_dir, "wind_power_rose_$(speed_sensor.height)m.svg"), power_plot)
                
                power_freq_plot = create_wind_rose_plot(overall_stats, 
                    "Wind Power Frequency Rose - $(mast.name) ($(speed_sensor.height)m)", :power_frequency)
                save(joinpath(output_dir, "wind_power_frequency_rose_$(speed_sensor.height)m.svg"), power_freq_plot)
            end
            
            mast_results["$(speed_sensor.height)m"] = Dict(
                "overall" => overall_stats
            )
            
            @info "Generated wind rose analysis for mast $(mast.name) at $(speed_sensor.height)m"
        end
        
        # Create combined multi-height plots (only heights >= 100m)
        if length(stats_by_height_freq) > 1
            freq_multi_plot = create_multi_height_wind_rose(
                stats_by_height_freq, 
                "Wind Direction Frequency Rose - $(mast.name) (Heights ≥ 100m)", 
                :frequency
            )
            save(joinpath(output_dir, "direction_frequency_rose_height_gt100m.svg"), freq_multi_plot)
            
            # Create power-related multi-height plots only if air density is available
            if has_air_density
                power_multi_plot = create_multi_height_wind_rose(
                    stats_by_height_power, 
                    "Wind Power Rose - $(mast.name) (Heights ≥ 100m)", 
                    :avg_power
                )
                save(joinpath(output_dir, "wind_power_rose_height_gt100m.svg"), power_multi_plot)
                
                power_freq_multi_plot = create_multi_height_wind_rose(
                    stats_by_height_power, 
                    "Wind Power Frequency Rose - $(mast.name) (Heights ≥ 100m)", 
                    :power_frequency
                )
                save(joinpath(output_dir, "wind_power_frequency_rose_height_gt100m.svg"), power_freq_multi_plot)
            end
            
            @info "Generated combined multi-height wind rose plots for mast $(mast.name)"
        end
        
        # Create wind-rose.typ file for this mast
        typst_file = joinpath(output_dir, "wind-rose.typ")
        if isfile(typst_file)
            rm(typst_file)
        end
        open(typst_file, "w") do f
            println(f, "// Wind Rose Analysis Tables for $(mast.name)")
            println(f, "// Generated by WindRose.jl")
            println(f, "= 风向风能频率分析")
        end
        
        # Monthly analysis for all heights >= 100m
        monthly_stats = analyze_monthly_wind_rose_multi_height(
            mast,
            output_dir,
            has_air_density
        )

        # Export summary tables for heights >= 100m
        export_wind_direction_summary_tables(stats_by_height_freq, stats_by_height_power, 
                                           output_dir, mast.name, typst_file, has_air_density)
        
        
        mast_results["monthly_multi_height"] = monthly_stats
        
        results[mast.name] = mast_results
    end
    
    return results
end

"""
    analyze_monthly_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String, has_air_density::Bool)

Analyze wind rose patterns for each month with all heights >= 100m in one plot.
Power-related analyses are only performed when has_air_density is true.
"""
function analyze_monthly_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String, has_air_density::Bool)
    # Generate frequency roses
    freq_results = analyze_monthly_frequency_wind_rose_multi_height(mast, output_dir)
    
    # Generate power roses only if air density is available
    if has_air_density
        power_results = analyze_monthly_power_wind_rose_multi_height(mast, output_dir)
        power_freq_results = analyze_monthly_power_frequency_wind_rose_multi_height(mast, output_dir)
        return Dict("frequency" => freq_results, "power" => power_results, "power_frequency" => power_freq_results)
    else
        return Dict("frequency" => freq_results)
    end
end

"""
    analyze_monthly_frequency_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String)

Analyze monthly wind direction frequency patterns for all heights >= 100m.
"""
function analyze_monthly_frequency_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String)
    ts = mast.timeSeriesData
    
    # Find wind speed sensors with height >= 100m
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg" && s.height >= 100.0, 
                          ts.sensors)
    
    if isempty(speed_sensors)
        @warn "No wind speed sensors found with height >= 100m for mast $(mast.name)"
        return Dict{Int, Any}()
    end
    
    # Month names
    month_names = Dates.monthname.(1:12)
    
    # Initialize results
    monthly_results = Dict{Int, Any}()
    
    # Create figure for frequency grid (3x4 layout + legend space)
    freq_fig = Figure(size=(4000, 2700))  # Wider to accommodate legend on the side
    
    # Add main title
    Label(freq_fig[0, :], "Monthly Wind Direction Frequency Roses - $(mast.name) (Heights ≥ 100m)", 
          fontsize=24, tellwidth=false)
    
    # Define colors for different heights
    colors = [:blue, :red, :green, :orange, :purple, :cyan, :brown, :pink]
    
    # Store legend elements - collect from month with most complete data
    legend_objects = []
    legend_labels = String[]
    max_heights_count = 0
    
    # Analyze each month and create subplots
    for m in 1:12
        # Calculate grid position (3 rows, 4 columns)
        row = div(m-1, 4) + 1
        col = mod(m-1, 4) + 1
        
        # Collect monthly data for all heights
        stats_by_height = Dict{Float64, DataFrame}()
        has_data = false
        
        for speed_sensor in speed_sensors
            # Get direction data
            (df, dir_columnName) = get_direction_data_for_speed_sensor(speed_sensor, ts)
            
            # Add month column and filter
            df_monthly = copy(df)
            df_monthly.month = month.(df_monthly.timestamp)
            month_data = filter(row -> row.month == m, df_monthly)
            
            if nrow(month_data) == 0
                continue
            end
            
            has_data = true
            
            # Calculate air density and statistics (air density may be nothing)
            air_density = isnothing(mast.airDensity) ? nothing : calculate_air_density(speed_sensor.height, mast.airDensity)
            month_stats = calculate_sector_statistics(month_data, speed_sensor.columnName, dir_columnName, air_density)
            
            stats_by_height[speed_sensor.height] = month_stats
        end
        
        if !has_data
            # Create empty plot for missing month
            freq_ax = Axis(freq_fig[row, col], title=month_names[m])
            text!(freq_ax, 0.5, 0.5, text="No Data", align=(:center, :center))
            hidedecorations!(freq_ax)
            continue
        end
        
        # Create frequency wind rose subplot with multiple heights
        freq_ax = PolarAxis(freq_fig[row, col], title=month_names[m], titlesize=16,
                           theta_0=-π/2, direction=-1)
        
        # Plot each height
        color_idx = 1
        height_stats_sorted = sort(collect(stats_by_height), by = p -> p[1], rev = true)
        
        # Update legend if this month has more complete data
        if length(height_stats_sorted) > max_heights_count
            max_heights_count = length(height_stats_sorted)
            legend_objects = []
            legend_labels = String[]
        end
        
        for (height, stats) in height_stats_sorted
            # Replace zero frequency with small value to maintain complete rose pattern
            values_freq = copy(stats.frequency)
            values_freq[values_freq .== 0] .= 0.01
            
            angles = deg2rad.(stats.angle)
            angles_closed = vcat(angles, angles[1])
            values_closed = vcat(values_freq, values_freq[1])
            
            line_obj = lines!(freq_ax, angles_closed, values_closed, 
                             linewidth=2, color=colors[color_idx])
            
            # Collect legend items from month with most complete data
            if length(height_stats_sorted) == max_heights_count && length(legend_objects) < length(height_stats_sorted)
                push!(legend_objects, line_obj)
                push!(legend_labels, "$(height)m")
            end
            
            color_idx = (color_idx % length(colors)) + 1
        end
        
        # Set grid properties
        freq_ax.rgridcolor = (:gray, 0.2)
        freq_ax.thetagridcolor = (:gray, 0.2)
        freq_ax.rgridwidth = 0.5
        freq_ax.thetagridwidth = 0.5
        
        monthly_results[m] = stats_by_height
    end
    
    # Add legend in dedicated space to the right of the 3x4 grid
    if !isempty(legend_objects)
        Legend(freq_fig[1:3, 5], legend_objects, legend_labels,
               framevisible=true, backgroundcolor=(:white, 0.9),
               titletext="Height", titlesize=14)
    end
    
    # Save the grid plot
    save(joinpath(output_dir, "monthly_direction_frequency_roses_height_gt100m.svg"), freq_fig)
    
    @info "Generated monthly frequency wind rose plots for mast $(mast.name)"
    
    return monthly_results
end

"""
    analyze_monthly_power_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String)

Analyze monthly wind power patterns for all heights >= 100m.
"""
function analyze_monthly_power_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String)
    ts = mast.timeSeriesData
    
    # Find wind speed sensors with height >= 100m
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg" && s.height >= 100.0, 
                          ts.sensors)
    
    if isempty(speed_sensors)
        @warn "No wind speed sensors found with height >= 100m for mast $(mast.name)"
        return Dict{Int, Any}()
    end
    
    # Month names
    month_names = Dates.monthname.(1:12)
    
    # Initialize results
    monthly_results = Dict{Int, Any}()
    
    # Create figure for power grid (3x4 layout + legend space)
    power_fig = Figure(size=(4000, 2700))  # Wider to accommodate legend on the side
    
    # Add main title
    Label(power_fig[0, :], "Monthly Wind Power Roses - $(mast.name) (Heights ≥ 100m)", 
          fontsize=24, tellwidth=false)
    
    # Define colors for different heights
    colors = [:blue, :red, :green, :orange, :purple, :cyan, :brown, :pink]
    
    # Store legend elements - collect from month with most complete data
    legend_objects = []
    legend_labels = String[]
    max_heights_count = 0
    
    # Analyze each month and create subplots
    for m in 1:12
        # Calculate grid position (3 rows, 4 columns)
        row = div(m-1, 4) + 1
        col = mod(m-1, 4) + 1
        
        # Collect monthly data for all heights
        stats_by_height = Dict{Float64, DataFrame}()
        has_data = false
        
        for speed_sensor in speed_sensors
            # Get direction data
            (df, dir_columnName) = get_direction_data_for_speed_sensor(speed_sensor, ts)
            
            # Add month column and filter
            df_monthly = copy(df)
            df_monthly.month = month.(df_monthly.timestamp)
            month_data = filter(row -> row.month == m, df_monthly)
            
            if nrow(month_data) == 0
                continue
            end
            
            has_data = true
            
            # Calculate air density and statistics (air density may be nothing)
            air_density = isnothing(mast.airDensity) ? nothing : calculate_air_density(speed_sensor.height, mast.airDensity)
            month_stats = calculate_sector_statistics(month_data, speed_sensor.columnName, dir_columnName, air_density)
            
            stats_by_height[speed_sensor.height] = month_stats
        end
        
        if !has_data
            # Create empty plot for missing month
            power_ax = Axis(power_fig[row, col], title=month_names[m])
            text!(power_ax, 0.5, 0.5, text="No Data", align=(:center, :center))
            hidedecorations!(power_ax)
            continue
        end
        
        # Create power wind rose subplot with multiple heights
        power_ax = PolarAxis(power_fig[row, col], title=month_names[m], titlesize=16,
                            theta_0=-π/2, direction=-1)
        
        # Plot each height
        color_idx = 1
        height_stats_sorted = sort(collect(stats_by_height), by = p -> p[1], rev = true)
        
        # Update legend if this month has more complete data
        if length(height_stats_sorted) > max_heights_count
            max_heights_count = length(height_stats_sorted)
            legend_objects = []
            legend_labels = String[]
        end
        
        for (height, stats) in height_stats_sorted
            # Replace zero power with small value to maintain complete rose pattern
            values_power = copy(stats.avg_power)
            values_power[values_power .== 0] .= 0.01
            
            angles = deg2rad.(stats.angle)
            angles_closed = vcat(angles, angles[1])
            values_closed = vcat(values_power, values_power[1])
            
            line_obj = lines!(power_ax, angles_closed, values_closed, 
                             linewidth=2, color=colors[color_idx])
            
            # Collect legend items from month with most complete data
            if length(height_stats_sorted) == max_heights_count && length(legend_objects) < length(height_stats_sorted)
                push!(legend_objects, line_obj)
                push!(legend_labels, "$(height)m")
            end
            
            color_idx = (color_idx % length(colors)) + 1
        end
        
        # Set grid properties
        power_ax.rgridcolor = (:gray, 0.2)
        power_ax.thetagridcolor = (:gray, 0.2)
        power_ax.rgridwidth = 0.5
        power_ax.thetagridwidth = 0.5
        
        monthly_results[m] = stats_by_height
    end
    
    # Add legend in dedicated space to the right of the 3x4 grid
    if !isempty(legend_objects)
        Legend(power_fig[1:3, 5], legend_objects, legend_labels,
               framevisible=true, backgroundcolor=(:white, 0.9),
               titletext="Height", titlesize=14)
    end
    
    # Save the grid plot
    save(joinpath(output_dir, "monthly_wind_power_roses_height_gt100m.svg"), power_fig)
    
    @info "Generated monthly power wind rose plots for mast $(mast.name)"
    
    return monthly_results
end

"""
    analyze_monthly_power_frequency_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String)

Analyze monthly wind power frequency patterns for all heights >= 100m.
"""
function analyze_monthly_power_frequency_wind_rose_multi_height(mast::MastAnalyzeConfig, output_dir::String)
    ts = mast.timeSeriesData
    
    # Find wind speed sensors with height >= 100m
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg" && s.height >= 100.0, 
                          ts.sensors)
    
    if isempty(speed_sensors)
        @warn "No wind speed sensors found with height >= 100m for mast $(mast.name)"
        return Dict{Int, Any}()
    end
    
    # Month names
    month_names = Dates.monthname.(1:12)
    
    # Initialize results
    monthly_results = Dict{Int, Any}()
    
    # Create figure for power frequency grid (3x4 layout + legend space)
    power_freq_fig = Figure(size=(4000, 2700))  # Wider to accommodate legend on the side
    
    # Add main title
    Label(power_freq_fig[0, :], "Monthly Wind Power Frequency Roses - $(mast.name) (Heights ≥ 100m)", 
          fontsize=24, tellwidth=false)
    
    # Define colors for different heights
    colors = [:blue, :red, :green, :orange, :purple, :cyan, :brown, :pink]
    
    # Store legend elements - collect from month with most complete data
    legend_objects = []
    legend_labels = String[]
    max_heights_count = 0
    
    # Analyze each month and create subplots
    for m in 1:12
        # Calculate grid position (3 rows, 4 columns)
        row = div(m-1, 4) + 1
        col = mod(m-1, 4) + 1
        
        # Collect monthly data for all heights
        stats_by_height = Dict{Float64, DataFrame}()
        has_data = false
        
        for speed_sensor in speed_sensors
            # Get direction data
            (df, dir_columnName) = get_direction_data_for_speed_sensor(speed_sensor, ts)
            
            # Add month column and filter
            df_monthly = copy(df)
            df_monthly.month = month.(df_monthly.timestamp)
            month_data = filter(row -> row.month == m, df_monthly)
            
            if nrow(month_data) == 0
                continue
            end
            
            has_data = true
            
            # Calculate air density and statistics (air density may be nothing)
            air_density = isnothing(mast.airDensity) ? nothing : calculate_air_density(speed_sensor.height, mast.airDensity)
            month_stats = calculate_sector_statistics(month_data, speed_sensor.columnName, dir_columnName, air_density)
            
            stats_by_height[speed_sensor.height] = month_stats
        end
        
        if !has_data
            # Create empty plot for missing month
            power_freq_ax = Axis(power_freq_fig[row, col], title=month_names[m])
            text!(power_freq_ax, 0.5, 0.5, text="No Data", align=(:center, :center))
            hidedecorations!(power_freq_ax)
            continue
        end
        
        # Create power frequency wind rose subplot with multiple heights
        power_freq_ax = PolarAxis(power_freq_fig[row, col], title=month_names[m], titlesize=16,
                                 theta_0=-π/2, direction=-1)
        
        # Plot each height
        color_idx = 1
        height_stats_sorted = sort(collect(stats_by_height), by = p -> p[1], rev = true)
        
        # Update legend if this month has more complete data
        if length(height_stats_sorted) > max_heights_count
            max_heights_count = length(height_stats_sorted)
            legend_objects = []
            legend_labels = String[]
        end
        
        for (height, stats) in height_stats_sorted
            # Replace zero power frequency with small value to maintain complete rose pattern
            values_power_freq = copy(stats.power_frequency)
            values_power_freq[values_power_freq .== 0] .= 0.01
            
            angles = deg2rad.(stats.angle)
            angles_closed = vcat(angles, angles[1])
            values_closed = vcat(values_power_freq, values_power_freq[1])
            
            line_obj = lines!(power_freq_ax, angles_closed, values_closed, 
                             linewidth=2, color=colors[color_idx])
            
            # Collect legend items from month with most complete data
            if length(height_stats_sorted) == max_heights_count && length(legend_objects) < length(height_stats_sorted)
                push!(legend_objects, line_obj)
                push!(legend_labels, "$(height)m")
            end
            
            color_idx = (color_idx % length(colors)) + 1
        end
        
        # Set grid properties
        power_freq_ax.rgridcolor = (:gray, 0.2)
        power_freq_ax.thetagridcolor = (:gray, 0.2)
        power_freq_ax.rgridwidth = 0.5
        power_freq_ax.thetagridwidth = 0.5
        
        monthly_results[m] = stats_by_height
    end
    
    # Add legend in dedicated space to the right of the 3x4 grid
    if !isempty(legend_objects)
        Legend(power_freq_fig[1:3, 5], legend_objects, legend_labels,
               framevisible=true, backgroundcolor=(:white, 0.9),
               titletext="Height", titlesize=14)
    end
    
    # Save the grid plot
    save(joinpath(output_dir, "monthly_wind_power_frequency_roses_height_gt100m.svg"), power_freq_fig)
    
    @info "Generated monthly power frequency wind rose plots for mast $(mast.name)"
    
    return monthly_results
end

"""
    analyze_all_wind_rose(config::AnalyzeConfig)

Run all wind rose analyses for all masts in the configuration.
"""
function analyze_all_wind_rose(config::AnalyzeConfig)
    return analyze_wind_rose(config)
end

"""
    create_wind_direction_summary_table(stats_by_height::Dict, value_col::Symbol)

Create a summary table with wind directions as rows and heights as columns.
"""
function create_wind_direction_summary_table(stats_by_height::Dict, value_col::Symbol)
    # Filter heights >= 100m and sort
    height_stats_filtered = filter(p -> p[1] >= 100.0, collect(stats_by_height))
    height_stats_sorted = sort(height_stats_filtered, by = p -> p[1], rev = true)
    
    if isempty(height_stats_sorted)
        return DataFrame()
    end
    
    # Get wind direction labels from first height
    first_stats = height_stats_sorted[1][2]
    directions = first_stats.label
    
    # Create base dataframe with directions
    summary_df = DataFrame(Direction = directions)
    
    # Add columns for each height
    for (height, stats) in height_stats_sorted
        col_name = "$(height)m"
        if value_col == :frequency
            # Convert to percentage
            summary_df[!, col_name] = round.(stats[!, value_col] .* 100, digits=2)
        elseif value_col == :power_frequency
            # Convert to percentage  
            summary_df[!, col_name] = round.(stats[!, value_col] .* 100, digits=2)
        else
            summary_df[!, col_name] = round.(stats[!, value_col], digits=2)
        end
    end
    
    return summary_df
end

"""
    export_wind_direction_summary_tables(stats_by_height_freq::Dict, stats_by_height_power::Dict, 
                                        output_dir::String, mast_name::String, typst_file::String, has_air_density::Bool)

Export wind direction frequency and power frequency summary tables and figures to CSV and typst formats.
Power frequency table and figures are only generated when has_air_density is true.
"""
function export_wind_direction_summary_tables(stats_by_height_freq::Dict, stats_by_height_power::Dict, 
                                            output_dir::String, mast_name::String, typst_file::String, has_air_density::Bool)
    
    # Create frequency summary table
    freq_summary = create_wind_direction_summary_table(stats_by_height_freq, :frequency)
    if !isempty(freq_summary)
        # Export to CSV (keep English for encoding compatibility)
        CSV.write(joinpath(output_dir, "wind_direction_frequency_summary_height_gt100m.csv"), freq_summary)
        
        # Create typst table using SummaryTables with Chinese column names
        freq_table = create_summarytables_wind_table(freq_summary, "风向", "风向频率")
        
        # Write typst file using show method
        open(typst_file, "a") do f
            # Add section header
            println(f, "")
            println(f, "== 风向频率分析")
            println(f, "")
            println(f, " 表: [测风塔$(mast_name)代表年风向频率(%) - 高度≥100m],")
            show(f, MIME"text/typst"(), freq_table)
            println(f, "")
            
            # Add frequency wind rose figure
            if isfile(joinpath(output_dir, "direction_frequency_rose_height_gt100m.svg"))
                println(f, " 图: [测风塔$(mast_name)代表年风向频率玫瑰图 - 高度≥100m]")
                println(f, "")
                println(f, "#figure(")
                println(f, "  image(\"direction_frequency_rose_height_gt100m.svg\", width: 80%),")
                println(f, "  caption: [测风塔$(mast_name)代表年风向频率玫瑰图 - 高度≥100m]")
                println(f, ")")
                println(f, "")
            end
            
            # Add monthly frequency wind rose figure
            if isfile(joinpath(output_dir, "monthly_direction_frequency_roses_height_gt100m.svg"))
                println(f, " 图: [测风塔$(mast_name)各月风向频率玫瑰图 - 高度≥100m]")
                println(f, "")
                println(f, "#figure(")
                println(f, "  image(\"monthly_direction_frequency_roses_height_gt100m.svg\", width: 100%),")
                println(f, "  caption: [测风塔$(mast_name)各月风向频率玫瑰图 - 高度≥100m]")
                println(f, ")")
                println(f, "")
            end
        end
    end
    
    # Create power frequency summary table only if air density is available
    if has_air_density
        power_freq_summary = create_wind_direction_summary_table(stats_by_height_power, :power_frequency)
        if !isempty(power_freq_summary)
            # Export to CSV (keep English for encoding compatibility)
            CSV.write(joinpath(output_dir, "wind_power_frequency_summary_height_gt100m.csv"), power_freq_summary)
            
            # Create typst table using SummaryTables with Chinese column names
            power_freq_table = create_summarytables_wind_table(power_freq_summary, "风向", "风能频率")
            
            # Write typst file using show method
            open(typst_file, "a") do f
                # Add section header
                println(f, "")
                println(f, "== 风能频率分析")
                println(f, "")
                println(f, " 表: [测风塔$(mast_name)代表年风能频率(%) - 高度≥100m],")
                show(f, MIME"text/typst"(), power_freq_table)
                println(f, "")
                
                # Add power wind rose figure
                if isfile(joinpath(output_dir, "wind_power_rose_height_gt100m.svg"))
                    println(f, " 图: [测风塔$(mast_name)代表年风功率玫瑰图 - 高度≥100m]")
                    println(f, "")
                    println(f, "#figure(")
                    println(f, "  image(\"wind_power_rose_height_gt100m.svg\", width: 80%),")
                    println(f, "  caption: [测风塔$(mast_name)代表年风功率玫瑰图 - 高度≥100m]")
                    println(f, ")")
                    println(f, "")
                end
                
                # Add power frequency wind rose figure
                if isfile(joinpath(output_dir, "wind_power_frequency_rose_height_gt100m.svg"))
                    println(f, " 图: [测风塔$(mast_name)代表年风能频率玫瑰图 - 高度≥100m]")
                    println(f, "")
                    println(f, "#figure(")
                    println(f, "  image(\"wind_power_frequency_rose_height_gt100m.svg\", width: 80%),")
                    println(f, "  caption: [测风塔$(mast_name)代表年风能频率玫瑰图 - 高度≥100m]")
                    println(f, ")")
                    println(f, "")
                end
                
                # Add monthly power wind rose figure
                if isfile(joinpath(output_dir, "monthly_wind_power_roses_height_gt100m.svg"))
                    println(f, " 图: [测风塔$(mast_name)各月风功率玫瑰图 - 高度≥100m]")
                    println(f, "")
                    println(f, "#figure(")
                    println(f, "  image(\"monthly_wind_power_roses_height_gt100m.svg\", width: 100%),")
                    println(f, "  caption: [测风塔$(mast_name)各月风功率玫瑰图 - 高度≥100m]")
                    println(f, ")")
                    println(f, "")
                end
                
                # Add monthly power frequency wind rose figure
                if isfile(joinpath(output_dir, "monthly_wind_power_frequency_roses_height_gt100m.svg"))
                    println(f, " 图: [测风塔$(mast_name)各月风能频率玫瑰图 - 高度≥100m]")
                    println(f, "")
                    println(f, "#figure(")
                    println(f, "  image(\"monthly_wind_power_frequency_roses_height_gt100m.svg\", width: 100%),")
                    println(f, "  caption: [测风塔$(mast_name)各月风能频率玫瑰图 - 高度≥100m]")
                    println(f, ")")
                    println(f, "")
                end
            end
        end
    end
    
    @info "Generated wind direction summary tables and figures for mast $mast_name"
end

"""
    create_summarytables_wind_table(df::DataFrame, row_header::String, value_type::String)

Create a SummaryTables table from a wind direction summary DataFrame.
"""
function create_summarytables_wind_table(original_df::DataFrame, row_header::String, value_type::String)
    # Get column names (first is Direction, rest are heights/months)
    cols = names(original_df)

    direction_col = cols[1]
    data_cols = cols[2:end]
    df = copy(original_df)
    rename!(df, direction_col => row_header)
    mappings = map(data_cols) do col
        if occursin("m", col)  # Height columns
            new_name = "$col$value_type"
        else  # Month columns  
            new_name = "$col$value_type"
        end
        return col => new_name
    end
    rename!(df, mappings)
    
    # Create SummaryTables using simple_table with column renaming
    return simple_table(df)
end

export analyze_wind_rose, analyze_all_wind_rose

end # module 