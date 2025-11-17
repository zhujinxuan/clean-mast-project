module ReportCleanConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource
using ..CleanRules: Rule, RangeCriteria, LayerDifferenceCriteria, IcingCriteria, AvailabilityCriteria
using Parameters

export ReportCleanMast, ReportCleanMastGroup, ReportCleanOutput, ReportCleanConfiguration

@with_kw struct ReportCleanMast
    name::String
    input::TimeSeriesSource
    rules::Union{Vector{Rule}, Nothing} = nothing
end

@with_kw struct ReportCleanMastGroup
    masts::Vector{ReportCleanMast}
end

@with_kw struct ReportCleanOutput
    report_dir::String = "./report-masts/clean"
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

end # module
