module SensorFormats

using YAML
using ..Types.CleanMastConfig: SensorConfig, MappingRule
using ..Types.Utils: from_dict

const FORMATS_DIR = joinpath(dirname(@__FILE__), "..", "formats", "sensor")

"""
Load a preset format configuration from the formats directory.
"""
function load_preset_format(format_name::String)::SensorConfig
    format_path = joinpath(FORMATS_DIR, "$(format_name).yaml")
    !isfile(format_path) && error("Format file not found: $format_path")

    config = YAML.load_file(format_path)
    format = from_dict(SensorConfig, Dict{String, Any}(config["sensor"]))
    
    SensorConfig(format)
end

"""
Get a list of available preset formats.
"""
function list_preset_formats()::Vector{String}
    isdir(FORMATS_DIR) || return String[]
    
    [replace(f, r".yaml$" => "") for f in readdir(FORMATS_DIR) if endswith(f, ".yaml")]
end

export load_preset_format, list_preset_formats

end 