# 文件：./src/CleanMastConfig.jl

module CleanMastConfig

using YAML
using ..Types.Utils: from_dict, to_dict
using ..Types.CleanRules
using ..Types.CleanMastConfig
using ..SensorFormats: load_preset_format

"""
Parse project configuration from a directory.
"""
function parse_config(dir::String)::ProjectConfig
    config_path = joinpath(dir, "config.yaml")
    !isfile(config_path) && error("配置文件不存在: $config_path")

    config = YAML.load_file(config_path)
    config_dict = Dict{String, Any}(config)

    # Load preset formats if specified
    if haskey(config_dict, "Mast") && haskey(config_dict["Mast"], "sensor")
        if config_dict["Mast"]["sensor"] isa String
            config_dict["Mast"]["sensor"] = to_dict(load_preset_format(config_dict["Mast"]["sensor"]))
        end
    end

    if haskey(config_dict, "Meso") && haskey(config_dict["Meso"], "sensor")
        if config_dict["Meso"]["sensor"] isa String
            config_dict["Meso"]["sensor"] = to_dict(load_preset_format(config_dict["Meso"]["sensor"]))
        end
    end

    from_dict(ProjectConfig, config_dict)
end

export parse_config

end
