# 文件：./src/CleanMastConfig.jl

module CleanMastConfig

using YAML
using ..Types.Utils: from_dict
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
    if haskey(config_dict, "Mast") && haskey(config_dict["Mast"], "sensor") && 
       haskey(config_dict["Mast"]["sensor"], "format") && config_dict["Mast"]["sensor"]["format"] isa String
        config_dict["Mast"]["sensor"] = merge(
            load_preset_format(config_dict["Mast"]["sensor"]["format"]),
            Dict{String, Any}(config_dict["Mast"]["sensor"])
        )
    end

    if haskey(config_dict, "Meso") && haskey(config_dict["Meso"], "sensor") && 
       haskey(config_dict["Meso"]["sensor"], "format") && config_dict["Meso"]["sensor"]["format"] isa String
        config_dict["Meso"]["sensor"] = merge(
            load_preset_format(config_dict["Meso"]["sensor"]["format"]),
            Dict{String, Any}(config_dict["Meso"]["sensor"])
        )
    end

    from_dict(ProjectConfig, config_dict)
end

export parse_config

end
