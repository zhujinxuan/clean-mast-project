module AnnualClimatology

using DataFrames
using CSV
using AlgebraOfGraphics, CairoMakie
using Statistics
using Dates
using DataFramesMeta
using SummaryTables

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
import ...Types.ReportMesoTimeSeriesConfiguration: ReportMesoTimeSeriesConfig, MesoReportMesoTimeSeriesConfig, get_output_path

export analyze_annual_climatology, analyze_all

"""
    find_highest_wind_speed_sensor(sensors::Vector{SensorColumn}) -> Union{SensorColumn, Nothing}

Find the highest wind speed sensor (by height) from a list of sensors.
Only considers WindSpeed sensors with avg statType.
"""
function find_highest_wind_speed_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}
    wind_speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", sensors)

    if isempty(wind_speed_sensors)
        return nothing
    end

    return wind_speed_sensors[argmax([s.height for s in wind_speed_sensors])]
end

"""
    calculate_annual_statistics(df::DataFrame, sensor::SensorColumn) -> DataFrame

Calculate annual statistics for a given wind speed sensor.

# Arguments
- `df::DataFrame`: Time series data with timestamp column
- `sensor::SensorColumn`: Wind speed sensor to analyze

# Returns
- `DataFrame`: Table with columns: year, annual_mean, difference, climatology
"""
function calculate_annual_statistics(df::DataFrame, sensor::SensorColumn)::DataFrame
    df_with_year = @transform df :year = year.(:timestamp)

    annual_means = combine(
        groupby(df_with_year, :year),
        sensor.columnName => (x -> mean(skipmissing(x))) => :annual_mean
    )

    sort!(annual_means, :year)

    climatology = mean(skipmissing(annual_means.annual_mean))

    annual_means.climatology .= climatology
    annual_means.difference = ((annual_means.annual_mean .- climatology) ./ climatology) .* 100

    return annual_means
end

"""
    generate_climatology_plot(annual_stats::DataFrame, meso_name::String, sensor_height::Float64, output_path::String)

Generate a plot showing annual wind speed timeseries with climatology line.

# Arguments
- `annual_stats::DataFrame`: Annual statistics table
- `meso_name::String`: Name of the meso dataset
- `sensor_height::Float64`: Height of the sensor
- `output_path::String`: Path to save the SVG plot
"""
function generate_climatology_plot(annual_stats::DataFrame, meso_name::String, sensor_height::Float64, output_path::String)
    plot_data = copy(annual_stats)

    fig = Figure(size=(800, 500))
    ax = Axis(
        fig[1, 1],
        title="$(meso_name) - Annual Wind Speed at $(sensor_height)m",
        xlabel="Year",
        ylabel="Annual Mean Wind Speed (m/s)"
    )

    lines!(ax, plot_data.year, plot_data.annual_mean, label="Annual Mean", linewidth=2)

    hlines!(ax, [plot_data.climatology[1]], label="Climatology",
            color=:red, linestyle=:dash, linewidth=2)

    axislegend(ax, position=:rb)

    save(output_path, fig)
    empty!(fig)

    return nothing
end

