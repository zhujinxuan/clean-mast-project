module AnalyzeENConfiguration

using DataFrames
using YAML
import ..Utils: from_dict, to_dict

"""
Wind speed analysis result for a single mast at EN standard
"""
struct ENMastWindSpeedResult
    Label :: String
    X :: Float64
    Y :: Float64
    H :: Int64
    GeoHash :: String
    Vmean::Float64                    # Mean wind speed
    VmeanByDirection::DataFrame       # Direction, Vmean, Frequency
    FrequencyByDirectionAndSpeed::DataFrame  # Direction x Speed frequency matrix
end

"""
Input configuration for a mast's data sources
"""
struct MastInput
    data_path::String    # Path to data file
    sensor_path::String  # Path to sensor configuration
end

"""
Configuration for a single mast in the analyze-en.yaml
"""
struct ENMastConfig
    name::String
    x::Float64
    y::Float64
    H::Int64        # Hub height or measurement channel height
    GeoHash::String
    input::MastInput
end

"""
Root configuration for EN analysis
"""
struct ENAnalyzeConfig
    masts::Vector{ENMastConfig}
end

# Conversion functions for MastInput
function from_dict(::Type{MastInput}, dict::Dict{String, Any})::MastInput
    MastInput(
        dict["data_path"],
        dict["sensor_path"]
    )
end

function to_dict(input::MastInput)::Dict{String, Any}
    Dict{String, Any}(
        "data_path" => input.data_path,
        "sensor_path" => input.sensor_path
    )
end

# Conversion functions for ENMastConfig
function from_dict(::Type{ENMastConfig}, dict::Dict{String, Any})::ENMastConfig
    ENMastConfig(
        dict["name"],
        convert(Float64, dict["x"]),
        convert(Float64, dict["y"]),
        convert(Int64, dict["H"]),
        get(dict, "GeoHash", "wmnrtewnzz"),  # Default GeoHash
        from_dict(MastInput, Dict{String, Any}(dict["input"]))
    )
end

function to_dict(config::ENMastConfig)::Dict{String, Any}
    Dict{String, Any}(
        "name" => config.name,
        "x" => config.x,
        "y" => config.y,
        "H" => config.H,
        "GeoHash" => config.GeoHash,
        "input" => to_dict(config.input)
    )
end

# Conversion functions for ENAnalyzeConfig
function from_dict(::Type{ENAnalyzeConfig}, dict::Dict{String, Any})::ENAnalyzeConfig
    masts = [from_dict(ENMastConfig, Dict{String, Any}(m)) for m in dict["masts"]]
    ENAnalyzeConfig(masts)
end

function to_dict(config::ENAnalyzeConfig)::Dict{String, Any}
    Dict{String, Any}(
        "masts" => [to_dict(m) for m in config.masts]
    )
end

"""
    load_en_config(config_path::String) -> ENAnalyzeConfig

Load EN analysis configuration from a YAML file.
"""
function load_en_config(config_path::String)::ENAnalyzeConfig
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end
    
    yaml_dict = Dict{String, Any}(YAML.load_file(config_path))
    return from_dict(ENAnalyzeConfig, yaml_dict)
end

# Export all types and functions
export ENMastWindSpeedResult, MastInput, ENMastConfig, ENAnalyzeConfig
export from_dict, to_dict, load_en_config

end # module 