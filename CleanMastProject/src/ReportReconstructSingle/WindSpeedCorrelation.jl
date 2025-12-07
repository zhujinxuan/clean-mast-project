module WindSpeedCorrelation

using DataFrames
using CSV
using Statistics
using DataFramesMeta
using AlgebraOfGraphics
using CairoMakie
using GLM
using LinearAlgebra

# Import necessary functions from AlgebraOfGraphics
using AlgebraOfGraphics: data, mapping, visual, linear, draw
using CairoMakie: Scatter, Axis, Label, save
import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.ReportReconstructSingleConfiguration: ProcessedMastReconstructConfig

"""
    calculate_r2_matrix(data::TimeSeriesData) -> (Matrix{Float64}, Vector{Float64}, DataFrame)

Calculate R² matrix between wind speeds at different heights using functional programming patterns.
Returns the R² matrix, heights vector, and a DataFrame for easier manipulation.
"""
function calculate_r2_matrix(data::TimeSeriesData)
    # Get wind speed sensors (avg only) and sort by height (high to low)
    speed_sensors = data.sensors |> 
                   (sensors -> filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", sensors)) |>
                   (sensors -> sort(sensors, by = s -> s.height, rev=true))
    
    n_heights = length(speed_sensors)
    heights = map(s -> s.height, speed_sensors)
    
    # Create DataFrame with only wind speed columns
    speed_columns = map(s -> s.columnName, speed_sensors)
    speed_df = select(data.df, speed_columns)
    
    # Calculate R² for each pair using map over Cartesian product
    height_pairs = Iterators.product(1:n_heights, 1:n_heights)
    r2_values = map(height_pairs) do (i, j)
        if i == j
            return 1.0
        else
            return calculate_r2_pair(speed_df, speed_sensors[i], speed_sensors[j])
        end
    end
    
    # Reshape into matrix
    r2_matrix = reshape(collect(r2_values), n_heights, n_heights)
    
    # Create DataFrame for the matrix
    column_names = map(h -> Symbol("$(h)m"), heights)
    r2_df = DataFrame(r2_matrix, column_names)
    insertcols!(r2_df, 1, :height => heights)
    
    return r2_matrix, heights, r2_df
end

"""
    calculate_r2_pair(speed_df::DataFrame, sensor1::SensorColumn, sensor2::SensorColumn) -> Float64

Calculate R² between two sensor columns.
"""
function calculate_r2_pair(speed_df::DataFrame, sensor1::SensorColumn, sensor2::SensorColumn)::Float64
    col_i = speed_df[:, sensor1.columnName]
    col_j = speed_df[:, sensor2.columnName]
    
    # Find valid (non-missing) pairs
    valid_pairs = collect(zip(col_i, col_j)) |>
                 (pairs -> filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), pairs))
    
    if length(valid_pairs) <= 10
        return NaN
    end
    
    # Extract x and y values
    valid_x = map(pair -> Float64(pair[1]), valid_pairs)
    valid_y = map(pair -> Float64(pair[2]), valid_pairs)
    
    # Calculate R² using linear regression if there's variance
    if var(valid_x) > 0 && var(valid_y) > 0
        model = lm(@formula(y ~ x), DataFrame(x = valid_x, y = valid_y))
        return r²(model)
    else
        return NaN
    end
end

"""
    calculate_r2_text(df::DataFrame, sensor1::SensorColumn, sensor2::SensorColumn) -> String

Calculate R² text annotation for plotting.
"""
function calculate_r2_text(df::DataFrame, sensor1::SensorColumn, sensor2::SensorColumn)::String
    x_data = df[:, sensor1.columnName]
    y_data = df[:, sensor2.columnName]
    
    # Find valid pairs using functional composition
    valid_pairs = collect(zip(x_data, y_data)) |>
                 (pairs -> filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), pairs))
    
    if length(valid_pairs) <= 10
        return "No data"
    end
    
    # Extract and validate data
    valid_x = map(pair -> Float64(pair[1]), valid_pairs)
    valid_y = map(pair -> Float64(pair[2]), valid_pairs)
    
    if var(valid_x) > 0 && var(valid_y) > 0
        model = lm(@formula(y ~ x), DataFrame(x = valid_x, y = valid_y))
        r2_value = r²(model)
        return "R² = $(round(r2_value, digits=3))"
    else
        return "No variance"
    end
end

