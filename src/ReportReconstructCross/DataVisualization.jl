"""
    DataVisualization.jl

Data visualization functions for cross-mast analysis using AlgebraOfGraphics.
Generates individual plot files for each mast pair with proper handling of wind direction wrap-around.
"""
module DataVisualization

using AlgebraOfGraphics
using CairoMakie
using DataFrames
using Statistics
using Printf

# Import types for data structures
using ...Types.CrossMastSpeedModels: CrossMastSpeedPair
using ...Types.CrossMastDirectionModels: CrossMastDirectionPair
using ...Types.MastTimeSeries: TimeSeriesData

export create_mast_pair_plots, create_speed_correlation_plot, create_direction_scatter_plot

"""
    create_mast_pair_plots(analysis_results, output_dir, mast_data)

Generate individual plots for all mast pairs.

# Arguments
- `analysis_results::Vector`: Array of AnalyzePairResult
- `output_dir::String`: Output directory for plots
- `mast_data::Dict{String,TimeSeriesData}`: Dictionary mapping mast names to TimeSeriesData

# Description
Creates individual plot files for each mast pair:
- {target}_{source}_speed_correlations.png
- {target}_{source}_direction_scatter.png
"""
function create_mast_pair_plots(analysis_results::Vector, output_dir::String, mast_data::Dict{String,TimeSeriesData})
    plots_dir = joinpath(output_dir, "plots")
    mkpath(plots_dir)

    for result in analysis_results
        target_name = result.target_mast
        source_name = result.source_mast

        # Get time series data
        target_ts = haskey(mast_data, target_name) ? mast_data[target_name] : nothing
        source_ts = haskey(mast_data, source_name) ? mast_data[source_name] : nothing

        # Speed correlation plot with real data
        speed_plot_file = joinpath(plots_dir, "$(target_name)_$(source_name)_speed_correlations.png")
        create_speed_correlation_plot(result.speed_correlations, speed_plot_file, target_name, source_name, target_ts, source_ts)


        # Direction scatter plot with real data
        direction_plot_file = joinpath(plots_dir, "$(target_name)_$(source_name)_direction_scatter.png")
        create_direction_scatter_plot(result.direction_analysis, direction_plot_file, target_name, source_name, target_ts, source_ts)
    end
end

