module ProcessCleanCommand

using CSV, YAML, DataFrames, Dates, TOML
using ...Types.ProcessCleanConfig: ProcessCleanConfiguration
using ...Types.CleanRules: Rule, RuleViolation
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, save_timeseries
using ...Types.SensorColumns: SensorColumn
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

function log_violations(violations::Vector{RuleViolation}, mast_name::String)
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
        
        log_violations(violations, name)

        save_timeseries(mast_config.output, project_dir, result)
        
        println("Clean data processing completed for mast: $name")
        println("- Saved processed data to $(mast_config.output.data)")
        println("- Saved updated sensors to $(mast_config.output.sensors)")
    end
end

end 