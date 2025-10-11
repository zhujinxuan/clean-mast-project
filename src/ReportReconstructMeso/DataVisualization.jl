"""
    DataVisualization.jl

Data visualization functions for meso-mast reconstruction analysis using AlgebraOfGraphics.
Generates scatter plots with fitted lines for each meso-mast pair.
"""
module DataVisualization

using AlgebraOfGraphics
using CairoMakie
using DataFrames
using Statistics
using Printf
using GLM

using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.SensorColumns: create_sensor_short_name
using ...TimeSeriesProcessing.Interpolation: interpolate_timeseries

export create_meso_mast_plots, create_sensor_scatter_plot

"""
    create_meso_mast_plots(analysis_results, output_dir, mast_data, meso_data)

Generate individual plots for all meso-mast pairs.

# Arguments
- `analysis_results::Vector`: Array of AnalyzeMesoMastResult
- `output_dir::String`: Output directory for plots
- `mast_data::Dict{String,TimeSeriesData}`: Dictionary mapping mast names to TimeSeriesData
- `meso_data::Dict{String,TimeSeriesData}`: Dictionary mapping meso names to TimeSeriesData
"""
function create_meso_mast_plots(
    analysis_results::Vector,
    output_dir::String,
    mast_data::Dict{String,TimeSeriesData},
    meso_data::Dict{String,TimeSeriesData}
)
    plots_dir = joinpath(output_dir, "plots")
    mkpath(plots_dir)

    for result in analysis_results
        mast_name = result.mast_name
        meso_name = result.meso_name

        mast_ts = haskey(mast_data, mast_name) ? mast_data[mast_name] : nothing
        meso_ts = haskey(meso_data, meso_name) ? meso_data[meso_name] : nothing

        if isnothing(mast_ts) || isnothing(meso_ts)
            @warn "Missing data for $(mast_name) ← $(meso_name), skipping plot"
            continue
        end

        plot_file = joinpath(plots_dir, "$(mast_name)_$(meso_name)_sensors.png")
        create_sensor_scatter_plot(
            mast_ts,
            meso_ts,
            result.sensor_metrics,
            plot_file,
            mast_name,
            meso_name
        )
    end
end

"""
    create_sensor_scatter_plot(mast_ts, meso_ts, sensor_metrics, output_file, mast_name, meso_name)

Create scatter plots with fitted lines for top sensor pairs.

# Arguments
- `mast_ts::TimeSeriesData`: Mast time series data
- `meso_ts::TimeSeriesData`: Meso time series data
- `sensor_metrics::Vector`: Sensor pair metrics
- `output_file::String`: Output PNG file path
- `mast_name::String`: Mast name
- `meso_name::String`: Meso name
"""
function create_sensor_scatter_plot(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    sensor_metrics::Vector,
    output_file::String,
    mast_name::String,
    meso_name::String
)
    if isempty(sensor_metrics)
        @warn "No sensor metrics to plot for $(mast_name) ← $(meso_name)"
        return
    end

    # Interpolate meso to match mast timestamps
    meso_ts_aligned = interpolate_timeseries(
        meso_ts,
        mast_ts.df.timestamp
    )

    top_metrics = sort(sensor_metrics, by = m -> m.correlation, rev = true)[1:min(3, length(sensor_metrics))]

    n_plots = length(top_metrics)
    fig = Figure(size = (400 * n_plots, 400))

    for (i, metrics) in enumerate(top_metrics)
        mast_col = metrics.mast_sensor.columnName
        meso_col = metrics.meso_sensor.columnName

        if !hasproperty(mast_ts.df, mast_col)
            error("Mast column $(mast_col) not found in mast data for $(mast_name). This should not happen - column exists in analysis but not in visualization.")
        end

        if !hasproperty(meso_ts_aligned.df, meso_col)
            error("Meso column $(meso_col) not found in meso data for $(meso_name). This should not happen - column exists in analysis but not in visualization.")
        end

        mast_vec = mast_ts.df[!, mast_col]
        meso_vec = meso_ts_aligned.df[!, meso_col]

        valid_mask = .!(ismissing.(mast_vec) .| ismissing.(meso_vec))

        if count(valid_mask) < 10
            continue
        end

        mast_valid = collect(skipmissing(mast_vec[valid_mask]))
        meso_valid = collect(skipmissing(meso_vec[valid_mask]))

        plot_df = DataFrame(
            meso = meso_valid,
            mast = mast_valid
        )

        model = lm(@formula(mast ~ meso), plot_df)
        coefs = coef(model)
        intercept = coefs[1]
        slope = coefs[2]

        mast_short = create_sensor_short_name(metrics.mast_sensor)
        meso_short = create_sensor_short_name(metrics.meso_sensor)

        ax = Axis(
            fig[1, i],
            xlabel = "Meso: $(meso_short) (m/s)",
            ylabel = "Mast: $(mast_short) (m/s)",
            title = "$(mast_name) ← $(meso_name)\nr=$((@sprintf "%.3f" metrics.correlation)), RMSE=$((@sprintf "%.2f" metrics.rmse)) m/s\ny=$((@sprintf "%.2f" slope))x + $((@sprintf "%.2f" intercept))"
        )

        scatter!(
            ax,
            plot_df.meso,
            plot_df.mast,
            color = (:blue, 0.3),
            markersize = 3
        )

        x_range = range(minimum(plot_df.meso), maximum(plot_df.meso), length = 100)
        y_fitted = intercept .+ slope .* x_range
        lines!(
            ax,
            x_range,
            y_fitted,
            color = :red,
            linewidth = 2,
            linestyle = :dash
        )

        xlims!(ax, 0, maximum(plot_df.meso) * 1.1)
        ylims!(ax, 0, maximum(plot_df.mast) * 1.1)
    end

    save(output_file, fig)
    println("      ✓ Saved plot: $(basename(output_file))")
end

end # module
