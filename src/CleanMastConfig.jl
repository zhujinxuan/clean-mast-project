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

  # Parse MastConfig as before
  mast_config = parse_mast_config(config["Mast"])
  
  # Parse new MesoConfig
  meso_config = parse_meso_config(config["Meso"])
  
  # Parse new AnalysisConfig
  analysis_config = parse_analysis_config(config["Analysis"])
  
  return ProjectConfig(mast_config, meso_config, analysis_config)
end

# Helper function to parse mast config (existing code moved here)
function parse_mast_config(config::Dict{String, Any})::MastConfig
  sensor_config = from_dict(SensorConfig, Dict{String, Any}(config["sensor"]))

  rules = Vector{Rule}()
  if haskey(config, "rules")
    rules = [parse_rule(rule) for rule in config["rules"]]
  end

  MastConfig(
                             config["data_path"],
                             config["skip_to"],
                             get(config, "delim", nothing),
                             sensor_config,
                             rules
                            )
end

# New helper functions for parsing meso and analysis configs
function parse_meso_config(config::Dict)::MesoConfig
  sensor_mappings = parse_mapping_rules(config["sensor"]["mappings"])
  sensor_config = SensorConfig(
                               config["sensor"]["column_format"],
                               config["sensor"]["timestamp_column"],
                               config["sensor"]["timestamp_format"],
                               sensor_mappings
                                )

  MesoConfig(
                             config["data_path"],
                             get(config, "delim", nothing),
                             Vector{String}(config["skip_to"]),
                             Vector{String}(config["timestamp_column"]),
                             config["timestamp_format"],
                             sensor_config
                            )
end

function parse_analysis_config(config::Dict)::AnalysisConfig
  time_range = TimeRange(
                             get(config["time_range"], "min", nothing),
                             get(config["time_range"], "max", nothing)
                            )
  
  AnalysisConfig(time_range)
end

export parse_config

end
