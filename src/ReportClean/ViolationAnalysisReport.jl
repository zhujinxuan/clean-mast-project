"""
Violation Analysis Report Generation Module

This module generates the "规则违规分析" (Rule Violation Analysis) section of the clean report.
It provides detailed analysis of data cleaning rule violations for each mast with table format,
Chinese translations, and time series visualizations.
"""

module ViolationAnalysisReport

using DataFrames
using Statistics
using Dates
using AlgebraOfGraphics, CairoMakie
using ....Types.ReportCleanData: MastReportData
using ....Types.ViolationData: ViolationAnalysisData, ViolationColumn, ViolationRule
using ..DataCoverageReport: create_short_sensor_name

export generate_violation_analysis_section

# Type alias for the violations_by_column parameter
const ViolationsByColumn = Vector{ViolationColumn}

# Chinese translations for rule names
const RULE_TRANSLATIONS = Dict{String, String}(
    "Wind Speed Range" => "风速范围检查",
    "Wind Direction Range" => "风向范围检查",
    "High Wind Speed Layer Difference" => "高风速层差检查",
    "High Wind Speed Layer Difference; 50m" => "高风速层差检查(50m)",
    "Icing WS Detection" => "风速结冰检测",
    "Icing WD Detection" => "风向结冰检测",
    "range_check" => "范围检查",
    "icing_detection" => "结冰检测",
    "layer_difference" => "层差检查",
    "out_of_range" => "超出范围"
)

"""
    get_chinese_rule_name(rule_name::String)

Get Chinese translation for rule name, fallback to original if not found.
"""
function get_chinese_rule_name(rule_name::String)
    return get(RULE_TRANSLATIONS, rule_name, rule_name)
end



"""
    create_violation_timeseries_plot(violations_by_column::ViolationsByColumn, mast_name::String, output_dir::String)

Create bar chart visualization of violations by sensor and rule with monthly facets.
X-axis: sensor channels, Y-axis: violation counts, Facets: months, Stacked by rules.
Returns the path to the generated SVG file.
"""
function create_violation_timeseries_plot(violations_by_column::ViolationsByColumn, mast_name::String, output_dir::String)::Union{String, Nothing}
    if isempty(violations_by_column)
        return nothing
    end

    # Collect violation counts by sensor, rule, and month
    violation_data = NamedTuple{(:sensor, :rule, :month_name, :violation_count), Tuple{String, String, String, Int}}[]

    for column_data in violations_by_column
        column_name = column_data.column

        for rule in column_data.rules
            rule_name = rule.rule_name
            chinese_rule = get_chinese_rule_name(rule_name)
            timestamps = rule.timestamps

            # Group timestamps by month
            monthly_counts = Dict{String, Int}()

            for ts_str in timestamps
                # Parse timestamp and get month name
                ts = DateTime(ts_str)
                month_name = Dates.format(ts, "yyyy-mm")
                monthly_counts[month_name] = get(monthly_counts, month_name, 0) + 1
            end

            # Add data for each month that has violations
            for (month_name, count) in monthly_counts
                push!(violation_data, (
                    sensor = column_name,
                    rule = chinese_rule,
                    month_name = month_name,
                    violation_count = count
                ))
            end
        end
    end

    if isempty(violation_data)
        return nothing
    end

    # Convert to DataFrame
    df = DataFrame(violation_data)

    # Create stacked bar chart with monthly facets
    fig = data(df) *
          mapping(:sensor, :violation_count, color=:rule, layout=:month_name) *
          visual(BarPlot) |>
          draw(facet=(; linkyaxes=:none),
               axis=(ylabel="违规次数",
                     xlabel="传感器",
                     xticklabelrotation=π/4,  # Rotate sensor names for better readability
                     title="$(mast_name) - 违规分析（按月份分面）"))

    # Save plot
    mkpath(output_dir)
    plot_path = joinpath(output_dir, "violation_timeseries_$(mast_name).png")
    save(plot_path, fig, size=(1400, 1000))  # Larger size for better readability

    return plot_path
end

