#src/CleanMastUtils.jl
"""
General utility functions for CleanMastProject, including configuration loaders.
"""
module CleanMastUtils

using YAML, JSON, TOML

export load_dict

"""
    load_dict(filepath::String)

Load a file and parse it into a dictionary.
Supports JSON, YAML, and TOML formats based on file extension.

# Arguments
- `filepath::String`: Absolute or relative path to the configuration file.

# Returns
- `Dict{String, Any}`: The parsed configuration as a dictionary.

# Throws
- `ErrorException`: If the file does not exist.
- `ArgumentError`: If the file format is not supported (.json, .yaml, .yml, .toml).
"""
function load_dict(filepath::String)::Dict{String, Any}
    !isfile(filepath) && error("File not found: $filepath")

    # Get file extension to determine format
    ext = lowercase(splitext(filepath)[2])

    if ext == ".json"
        return JSON.parsefile(filepath)
    elseif ext in [".yaml", ".yml"]
        return YAML.load_file(filepath; dicttype=Dict{String, Any})
    elseif ext == ".toml"
        return TOML.parsefile(filepath)
    else
        throw(ArgumentError("Unsupported file format: $ext. Use .json, .yaml, or .toml"))
    end
end

end # end module 