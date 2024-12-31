# 文件：./src/CleanMastConfig.jl

module CleanMastConfig

using YAML
using ..Types.Utils: from_dict
using ..Types.CleanRules
using ..Types.CleanMastConfig

function parse_config(dir::String)::ProjectConfig
  config_path = joinpath(dir, "config.yaml")
  !isfile(config_path) && error("配置文件不存在: $config_path")

  config = YAML.load_file(config_path)
  from_dict(ProjectConfig, Dict{String, Any}(config))

end

export parse_config

end
