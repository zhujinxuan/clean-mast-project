module ReportCleanConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource, adjust_timeseries_source_paths, adjust_timeseries_source_paths_to_parquet
using ..ProcessCleanConfig: ProcessCleanConfiguration, load_rules
using ..CleanRules: Rule, RangeCriteria, LayerDifferenceCriteria, IcingCriteria, AvailabilityCriteria
using Parameters

export ReportCleanMast, ReportCleanMastGroup, ReportCleanOutput, ReportCleanConfiguration, to_report_clean_config

@with_kw struct ReportCleanMast
    name::String
    input::TimeSeriesSource
    rules::Union{Vector{Rule}, Nothing} = nothing
end

@with_kw struct ReportCleanMastGroup
    masts::Vector{ReportCleanMast}
end

@with_kw struct ReportCleanOutput
    report_dir::String = "./clean"
    report_filename::String = "report.typ"
end

@with_kw struct ReportCleanConfiguration
    raw::ReportCleanMastGroup
    clean::ReportCleanMastGroup
    output::ReportCleanOutput = ReportCleanOutput()
end

# from_dict implementations using existing pattern
function from_dict(::Type{ReportCleanMast}, dict::Dict{String, Any})
    rules = if haskey(dict, "rules")
        [from_dict(Rule, r) for r in dict["rules"]]
    else
        nothing
    end

    return ReportCleanMast(
        name = dict["name"],
        input = from_dict(TimeSeriesSource, dict["input"]),
        rules = rules
    )
end

function from_dict(::Type{ReportCleanMastGroup}, dict::Dict{String, Any})
    return ReportCleanMastGroup(
        masts = [from_dict(ReportCleanMast, m) for m in dict["masts"]]
    )
end

function from_dict(::Type{ReportCleanOutput}, dict::Dict{String, Any})
    return ReportCleanOutput(
        report_dir = get(dict, "report_dir", "./report-masts/clean"),
        report_filename = get(dict, "report_filename", "report.typ")
    )
end

function from_dict(::Type{ReportCleanConfiguration}, dict::Dict{String, Any})
    return ReportCleanConfiguration(
        raw = from_dict(ReportCleanMastGroup, dict["raw"]),
        clean = from_dict(ReportCleanMastGroup, dict["clean"]),
        output = haskey(dict, "output") ? from_dict(ReportCleanOutput, dict["output"]) : ReportCleanOutput()
    )
end

# to_dict implementations for saving configurations
function to_dict(mast::ReportCleanMast)
    result = Dict{String, Any}(
        "name" => mast.name,
        "input" => to_dict(mast.input)
    )
    if !isnothing(mast.rules)
        result["rules"] = [to_dict(r) for r in mast.rules]
    end
    return result
end

# to_dict for Rule - converts Rule back to TOML-compatible dict
function to_dict(rule::Rule)
    result = Dict{String, Any}(
        "name" => rule.name,
        "sensorType" => rule.sensorType
    )

    # Height filter
    height_dict = Dict{String, Any}()
    if !isnothing(rule.height.min)
        height_dict["min"] = rule.height.min
    end
    if !isnothing(rule.height.max)
        height_dict["max"] = rule.height.max
    end
    if !isempty(height_dict)
        result["height"] = height_dict
    end

    # Criteria
    if rule.criteria isa RangeCriteria
        range_dict = Dict{String, Any}()
        if !isnothing(rule.criteria.min)
            range_dict["min"] = rule.criteria.min
        end
        if !isnothing(rule.criteria.max)
            range_dict["max"] = rule.criteria.max
        end
        result["out_of_range"] = range_dict
    elseif rule.criteria isa LayerDifferenceCriteria
        ld_dict = Dict{String, Any}(
            "lower_layer_height" => rule.criteria.lower_layer_height
        )

        abs_diff = Dict{String, Any}()
        if !isnothing(rule.criteria.abs_diff.min)
            abs_diff["min"] = rule.criteria.abs_diff.min
        end
        if !isnothing(rule.criteria.abs_diff.max)
            abs_diff["max"] = rule.criteria.abs_diff.max
        end
        ld_dict["abs_diff"] = abs_diff

        lower_ws = Dict{String, Any}()
        if !isnothing(rule.criteria.lower_wind_speed.min)
            lower_ws["min"] = rule.criteria.lower_wind_speed.min
        end
        if !isnothing(rule.criteria.lower_wind_speed.max)
            lower_ws["max"] = rule.criteria.lower_wind_speed.max
        end
        ld_dict["lower_wind_speed"] = lower_ws

        result["layer_difference"] = ld_dict
    elseif rule.criteria isa IcingCriteria
        result["icing"] = Dict{String, Any}(
            "time_range" => rule.criteria.time_range,
            "max_change" => rule.criteria.max_change
        )
    elseif rule.criteria isa AvailabilityCriteria
        result["availability"] = Dict{String, Any}(
            "low_threshold" => rule.criteria.low_threshold
        )
    end

    return result
