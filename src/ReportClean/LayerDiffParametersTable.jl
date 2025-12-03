"""
Layer Difference Parameters Table Generation Module

This module generates the "主要参数的合理相关性表" (Main Parameters Reasonable Correlation Table)
section showing layer difference thresholds for wind speed and direction comparisons.
"""

module LayerDiffParametersTable

using DataFrames
using ....Types.CleanRules: Rule, LayerDifferenceCriteria, RangeCriteria
using ....Types.SensorColumns: SensorColumn
using ....Types.ReportCleanData: MastReportData

export generate_layer_diff_parameters_for_all_masts

"""
    LayerComparisonRow

Represents a single row in the layer difference parameters table.
"""
struct LayerComparisonRow
    upper_height::Float64
    lower_height::Float64
    sensor_type::String
    threshold::String
    note::String
end

"""
    extract_layer_diff_rules(rules::Vector{Rule})::Vector{Rule}

Extract only layer difference rules from the full rule set.
"""
function extract_layer_diff_rules(rules::Vector{Rule})::Vector{Rule}
    return filter(r -> r.criteria isa LayerDifferenceCriteria, rules)
end

"""
    find_applicable_height_pairs(
        rule::Rule,
        sensors::Vector{SensorColumn}
    )::Vector{Tuple{Float64, Float64}}

Find all height pairs that this rule applies to based on sensor inventory.
Returns vector of (upper_height, lower_height) tuples.
"""
function find_applicable_height_pairs(
    rule::Rule,
    sensors::Vector{SensorColumn}
)::Vector{Tuple{Float64, Float64}}
    @assert rule.criteria isa LayerDifferenceCriteria

    criteria = rule.criteria
    height_diff = criteria.lower_layer_height

    target_sensors = filter(sensors) do s
        s.sensorType == rule.sensorType &&
        s.statType == "avg" &&
        (isnothing(rule.height.min) || s.height >= rule.height.min) &&
        (isnothing(rule.height.max) || s.height <= rule.height.max)
    end

    pairs = Tuple{Float64, Float64}[]

    for target in target_sensors
        lower_sensors = filter(sensors) do s
            s.sensorType == rule.sensorType &&
            s.statType == "avg" &&
            s.height < target.height &&
            (target.height - s.height) <= height_diff
        end

        for lower in lower_sensors
            push!(pairs, (target.height, lower.height))
        end
    end

    return unique(pairs)
end

"""
    format_threshold(criteria::RangeCriteria, sensor_type::String)::String

Format the threshold value with appropriate units and comparison operators.
Escapes < and > for Typst syntax.
"""
function format_threshold(criteria::RangeCriteria, sensor_type::String)::String
    unit = sensor_type == "WindSpeed" ? "m/s" : "°"

    if !isnothing(criteria.max)
        return "\\<$(criteria.max)$(unit)"
    elseif !isnothing(criteria.min)
        return "\\>$(criteria.min)$(unit)"
    else
        return "未指定"
    end
end

"""
    create_comparison_rows(
        rules::Vector{Rule},
        sensors::Vector{SensorColumn}
    )::Vector{LayerComparisonRow}

Create table rows for all layer difference rules and applicable height pairs.
"""
function create_comparison_rows(
    rules::Vector{Rule},
    sensors::Vector{SensorColumn}
)::Vector{LayerComparisonRow}
    rows = LayerComparisonRow[]

    layer_diff_rules = extract_layer_diff_rules(rules)

    for rule in layer_diff_rules
        criteria = rule.criteria::LayerDifferenceCriteria
        height_pairs = find_applicable_height_pairs(rule, sensors)

        for (upper, lower) in height_pairs
            threshold = format_threshold(criteria.abs_diff, rule.sensorType)
            note = "参考值"

            row = LayerComparisonRow(
                upper,
                lower,
                rule.sensorType,
                threshold,
                note
            )
            push!(rows, row)
        end
    end

    return rows
end

"""
    sort_comparison_rows(rows::Vector{LayerComparisonRow})::Vector{LayerComparisonRow}

Sort rows by sensor type (WindSpeed first), then by upper height descending.
"""
function sort_comparison_rows(rows::Vector{LayerComparisonRow})::Vector{LayerComparisonRow}
    return sort(rows, by = r -> (
        r.sensor_type == "WindSpeed" ? 0 : 1,
        -r.upper_height
    ))
end

"""
    format_height_pair(upper::Float64, lower::Float64)::String

Format height pair display (e.g., "140m/120m").
"""
function format_height_pair(upper::Float64, lower::Float64)::String
    upper_str = upper == floor(upper) ? string(Int(upper)) : string(upper)
    lower_str = lower == floor(lower) ? string(Int(lower)) : string(lower)
    return "$(upper_str)m/$(lower_str)m"
end

"""
    generate_typst_table(rows::Vector{LayerComparisonRow})::String

Generate Typst markup for the layer difference parameters table.
"""
function generate_typst_table(rows::Vector{LayerComparisonRow})::String
    if isempty(rows)
        return "未发现层差检查规则。"
    end

    lines = String[
        "#figure(",
        "  table(",
        "    columns: 3,",
        "    align: center,",
        "    [*主要参数*], [*合理相关性范围*], [*备注*],"
    ]

    ws_rows = filter(r -> r.sensor_type == "WindSpeed", rows)
    wd_rows = filter(r -> r.sensor_type == "WindDirection", rows)

    for row in ws_rows
        height_pair = format_height_pair(row.upper_height, row.lower_height)
        push!(lines, "    [$(height_pair) 高度小时平均风速差值], [$(row.threshold)], [$(row.note)],")
    end

    for row in wd_rows
        height_pair = format_height_pair(row.upper_height, row.lower_height)
        push!(lines, "    [$(height_pair) 高度小时平均风向差值], [$(row.threshold)], [$(row.note)],")
    end

    push!(lines, "  ),")
    push!(lines, "  caption: [层差检查参数合理相关性表]")
    push!(lines, ")")

    return join(lines, "\n")
end

"""
    generate_layer_diff_parameters_for_all_masts(
        mast_data::Vector{MastReportData},
        rules::Vector{Rule}
    )::String

Generate layer difference parameters section with subsections for each mast.
Returns a string containing the Typst markup for all masts.
"""
function generate_layer_diff_parameters_for_all_masts(
    mast_data::Vector{MastReportData},
    rules::Vector{Rule}
)::String
    if isempty(mast_data) || isempty(rules)
        return ""
    end

    # Generate header section
    header = """
=== 层差检查参数

以下表格列出了数据清洗过程中使用的层差检查参数及其合理相关性范围。

"""

    # Generate table for each mast
    mast_sections = map(mast_data) do mast
        sensors = mast.clean_data.sensors
        rows = create_comparison_rows(rules, sensors)
        sorted_rows = sort_comparison_rows(rows)
        table_markup = generate_typst_table(sorted_rows)

        """
==== $(mast.name)

$(table_markup)
"""
    end

    # Combine header and all mast sections
    return header * join(mast_sections, "\n")
end

end # module
