module QuickStart

"""
Create a new project directory and initialize it with example config
"""
function execute(dir::String)
    # Create directory if it doesn't exist
    if !isdir(dir)
        mkpath(dir)
        println("Created directory: $dir")
    end

    # Get example file paths relative to package root
    package_root = dirname(dirname(dirname(@__FILE__)))
    example_project_dir = joinpath(package_root, "example_project")
    
    # Files and directories to copy
    items_to_copy = [
        "parse-sensors.toml",
        "formats"
    ]

    for item in items_to_copy
        source_path = joinpath(example_project_dir, item)
        target_path = joinpath(dir, item)

        if !isfile(target_path) && !isdir(target_path)
            cp(source_path, target_path)
            println("Copied example $item to: $target_path")
        else
            println("$item already exists: $target_path")
        end
    end
end

export execute
end 