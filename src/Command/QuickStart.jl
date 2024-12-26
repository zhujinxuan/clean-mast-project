module QuickStart

using ...Types.CleanMastConfig

"""
Create a new project directory and initialize it with example config
"""
function execute(dir::String)
    # Create directory if it doesn't exist
    if !isdir(dir)
        mkpath(dir)
        println("Created directory: $dir")
    end

    # Get example config path relative to package root
    package_root = dirname(dirname(dirname(@__FILE__)))
    example_config = joinpath(package_root, "example_project", "config.yaml")
    
    # Copy config file
    target_config = joinpath(dir, "config.yaml")
    if !isfile(target_config)
        cp(example_config, target_config)
        println("Copied example config to: $target_config")
    else
        println("Config file already exists: $target_config")
    end
end

export execute
end 