"""
    create_speed_correlation_plot(correlations, output_file, target_name, source_name, target_ts, source_ts)

Create wind speed correlation scatter plots for a mast pair using actual time series data.

# Arguments
- `correlations::Vector{CrossMastSpeedPair}`: Speed correlation results
- `output_file::String`: Output PNG file path
- `target_name::String`: Target mast name
- `source_name::String`: Source mast name
- `target_ts::Union{TimeSeriesData,Nothing}`: Target mast time series data
- `source_ts::Union{TimeSeriesData,Nothing}`: Source mast time series data

# Description
Creates subplot grid showing correlations for all sensor pairs within this mast pair.
Each subplot represents one sensor pair with scatter plot and correlation info using real data.
"""
function create_speed_correlation_plot(correlations::Vector, output_file::String,
                                       target_name::String, source_name::String,
                                       target_ts::Union{TimeSeriesData,Nothing},
                                       source_ts::Union{TimeSeriesData,Nothing})

    if isempty(correlations)
        @warn "No speed correlations to plot for $(target_name) ← $(source_name)"
        return
    end

    # Filter correlations to high sensors only (>100m or top 2 if insufficient)
    high_correlations = filter(c -> c.target_sensor.height > 100 && c.source_sensor.height > 100, correlations)

    if length(high_correlations) < 2
        # Sort by target sensor height (descending) and take top 2
        sorted_by_height = sort(correlations, by = c -> c.target_sensor.height, rev = true)
        high_correlations = sorted_by_height[1:min(2, length(sorted_by_height))]
    end

    # Prepare data for plotting using actual time series data
    # Store data per sensor pair to avoid redundant filtering
    sensor_pair_data = Dict()

    for (i, corr) in enumerate(high_correlations)
        target_height = corr.target_sensor.height
        source_height = corr.source_sensor.height
        pair_key = "$(target_height)_$(source_height)"

        if !isnothing(target_ts) && !isnothing(source_ts)
            # Use actual time series data
            target_col = corr.target_sensor.columnName
            source_col = corr.source_sensor.columnName

            # Check if columns exist
            if target_col in propertynames(target_ts.df) && source_col in propertynames(source_ts.df)
                # Create merged DataFrame (same as in correlation analysis)
                target_df_subset = select(target_ts.df, :timestamp, target_col => :target)
                source_df_subset = select(source_ts.df, :timestamp, source_col => :source)
                merged_df = innerjoin(target_df_subset, source_df_subset, on = :timestamp)
                clean_df = dropmissing(merged_df)

                if nrow(clean_df) >= 100
                    # Sample data points for visualization (use every Nth point to avoid overcrowding)
                    n_total = nrow(clean_df)
                    sample_interval = max(1, div(n_total, 200))  # Sample ~200 points max
                    sample_indices = 1:sample_interval:n_total

                    source_vals = Float64.(clean_df.source[sample_indices])
                    target_vals = Float64.(clean_df.target[sample_indices])

                    # Store data for this specific sensor pair
                    sensor_pair_data[pair_key] = (
                        source_vals = source_vals,
                        target_vals = target_vals,
                        correlation = corr.correlation,
                        slope = corr.slope,
                        intercept = corr.intercept
                    )
                end
            end
        end
    end

    # Calculate optimal grid dimensions and figure size
    n_pairs = length(high_correlations)
    if n_pairs == 0
        @warn "No high sensor pairs to plot"
        return
    end

    # Calculate grid layout
    if n_pairs == 1
        n_cols, n_rows = 1, 1
        fig_width, fig_height = 600, 500
    elseif n_pairs == 2
        n_cols, n_rows = 2, 1  # Side by side
        fig_width, fig_height = 1000, 500
    elseif n_pairs <= 4
        n_cols, n_rows = 2, 2
        fig_width, fig_height = 1000, 800
    elseif n_pairs <= 6
        n_cols, n_rows = 3, 2
        fig_width, fig_height = 1200, 800
    else
        n_cols = 3
        n_rows = ceil(Int, n_pairs / n_cols)
        fig_width = 1200
        fig_height = max(600, n_rows * 300)  # At least 300px per row
    end

    # Create the plot with calculated dimensions
    fig = Figure(size = (fig_width, fig_height))

    # Create subplots for high correlations only
    for (i, corr) in enumerate(high_correlations)
        row = ceil(Int, i / n_cols)
        col = ((i - 1) % n_cols) + 1

        target_height = corr.target_sensor.height
        source_height = corr.source_sensor.height
        pair_key = "$(target_height)_$(source_height)"

        ax = Axis(fig[row, col],
                 xlabel = "源测风塔风速 (m/s)",
                 ylabel = "目标测风塔风速 (m/s)",
                 title = "$(target_height)m ← $(source_height)m\nr = $(floor(corr.correlation * 1000) / 1000)")

        # Use pre-extracted data for this sensor pair
        if haskey(sensor_pair_data, pair_key)
            pair_data = sensor_pair_data[pair_key]

            scatter!(ax, pair_data.source_vals, pair_data.target_vals,
                    color = :blue, alpha = 0.6, markersize = 4)

            # Add regression line using actual data range
            x_range = [minimum(pair_data.source_vals), maximum(pair_data.source_vals)]
            y_range = corr.slope .* x_range .+ corr.intercept
            lines!(ax, x_range, y_range, color = :red, linewidth = 2)
        else
            # No data found - show empty plot with note
            text!(ax, 0.5, 0.5, text="No data available\nr = $(floor(corr.correlation * 1000) / 1000)",
                  align=(:center, :center), space=:relative)
        end
    end
    
    # Overall title
    Label(fig[0, :], "风速相关性: $(target_name) ← $(source_name)", fontsize = 16, font = :bold)

    # Save the plot
    save(output_file, fig)
    println("    ✓ Speed correlations: $(output_file)")
end