"""
    create_violation_monthly_faceted_plot(violations_by_column::ViolationsByColumn, mast_name::String, mast::MastReportData, output_dir::String)

Create comprehensive data quality visualization combining:
- Violation counts by rule type (stacked bars)
- Missing data percentages (separate metric)
- X-axis: Months, Faceted by sensors
Returns the path to the generated PNG file.
"""
function create_violation_monthly_faceted_plot(violations_by_column::ViolationsByColumn, mast_name::String, mast::MastReportData, output_dir::String)::Union{String, Nothing}
    if isempty(violations_by_column)
        @warn "No violations data for $(mast_name)"
        return nothing
    end

    @info "Creating faceted plot for $(mast_name) with $(length(violations_by_column)) violation columns"

    # Create mapping from column names to short sensor names
    column_to_sensor = Dict{String, eltype(mast.clean_data.sensors)}()
    for sensor in mast.clean_data.sensors
        column_to_sensor[string(sensor.columnName)] = sensor
    end

    # Collect violation data by month, sensor, and rule
    violation_data = NamedTuple{(:month, :sensor, :rule, :violation_count), Tuple{String, String, String, Int}}[]

    for column_data in violations_by_column
        column_name = column_data.column

        # Get short sensor name
        short_sensor_name = if haskey(column_to_sensor, column_name)
            create_short_sensor_name(column_to_sensor[column_name])
        else
            column_name
        end

        for rule in column_data.rules
            rule_name = rule.rule_name
            chinese_rule = get_chinese_rule_name(rule_name)
            timestamps = rule.timestamps

            # Group timestamps by month
            monthly_counts = Dict{String, Int}()

            for ts_str in timestamps
                # Parse timestamp and format as YYYY-MM
                ts = DateTime(ts_str)
                month_name = Dates.format(ts, "yyyy-mm")
                monthly_counts[month_name] = get(monthly_counts, month_name, 0) + 1
            end

            # Add data for each month that has violations
            for (month_name, count) in monthly_counts
                push!(violation_data, (
                    month = month_name,
                    sensor = short_sensor_name,
                    rule = chinese_rule,
                    violation_count = count
                ))
            end
        end
    end

    if isempty(violation_data)
        @warn "No violation data collected for $(mast_name)"
        return nothing
    end

    @info "Collected $(length(violation_data)) violation data points for $(mast_name)"

    # Convert to DataFrame for plotting
    df = DataFrame(violation_data)

    # Sort months chronologically for proper ordering
    month_order = sort(unique(df.month))

    # Create faceted plot using AlgebraOfGraphics
    # Each sensor gets its own facet, with months on x-axis and dodged bars for rules
    plot_spec = data(df) *
        mapping(:month => sorter(month_order), :violation_count,
                col = :sensor,  # Facet by sensor
                color = :rule,  # Color by rule type
                dodge = :rule   # Dodge bars by rule type
        ) *
        visual(BarPlot)

    # Create the figure and draw the plot
    fig = draw(plot_spec,
        figure = (size = (1400, 800),),
        axis = (xticklabelrotation = π/4,),
        facet = (linkxaxes = :minimal, linkyaxes = :all)
    )

    # Note: Title is handled by the report document, not the plot itself

    # Save plot
    mkpath(output_dir)
    plot_path = joinpath(output_dir, "violation_monthly_faceted_$(mast_name).png")
    save(plot_path, fig.figure)

    return plot_path
end







"""
    generate_violation_analysis_section(mast_data::Vector{MastReportData}, plots_dir::String)

Generate the complete violation analysis section in Typst format with table format
and Chinese translations.
Returns a string containing the Typst markup for the violation analysis.
"""
function generate_violation_analysis_section(mast_data::Vector{MastReportData}, plots_dir::String) :: String
    sections = String[]

    push!(sections, "== 4. 规则违规分析")
    push!(sections, "")

    for mast in mast_data
        # Access properly typed violation data directly
        violation_analysis = mast.violation_data
        total_violations = violation_analysis.violation_summary.total_violations
        violations_by_column = violation_analysis.violations_by_column

        # Check if there are any violations
        if total_violations == 0 || isempty(violations_by_column)
            @info "No violations found for mast $(mast.name)"
            push!(sections, "=== $(mast.name)")
            push!(sections, "")
            push!(sections, "该测风塔无违规记录。")
            push!(sections, "")
            continue
        end

        @info "Processing mast $(mast.name): found $(length(violations_by_column)) violation columns"

        # Generate mast section
        push!(sections, "=== $(mast.name)")
        push!(sections, "")
        push!(sections, "总违规数量: $(total_violations)")
        push!(sections, "")

        # Create and add violation visualization if violations exist
        if !isempty(violations_by_column)
            # Create stacked bar chart visualization
            mkpath(plots_dir)

            plot_path = create_violation_monthly_faceted_plot(violations_by_column, mast.name, mast, plots_dir)

            if !isnothing(plot_path)
                push!(sections, "==== 违规分析图表")
                push!(sections, "")
                push!(sections, "#figure(")
                push!(sections, "  image(\"plots/$(basename(plot_path))\"),")
                push!(sections, "  caption: [$(mast.name) 月度违规分析 - 按传感器分面的柱状图，规则类型用颜色区分],")
                push!(sections, ")")
                push!(sections, "")
            else
                @warn "Failed to create violation plot for $(mast.name)"
            end
        else
            push!(sections, "该测风塔无违规记录。")
            push!(sections, "")
        end
    end

    return join(sections, "\n")
end

end # module ViolationAnalysisReport
