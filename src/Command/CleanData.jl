module CleanData

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...MastTimeSeries
using ...CleanMastRules: Process
using Dates

export execute

function execute(dir::String)
    config = parse_config(dir)
    time_series = read_mast_data(config, dir)
    
    violations = Process.apply_rules!(config.mast.rules, time_series)
    
    original_filename = config.mast.data_path
    cleaned_filename = "clean_data.$(original_filename).csv"
    CSV.write(joinpath(dir, cleaned_filename), time_series.df)
    
    violations_yaml = Dict(
        "violations" => [Dict(
            "timestamp" => Dates.format(v.timestamp, "yyyy-mm-dd HH:MM:SS"),
            "column" => String(v.column),
            "rule_name" => v.rule.name
        ) for v in violations]
    )
    open(joinpath(dir, "violations.yaml"), "w") do io
        YAML.write(io, violations_yaml)
    end
    
    println("Data cleaning completed:")
    println("- Found $(length(violations)) violations")
    println("- Saved cleaned data to $(cleaned_filename)")
    println("- Saved violations to violations.csv and violations.yaml")
end

end 