"""
    create_correlation_grid_plot(ts_data::TimeSeriesData, height_groups::Tuple{String, Function, Function}, 
                                output_path::String, plot_title::String)

Create a grid plot of wind speed correlations for specified height groups using AlgebraOfGraphics categorical faceting.
"""
function create_correlation_grid_plot(ts_data::TimeSeriesData, 
                                    height_groups::Tuple{String, Function, Function}, 
                                    output_path::String, plot_title::String)
    group_name, filter1, filter2 = height_groups
    
    # Get sensors for each group
    sensors1 = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg" && filter1(s.height), ts_data.sensors)
    sensors2 = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg" && filter2(s.height), ts_data.sensors)
    
    sort!(sensors1, by = s -> s.height, rev=true)
    sort!(sensors2, by = s -> s.height, rev=true)
    
    if isempty(sensors1) || isempty(sensors2)
        @warn "No sensors found for height group: $group_name"
        return nothing
    end
    
    # Generate all sensor pairs excluding same-height comparisons
    sensor_pairs = Iterators.product(sensors1, sensors2) |> collect |>
                  (pairs -> filter(pair -> pair[1].height != pair[2].height, pairs))
    
    if isempty(sensor_pairs)
        @warn "No valid sensor pairs for plotting in group: $group_name"
        return nothing
    end
    
    # Prepare plot data using categorical approach - create long-form data
    plot_data_list = map(sensor_pairs) do (sensor1, sensor2)
        x_data = ts_data.df[:, sensor1.columnName]
        y_data = ts_data.df[:, sensor2.columnName]
        
        # Create DataFrame and drop missing values
        df_pair = DataFrame(
            x = x_data,
            y = y_data,
            source_height = fill("$(sensor1.height)m", length(x_data)),
            target_height = fill("$(sensor2.height)m", length(y_data))
        )
        
        # Drop rows with missing values in x or y
        dropmissing(df_pair, [:x, :y])
    end
    
    # Combine all plot data
    plot_data = reduce(vcat, plot_data_list)
    
    # Calculate R² values for annotations using map  
    r2_data_list = map(sensor_pairs) do (sensor1, sensor2)
        comparison = "$(sensor1.height)m vs $(sensor2.height)m"
        r2_text = calculate_r2_text(ts_data.df, sensor1, sensor2)
        (
            source_height = "$(sensor1.height)m",
            target_height = "$(sensor2.height)m", 
            comparison = comparison,
            r2_text = r2_text
        )
    end
    
    # Convert to DataFrame
    r2_data = DataFrame(r2_data_list)
    
    if nrow(plot_data) == 0
        @warn "No valid data for plotting in group: $group_name"
        return nothing
    end
    
    # Create the main plot using categorical faceting with col and row
    plt = data(plot_data) * 
          mapping(:x, :y, col = :source_height, row = :target_height) * 
          (visual(Scatter, alpha = 0.3, markersize = 6) + linear())
    
    # Draw the plot with categorical faceting
    fig = draw(plt; 
               axis = (;
                   xlabel = "Wind Speed (m/s)",
                   ylabel = "Wind Speed (m/s)"
               ),
               figure = (;
                   size = (1200, 800),
                   fontsize = 12
               ))
    
    # Add overall title
    try
        fig.figure[0, :] = Label(fig.figure, plot_title, fontsize = 16, tellwidth = false)
    catch e
        @debug "Could not add title: $e"
    end
    
    save(output_path, fig)
    
    # Save R² values to a separate CSV file for reference
    r2_output_path = replace(output_path, ".png" => "_r2_values.csv")
    CSV.write(r2_output_path, r2_data)
    
    return fig
end

"""
    determine_high_sensors(sensors::Vector{SensorColumn})

Determine which sensors are considered "high" sensors based on the following logic:
1. If there are at least 3 sensors with height >= 100m, use those sensors (>=100m)
2. Otherwise, use the top 3 highest sensors

Returns a Set of heights that are considered "high" sensors.
"""
function determine_high_sensors(sensors::Vector{SensorColumn})::Set{Float64}
    speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", sensors)
    sorted_sensors = sort(speed_sensors, by = s -> s.height, rev=true)

    high_100m_sensors = filter(s -> s.height >= 100, sorted_sensors)

    if length(high_100m_sensors) >= 3
        return Set(map(s -> s.height, high_100m_sensors))
    else
        top_3 = sorted_sensors[1:min(3, length(sorted_sensors))]
        return Set(map(s -> s.height, top_3))
    end
end

"""
    analyze_wind_speed_correlation(mast::ProcessedMastReconstructConfig, output_dir::String)

Analyze wind speed correlations between different heights.
"""
function analyze_wind_speed_correlation(mast::ProcessedMastReconstructConfig, output_dir::String)
    @info "Analyzing wind speed correlations for mast: $(mast.name)"

    # Calculate R² matrix for after reconstruction data
    r2_matrix, heights, r2_df = calculate_r2_matrix(mast.afterData)

    # Save R² matrix to CSV
    CSV.write(joinpath(output_dir, "wind_speed_r2_matrix.csv"), r2_df)

    # Create correlation plots for different height groups
    plots_dir = joinpath(output_dir, "correlation_plots")
    mkpath(plots_dir)

    # Determine high sensors dynamically
    high_sensor_heights = determine_high_sensors(mast.afterData.sensors)

    # Define height groups for plotting based on dynamic high sensor determination
    height_groups = [
        ("high_vs_high", h -> h in high_sensor_heights, h -> h in high_sensor_heights),
        ("high_vs_low", h -> h in high_sensor_heights, h -> !(h in high_sensor_heights)),
        ("low_vs_low", h -> !(h in high_sensor_heights), h -> !(h in high_sensor_heights))
    ]
    
    # Create plot titles based on actual high sensor heights
    high_heights_str = join(sort(collect(high_sensor_heights), rev=true), "m, ") * "m"

    plot_results = Dict{String, Any}()
    for (group_name, filter1, filter2) in height_groups
        plot_path = joinpath(plots_dir, "correlation_$(group_name).png")
        r2_path = joinpath(plots_dir, "correlation_$(group_name)_r2_values.csv")
        plot_title = if group_name == "high_vs_high"
            "Wind Speed Correlations: High Sensors ($(high_heights_str)) vs High Sensors"
        elseif group_name == "high_vs_low"
            "Wind Speed Correlations: High Sensors ($(high_heights_str)) vs Low Sensors"
        else
            "Wind Speed Correlations: Low Sensors vs Low Sensors"
        end
        
        fig = create_correlation_grid_plot(mast.afterData, (group_name, filter1, filter2), 
                                         plot_path, plot_title)
        plot_results[group_name] = Dict(
            "plot" => plot_path,
            "r2_values" => r2_path
        )
    end
    
    results = Dict{String, Any}(
        "r2_matrix" => r2_matrix,
        "heights" => heights,
        "r2_df" => r2_df,
        "plots" => plot_results
    )
    
    return results
end

export analyze_wind_speed_correlation

end # module 