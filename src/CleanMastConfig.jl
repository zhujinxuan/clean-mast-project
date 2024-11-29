# 文件：./src/CleanMastConfig.jl

module CleanMastConfig

using YAML
using DataFrames
using ..CleanMastRules.Rules

struct SensorMappings
    sensor_types::Dict{String, String}
    stat_types::Dict{String, String}
    units::Dict{String, String}
end

struct SensorConfig
    column_format::String
    timestamp_column::String
    timestamp_format::String
    mappings::SensorMappings
end

struct MastConfig
    data_path::String
    skip_to::Int
    sensor::SensorConfig
    rules::Vector{Rule}  # Using Rules.Rule
end

struct ProjectConfig
    mast::MastConfig
end

struct SensorMetadata
    columnName::String
    sensorType::String
    sensorDirection::String
    height::Float64
    statType::String
    unit::String
end

struct MastTimeSeries
    df::DataFrame
    sensors::Vector{SensorMetadata}
end

function parse_config(dir::String)::ProjectConfig
    config_path = joinpath(dir, "config.yaml")
    !isfile(config_path) && error("配置文件不存在: $config_path")

    config = YAML.load_file(config_path)

    try
        sensor_mappings = SensorMappings(
            Dict{String, String}(config["Mast"]["sensor"]["mappings"]["sensor_types"]),
            Dict{String, String}(config["Mast"]["sensor"]["mappings"]["stat_types"]),
            Dict{String, String}(config["Mast"]["sensor"]["mappings"]["units"])
        )

        sensor_config = SensorConfig(
            config["Mast"]["sensor"]["column_format"],
            config["Mast"]["sensor"]["timestamp_column"],
            config["Mast"]["sensor"]["timestamp_format"],
            sensor_mappings
        )

        rules = Vector{Rule}()
        if haskey(config["Mast"], "rules")
            rules = [parse_rule(rule) for rule in config["Mast"]["rules"]]
        end

        mast_config = MastConfig(
            config["Mast"]["data_path"],
            config["Mast"]["skip_to"],
            sensor_config,
            rules
        )
        
        return ProjectConfig(mast_config)
    catch e
        error("配置文件解析或验证失败: $(e.message)")
    end
end

export parse_config, ProjectConfig, MastConfig, SensorConfig, SensorMappings, 
       SensorMetadata, MastTimeSeries

end