"""
    create_direction_scatter_plot(direction_data, output_file, target_name, source_name, target_ts, source_ts)

Create wind direction scatter plots for a mast pair using actual time series data.

# Arguments
- `direction_data::Vector{CrossMastDirectionPair}`: Direction analysis results
- `output_file::String`: Output PNG file path
- `target_name::String`: Target mast name
- `source_name::String`: Source mast name
- `target_ts::Union{TimeSeriesData,Nothing}`: Target mast time series data
- `source_ts::Union{TimeSeriesData,Nothing}`: Source mast time series data

# Description
Creates subplot grid showing direction relationships for all sensor pairs.
Properly handles 360° wrap-around by adding 360° to smaller values when abs difference > 180°.
"""
function create_direction_scatter_plot(direction_data::Vector, output_file::String,
                                       target_name::String, source_name::String,
                                       target_ts::Union{TimeSeriesData,Nothing},
                                       source_ts::Union{TimeSeriesData,Nothing})
    
    if isempty(direction_data)
        @warn "No direction analysis to plot for $(target_name) ← $(source_name)"
        return
    end
    
    # Prepare data for plotting using actual time series data
    plot_data = []
    for (i, dir_result) in enumerate(direction_data)
        target_height = dir_result.target_sensor.height
        source_height = dir_result.source_sensor.height

        if !isnothing(target_ts) && !isnothing(source_ts)
            # Use actual time series data
            target_col = dir_result.target_sensor.columnName
            source_col = dir_result.source_sensor.columnName

            # Check if columns exist
            if target_col in propertynames(target_ts.df) && source_col in propertynames(source_ts.df)
                # Create merged DataFrame (same as in correlation analysis)
                target_df_subset = select(target_ts.df, :timestamp, target_col => :target)
                source_df_subset = select(source_ts.df, :timestamp, source_col => :source)
                merged_df = innerjoin(target_df_subset, source_df_subset, on = :timestamp)
                clean_df = dropmissing(merged_df)

                if nrow(clean_df) >= 100
                    # Sample data points for visualization (use every Nth point to avoid overcrowding)
                    n_total = nrow(clean_df)
                    sample_interval = max(1, div(n_total, 200))  # Sample ~200 points max
                    sample_indices = 1:sample_interval:n_total

                    source_dirs = Float64.(clean_df.source[sample_indices])
                    target_dirs = Float64.(clean_df.target[sample_indices])

                    # Handle 360° wrap-around for plotting (add 360° to smaller values if abs diff > 180°)
                    for j in eachindex(source_dirs)
                        diff = abs(target_dirs[j] - source_dirs[j])
                        if diff > 180
                            if target_dirs[j] < source_dirs[j]
                                target_dirs[j] += 360
                            else
                                source_dirs[j] += 360
                            end
                        end
                    end

                    sensor_pair = "$(target_height)m ← $(source_height)m"
                    offset_text = @sprintf("offset=%.1f°", dir_result.offset)
                    std_text = @sprintf("std=%.1f°", dir_result.std_deviation)

                    for j in eachindex(source_dirs)
                        push!(plot_data, (
                            source_direction = source_dirs[j],
                            target_direction = target_dirs[j],
                            sensor_pair = sensor_pair,
                            offset_text = offset_text,
                            std_text = std_text,
                            target_height = target_height,
                            source_height = source_height
                        ))
                    end
                end
            end
        end
    end
    
    df = DataFrame(plot_data)
    
    # Create the plot
    fig = Figure(size = (800, 600))
    
    # Calculate grid dimensions
    n_pairs = length(direction_data)
    n_cols = min(3, n_pairs)
    n_rows = ceil(Int, n_pairs / n_cols)
    
    # Create subplots
    for (i, dir_result) in enumerate(direction_data)
        row = ceil(Int, i / n_cols)
        col = ((i - 1) % n_cols) + 1
        
        ax = Axis(fig[row, col],
                 xlabel = "源测风塔风向 (°)",
                 ylabel = "目标测风塔风向 (°)",
                 title = "$(dir_result.target_sensor.height)m ← $(dir_result.source_sensor.height)m\nstd = $(round(dir_result.std_deviation, digits=1))°")
        
        # Filter data for this sensor pair
        pair_data = filter(row -> row.target_height == dir_result.target_sensor.height && 
                                 row.source_height == dir_result.source_sensor.height, df)
        
        if !isempty(pair_data)
            scatter!(ax, pair_data.source_direction, pair_data.target_direction,
                    color = :blue, alpha = 0.6, markersize = 4)
            
            # Add 1:1 reference line
            axis_min = min(minimum(pair_data.source_direction), minimum(pair_data.target_direction))
            axis_max = max(maximum(pair_data.source_direction), maximum(pair_data.target_direction))
            lines!(ax, [axis_min, axis_max], [axis_min, axis_max], 
                   color = :red, linewidth = 2, linestyle = :dash)
        end
    end
    
    # Overall title
    Label(fig[0, :], "风向关系: $(target_name) ← $(source_name)", fontsize = 16, font = :bold)
    
    # Save the plot
    save(output_file, fig)
    println("    ✓ Direction scatter: $(output_file)")
end

end # module 