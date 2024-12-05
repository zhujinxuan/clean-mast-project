module CleanData

using CSV, YAML, DataFrames
using ...Types.CleanMastConfig
using ...MastTimeSeries
using ...CleanMastRules: Process

export execute

function execute(dir::String)
    try
        config = CleanMastConfig.parse_config(dir)
        time_series = read_mast_data(config, dir)
        
        violations = Process.apply_rules!(config.mast.rules, time_series)
        
        original_filename = config.mast.data_path
        cleaned_filename = "clean_data.$(original_filename)"
        CSV.write(joinpath(dir, cleaned_filename), time_series.df)
        
        violations_df = DataFrame(
            timestamp = [v.timestamp for v in violations],
            column = [String(v.column) for v in violations],
            rule_name = [v.rule_name for v in violations]
        )
        CSV.write(joinpath(dir, "violations.csv"), violations_df)
        
        violations_yaml = Dict(
            "violations" => [Dict(
                "timestamp" => string(v.timestamp),
                "column" => String(v.column),
                "rule_name" => v.rule_name
            ) for v in violations]
        )
        open(joinpath(dir, "violations.yaml"), "w") do io
            YAML.write(io, violations_yaml)
        end
        
        println("Data cleaning completed:")
        println("- Found $(length(violations)) violations")
        println("- Saved cleaned data to $(cleaned_filename)")
        println("- Saved violations to violations.csv and violations.yaml")
        
    catch e
        error("Data cleaning failed: $(e.message)")
    end
end

end 