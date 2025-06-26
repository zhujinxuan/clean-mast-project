# 文件：./src/CleanMastConfig.jl

module CleanMastConfig

using YAML
using ..Types.Utils: from_dict, to_dict
using ..Types.CleanRules
using ..Types.CleanMastConfig

"""
Parse project configuration from a directory.
"""
function parse_config(dir::String)::ProjectConfig
    config_path = joinpath(dir, "config.yaml")
    !isfile(config_path) && error("配置文件不存在: $config_path")

    config = YAML.load_file(config_path)
    config_dict = Dict{String, Any}(config)

    from_dict(ProjectConfig, config_dict)
end

export parse_config

end
