"""
Violation Data Types Module

This module defines types for representing rule violation data structures
that are read from YAML files (process_stats/process_clean*.yaml).
"""

module ViolationData

using Parameters
import ..Utils: from_dict, to_dict

"""
    ViolationRule

Represents a single violation rule with its violations.

# Fields
- `rule_name::String`: Name of the violated rule
- `count::Int`: Number of violations for this rule
- `timestamps::Vector{String}`: List of timestamps when violations occurred
"""
@with_kw struct ViolationRule
    rule_name::String
    count::Int
    timestamps::Vector{String}
end

"""
    ViolationColumn

Represents violations for a single sensor column.

# Fields
- `column::String`: Column/sensor name
- `total_violations::Int`: Total number of violations for this column
- `rules::Vector{ViolationRule}`: List of violated rules with their details
"""
@with_kw struct ViolationColumn
    column::String
    total_violations::Int
    rules::Vector{ViolationRule}
end

"""
    ViolationSummary

Summary statistics for all violations.

# Fields
- `total_violations::Int`: Total number of violations across all columns
- `violation_percentage::Float64`: Percentage of data points that are violations
"""
@with_kw struct ViolationSummary
    total_violations::Int
    violation_percentage::Float64
end

"""
    ProcessingInfo

Information about the processing that generated the violations.

# Fields
- `mast_name::String`: Name of the mast
- `start_time::String`: Start time of processing (ISO format)
- `end_time::String`: End time of processing (ISO format)
- `total_timestamps::Int`: Total number of timestamps processed
"""
@with_kw struct ProcessingInfo
    mast_name::String
    start_time::String
    end_time::String
    total_timestamps::Int
end

"""
    ViolationAnalysisData

Complete violation data structure as read from YAML files.

# Fields
- `processing_info::ProcessingInfo`: Information about the processing
- `violation_summary::ViolationSummary`: Summary statistics
- `violations_by_column::Vector{ViolationColumn}`: Detailed violations by column
"""
@with_kw struct ViolationAnalysisData
    processing_info::ProcessingInfo
    violation_summary::ViolationSummary
    violations_by_column::Vector{ViolationColumn}
end

# Conversion functions for ViolationRule
function from_dict(::Type{ViolationRule}, d::Dict{String, Any})::ViolationRule
    ViolationRule(
        rule_name = d["rule_name"],
        count = d["count"],
        timestamps = d["timestamps"]
    )
end

function to_dict(vr::ViolationRule)::Dict{String, Any}
    Dict{String, Any}(
        "rule_name" => vr.rule_name,
        "count" => vr.count,
        "timestamps" => vr.timestamps
    )
end

# Conversion functions for ViolationColumn
function from_dict(::Type{ViolationColumn}, d::Dict{String, Any})::ViolationColumn
    rules = [from_dict(ViolationRule, Dict{String, Any}(rule_dict)) for rule_dict in d["rules"]]
    ViolationColumn(
        column = d["column"],
        total_violations = d["total_violations"],
        rules = rules
    )
end

function to_dict(vc::ViolationColumn)::Dict{String, Any}
    Dict{String, Any}(
        "column" => vc.column,
        "total_violations" => vc.total_violations,
        "rules" => [to_dict(rule) for rule in vc.rules]
    )
end

# Conversion functions for ViolationSummary
function from_dict(::Type{ViolationSummary}, d::Dict{String, Any})::ViolationSummary
    ViolationSummary(
        total_violations = d["total_violations"],
        violation_percentage = d["violation_percentage"]
    )
end

function to_dict(vs::ViolationSummary)::Dict{String, Any}
    Dict{String, Any}(
        "total_violations" => vs.total_violations,
        "violation_percentage" => vs.violation_percentage
    )
end

# Conversion functions for ProcessingInfo
function from_dict(::Type{ProcessingInfo}, d::Dict{String, Any})::ProcessingInfo
    ProcessingInfo(
        mast_name = d["mast_name"],
        start_time = d["start_time"],
        end_time = d["end_time"],
        total_timestamps = d["total_timestamps"]
    )
end

function to_dict(pi::ProcessingInfo)::Dict{String, Any}
    Dict{String, Any}(
        "mast_name" => pi.mast_name,
        "start_time" => pi.start_time,
        "end_time" => pi.end_time,
        "total_timestamps" => pi.total_timestamps
    )
end

# Conversion functions for ViolationAnalysisData
function from_dict(::Type{ViolationAnalysisData}, d::Dict{String, Any})::ViolationAnalysisData
    processing_info = from_dict(ProcessingInfo, Dict{String,Any}(d["processing_info"]))
    violation_summary = from_dict(ViolationSummary, Dict{String,Any}(d["violation_summary"]))
    violations_by_column = [from_dict(ViolationColumn, Dict{String,Any}(col_dict)) for col_dict in d["violations_by_column"]]

    ViolationAnalysisData(
        processing_info = processing_info,
        violation_summary = violation_summary,
        violations_by_column = violations_by_column
    )
end

function to_dict(vd::ViolationAnalysisData)::Dict{String, Any}
    Dict{String, Any}(
        "processing_info" => to_dict(vd.processing_info),
        "violation_summary" => to_dict(vd.violation_summary),
        "violations_by_column" => [to_dict(col) for col in vd.violations_by_column]
    )
end

export ViolationRule, ViolationColumn, ViolationSummary, ProcessingInfo, ViolationAnalysisData

end # module ViolationData
