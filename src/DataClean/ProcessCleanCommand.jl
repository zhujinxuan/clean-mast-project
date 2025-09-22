module ProcessCleanCommand

using CSV, YAML, DataFrames, Dates, TOML
using ...Types.ProcessCleanConfig: ProcessCleanConfiguration
using ...Types.CleanRules: Rule, RuleViolation
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, save_timeseries
using ...Types.SensorColumns: SensorColumn
using ...Types.ViolationData: ViolationAnalysisData, ProcessingInfo, ViolationSummary, ViolationColumn, ViolationRule
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict
using ..Rules.Process: apply_rules!

export execute, process_clean_data!

"""
Process clean data by applying cleaning rules to the time series data.
    
Parameters
----------
rules : Vector{Rule}
    Cleaning rules to apply
time_series : TimeSeriesData
    Time series data to be processed

Returns
-------
Tuple{TimeSeriesData, Vector{RuleViolation}}
    Processed time series data with violations set to missing and a vector of rule violations
"""
function process_clean_data!(rules::Vector{Rule}, time_series::TimeSeriesData)::Tuple{TimeSeriesData, Vector{RuleViolation}}
    # Apply all cleaning rules
    violations = apply_rules!(rules, time_series)
    
    # Return the processed time series and violations
    return (time_series, violations)
end

function log_violations(violations::Vector{RuleViolation}, mast_name::String, project_dir::String, time_series::TimeSeriesData)
    # Keep existing console logging (unchanged)
    log_violations_to_console(violations, mast_name)

    # NEW: Save to YAML file
    save_violations_to_yaml(violations, mast_name, project_dir, time_series)
end

function log_violations_to_console(violations::Vector{RuleViolation}, mast_name::String)
    if isempty(violations)
        println("No violations found for mast: $mast_name")
        return
    end

    println("Found $(length(violations)) violations for mast: $mast_name")

    # Convert vector of structs to a DataFrame-compatible format
    violation_rows = [(column=v.column, rule_name=v.rule.name, timestamp=v.timestamp) for v in violations]
    df = DataFrame(violation_rows)

    # Group by column, then by rule name, and count violations
    if !isempty(df)
        summary = combine(groupby(df, [:column, :rule_name]), nrow => :count)

        # Print summary for each column
        for group in groupby(summary, :column)
            col_name = first(group.column)
            total_violations = sum(group.count)
            println("  - Column '$(col_name)': $total_violations total violations")

            for row in eachrow(group)
                println("    - Rule '$(row.rule_name)': $(row.count) violations")
            end
        end
    end
end

function save_violations_to_yaml(violations::Vector{RuleViolation}, mast_name::String, project_dir::String, time_series::TimeSeriesData)
    # Create process-stats directory if it doesn't exist
    process_stats_dir = joinpath(project_dir, "process-stats")
    mkpath(process_stats_dir)

    # Get time range from time series data
    timestamps = time_series.df.timestamp
    start_time = minimum(timestamps)
    end_time = maximum(timestamps)
    total_timestamps = length(timestamps)

    # Create YAML structure
    yaml_data = create_violation_yaml_structure(violations, mast_name, start_time, end_time, total_timestamps)

    # Save to YAML file
    stats_filename = "process-clean-$(mast_name).yaml"
    stats_filepath = joinpath(process_stats_dir, stats_filename)

    open(stats_filepath, "w") do io
        YAML.write(io, yaml_data)
    end

    println("- Saved violation summary to $(stats_filepath)")
end

function create_violation_yaml_structure(violations::Vector{RuleViolation}, mast_name::String,
                                       start_time::DateTime, end_time::DateTime, total_timestamps::Int)
    # Create typed structures first, then convert to dict for YAML serialization

    # Create processing info
    processing_info = ProcessingInfo(
        mast_name = mast_name,
        start_time = string(start_time),
        end_time = string(end_time),
        total_timestamps = total_timestamps
    )

    # Group violations by column and rule
    violation_rows = [(column=v.column, rule_name=v.rule.name, timestamp=v.timestamp) for v in violations]

    if isempty(violation_rows)
        # Handle case with no violations - create empty typed structure
        violation_analysis = ViolationAnalysisData(
            processing_info = processing_info,
            violation_summary = ViolationSummary(
                total_violations = 0,
                violation_percentage = 0.0
            ),
            violations_by_column = ViolationColumn[]
        )
        return to_dict(violation_analysis)
    end

    df = DataFrame(violation_rows)

    # Group by column and create typed ViolationColumn structures
    violations_by_column = ViolationColumn[]

    for column_group in groupby(df, :column)
        column_name = string(first(column_group.column))
        column_rules = ViolationRule[]

        # Group by rule within this column
        for rule_group in groupby(column_group, :rule_name)
            rule_name = first(rule_group.rule_name)
            timestamps = [string(ts) for ts in rule_group.timestamp]

            push!(column_rules, ViolationRule(
                rule_name = rule_name,
                count = nrow(rule_group),
                timestamps = timestamps
            ))
        end

        push!(violations_by_column, ViolationColumn(
            column = column_name,
            total_violations = nrow(column_group),
            rules = column_rules
        ))
    end

    # Calculate overall statistics
    total_violations = length(violations)
    violation_percentage = round((total_violations / total_timestamps) * 100, digits=2)

    # Create complete typed structure
    violation_analysis = ViolationAnalysisData(
        processing_info = processing_info,
        violation_summary = ViolationSummary(
            total_violations = total_violations,
            violation_percentage = violation_percentage
        ),
        violations_by_column = violations_by_column
    )

    # Convert to dictionary for YAML serialization
    return to_dict(violation_analysis)
end

function execute(config_path::String)
    if !isfile(config_path)
        error("Process clean config file not found: $config_path")
    end

    project_dir = dirname(config_path)
    config_dict = load_dict(config_path)
    config = from_dict(ProcessCleanConfiguration, config_dict)

    for mast_config in config.masts
        name = mast_config.name
        
        time_series = load_timeseries(mast_config.input, project_dir)

        rules_config = mast_config.rules
        rules_dict = isa(rules_config, String) ? load_dict(joinpath(project_dir, rules_config)) : rules_config
        rules = [from_dict(Rule, r) for r in rules_dict["rules"]]

        println("Processing clean data for mast: $name...")
        result, violations = process_clean_data!(rules, time_series)

        log_violations(violations, name, project_dir, time_series)

        save_timeseries(mast_config.output, project_dir, result)
        
        println("Clean data processing completed for mast: $name")
        println("- Saved processed data to $(mast_config.output.data)")
        println("- Saved updated sensors to $(mast_config.output.sensors)")
    end
end

end 