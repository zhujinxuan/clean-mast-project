module RecommendProcessCleanCommand

using TOML
using Dates
using DataFrames
using CSV
using ...ParseSensors.CommandParseSensors: load_and_normalize_config

function execute(dir::String)
    config_path = joinpath(dir, "parse-sensors.toml")
    
    normalized_config = load_and_normalize_config(config_path)
    
    masts = map(normalized_config.masts) do mast_file_config
        mast_name = mast_file_config.name
        
        input_data = mast_file_config.output.data
        input_sensors = mast_file_config.output.sensors

        output_data = joinpath("./clean", "$(mast_name).csv")
        output_sensors = joinpath("./clean", "$(mast_name).sensors.yaml")

        Dict(
            "name" => mast_name,
            "input" => Dict("data" => input_data, "sensors" => input_sensors),
            "output" => Dict("data" => output_data, "sensors" => output_sensors),
            "rules" => "formats/clean/nrg-strict.toml"
        )
    end

    output_config = Dict("masts" => masts)
    output_path = joinpath(dir, "process-clean.toml")

    open(output_path, "w") do io
        TOML.print(io, output_config)
    end

    println("Generated process-clean.toml at: $output_path")
end

export execute

end 