"""
    generate_typst_report(annual_stats::DataFrame, meso_name::String, sensor_height::Float64, output_dir::String)

Generate a Typst report with annual climatology table and plot.

# Arguments
- `annual_stats::DataFrame`: Annual statistics table
- `meso_name::String`: Name of the meso dataset
- `sensor_height::Float64`: Height of the sensor
- `output_dir::String`: Output directory path
"""
function generate_typst_report(annual_stats::DataFrame, meso_name::String, sensor_height::Float64, output_dir::String)
    typst_path = joinpath(output_dir, "annual_climatology.typ")

    table_df = copy(annual_stats)

    table_df.year = string.(table_df.year)
    table_df.annual_mean = [round(v, digits=3) for v in table_df.annual_mean]
    table_df.difference = [round(v, digits=3) for v in table_df.difference]
    table_df.climatology = [round(v, digits=3) for v in table_df.climatology]

    cols = [
        :year => "年份",
        :annual_mean => "年平均风速 (m/s)",
        :climatology => "气候平均 (m/s)",
        :difference => "与气候差值 (%)"
    ]

    table = simple_table(table_df, cols, round_digits=2)

    open(typst_path, "w") do io
        println(io, "== $(meso_name) 年际风速变化分析")
        println(io)
        println(io, "=== 分析高度")
        println(io)
        println(io, "本分析使用最高测风传感器：$(sensor_height)m")
        println(io)
        println(io, "=== 年际风速变化图")
        println(io)
        println(io, "#figure(")
        println(io, "  image(\"annual_climatology.png\"),")
        println(io, "  caption: [$(meso_name) 年际风速变化及气候平均],")
        println(io, ")")
        println(io)
        println(io, "=== 年际风速统计表")
        println(io)
        show(io, MIME"text/typst"(), table)
        println(io)
        println(io)
        println(io, "=== 统计摘要")
        println(io)

        climatology_value = annual_stats.climatology[1]
        max_year = annual_stats.year[argmax(annual_stats.annual_mean)]
        max_value = maximum(annual_stats.annual_mean)
        min_year = annual_stats.year[argmin(annual_stats.annual_mean)]
        min_value = minimum(annual_stats.annual_mean)

        println(io, "- 气候平均风速：$(round(climatology_value, digits=3)) m/s")
        println(io, "- 最高年份：$(max_year)年，年平均风速 $(round(max_value, digits=2)) m/s")
        println(io, "- 最低年份：$(min_year)年，年平均风速 $(round(min_value, digits=2)) m/s")
        println(io, "- 年际变化范围：$(round(max_value - min_value, digits=2)) m/s")
    end

    @info "Generated Typst report at: $typst_path"

    return nothing
end

"""
    analyze_annual_climatology(config::ReportMesoTimeSeriesConfig)

Analyze annual wind speed climatology for all mesos in the configuration.

# Arguments
- `config::ReportMesoTimeSeriesConfig`: Configuration with meso data

# Returns
- `Dict{String, Any}`: Results dictionary with annual statistics for each meso
"""
function analyze_annual_climatology(config::ReportMesoTimeSeriesConfig)::Dict{String, Any}
    results = Dict{String, Any}()

    for meso in config.mesos
        @info "Analyzing annual climatology for meso: $(meso.name)"

        highest_sensor = find_highest_wind_speed_sensor(meso.timeSeriesData.sensors)

        if isnothing(highest_sensor)
            @warn "No wind speed sensors found for meso $(meso.name)"
            continue
        end

        @info "Using highest sensor at $(highest_sensor.height)m for meso $(meso.name)"

        annual_stats = calculate_annual_statistics(meso.timeSeriesData.df, highest_sensor)

        output_dir = get_output_path(config, meso.name)

        csv_path = joinpath(output_dir, "annual_climatology.csv")
        CSV.write(csv_path, annual_stats)
        @info "Saved annual statistics to: $csv_path"

        svg_path = joinpath(output_dir, "annual_climatology.png")
        generate_climatology_plot(annual_stats, meso.name, highest_sensor.height, svg_path)
        @info "Saved climatology plot to: $svg_path"

        generate_typst_report(annual_stats, meso.name, highest_sensor.height, output_dir)

        results[meso.name] = annual_stats
    end

    return results
end

"""
    analyze_all(config::ReportMesoTimeSeriesConfig)

Run all analyses for report meso-timeseries.

# Arguments
- `config::ReportMesoTimeSeriesConfig`: Configuration with meso data

# Returns
- `Dict{String, Any}`: Results dictionary
"""
function analyze_all(config::ReportMesoTimeSeriesConfig)::Dict{String, Any}
    results = Dict{String, Any}()

    results["annual_climatology"] = analyze_annual_climatology(config)

    return results
end

end # module