end

function to_dict(group::ReportCleanMastGroup)
    return Dict{String, Any}(
        "masts" => [to_dict(mast) for mast in group.masts]
    )
end

function to_dict(output::ReportCleanOutput)
    return Dict{String, Any}(
        "report_dir" => output.report_dir,
        "report_filename" => output.report_filename
    )
end

function to_dict(config::ReportCleanConfiguration)
    return Dict{String, Any}(
        "raw" => to_dict(config.raw),
        "clean" => to_dict(config.clean),
        "output" => to_dict(config.output)
    )
end

"""
    to_report_clean_config(process_config::ProcessCleanConfiguration, config_dir::String, path_prefix::String) -> ReportCleanConfiguration

Convert ProcessCleanConfiguration to ReportCleanConfiguration.

# Arguments
- `process_config::ProcessCleanConfiguration`: The process-clean configuration to convert
- `config_dir::String`: Base directory for resolving relative rule file paths
- `path_prefix::String`: Prefix to prepend to relative paths (e.g., "../" for report-masts/)

# Returns
- `ReportCleanConfiguration`: The converted report clean configuration

# Description
This function converts a ProcessCleanConfiguration (from process-clean.toml) into a
ReportCleanConfiguration (for report-clean.toml). It:

1. Creates raw masts from process_config.masts[].input with adjusted paths
2. Creates clean masts from process_config.masts[].output with adjusted paths
3. Loads and parses rules for each mast
4. Applies path prefix adjustment for configs saved in subdirectories

# Example
```julia
process_config = from_dict(ProcessCleanConfiguration, load_dict("process-clean.toml"))
report_config = to_report_clean_config(process_config, "/path/to/project", "../")
```
"""
function to_report_clean_config(
    process_config::ProcessCleanConfiguration,
    config_dir::String,
    path_prefix::String
)::ReportCleanConfiguration
    # Create raw masts from process_config.masts[].input with adjusted paths
    raw_masts = [
        ReportCleanMast(
            name = mast.name,
            input = adjust_timeseries_source_paths(mast.input, path_prefix)
        )
        for mast in process_config.masts
    ]

    # Create clean masts from process_config.masts[].output with adjusted paths
    # Convert CSV to Parquet for clean output (which is now in Parquet format)
    # Load and parse rules for each mast
    clean_masts = [
        ReportCleanMast(
            name = mast.name,
            input = adjust_timeseries_source_paths_to_parquet(mast.output, path_prefix),
            rules = load_rules(mast.rules, config_dir)
        )
        for mast in process_config.masts
    ]

    # Create configuration with default output settings
    return ReportCleanConfiguration(
        raw = ReportCleanMastGroup(masts = raw_masts),
        clean = ReportCleanMastGroup(masts = clean_masts),
        output = ReportCleanOutput()  # Uses defaults: "./report-masts/clean", "report.typ"
    )
end

end # module
