# 文件：./src/CleanMastConfig.jl

module CleanMastConfig

using YAML
using DataFrames
using ..Types.CleanRules
using ..Types.CleanMastConfig

function parse_config(dir::String)::ProjectConfig
  config_path = joinpath(dir, "config.yaml")
  !isfile(config_path) && error("配置文件不存在: $config_path")

  config = YAML.load_file(config_path)

  try
    sensor_mappings = parse_mapping_rules(config["Mast"]["sensor"]["mappings"])
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
       SensorMetadata

end
