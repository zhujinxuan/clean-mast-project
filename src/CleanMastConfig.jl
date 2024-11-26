# 文件：./src/CleanMastConfig.jl

module CleanMastConfig

using YAML

# Type for storing mappings 
struct SensorMappings
    sensor_types::Dict{String, String}
    stat_types::Dict{String, String}
    units::Dict{String, String}
end

# Update SensorConfig to include mappings
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
end

struct ProjectConfig
    mast::MastConfig
end

# Metadata structure for parsed sensor information
struct SensorMetadata
    columnName::String
    sensorType::String  # Using string literal instead of enum
    sensorDirection::String
    height::Float64
    statType::String    # Using string literal instead of enum
    unit::String
end

struct MastTimeSeries
    df::DataFrame
    sensors::Vector{SensorMetadata}
end

# 解析配置文件的函数
function parse_config(dir::String)::ProjectConfig
    config_path = joinpath(dir, "config.yaml")
    if !isfile(config_path)
        error("配置文件不存在: $config_path")
    end

    # 读取并解析 YAML 配置文件
    config = YAML.load_file(config_path)

    try
        # Parse mappings
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

        mast_config = MastConfig(
            config["Mast"]["data_path"],
            config["Mast"]["skip_to"],
            sensor_config
        )
        
        return ProjectConfig(mast_config)
    catch e
        error("配置文件解析或验证失败: $(e.message)")
    end
end

# Export needed types and functions
export parse_config, ProjectConfig, MastConfig, SensorConfig, SensorMappings, 
       SensorMetadata, MastTimeSeries

end # module CleanMastConfig
