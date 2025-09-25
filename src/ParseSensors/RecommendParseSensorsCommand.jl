module RecommendParseSensorsCommand

using TOML

function execute(dir::String)
    # Ensure we're in the project directory
    if !isdir(dir)
        error("Project directory does not exist: $dir")
    end

    # Look for mast files in masts/ directory
    masts_dir = joinpath(dir, "masts")
    mesos_dir = joinpath(dir, "mesos")

    mast_files = String[]
    meso_files = String[]

    # Scan for mast files
    if isdir(masts_dir)
        all_files = readdir(masts_dir; join=true)
        for file in all_files
            if isfile(file) && (endswith(file, ".csv") || endswith(file, ".txt"))
                push!(mast_files, file)
            end
        end
    end

    # Scan for meso files
    if isdir(mesos_dir)
        all_files = readdir(mesos_dir; join=true)
        for file in all_files
            if isfile(file) && (endswith(file, ".csv") || endswith(file, ".txt"))
                push!(meso_files, file)
            end
        end
    end

    # Generate configuration
    config = Dict{String, Any}()

    # Generate mast configurations
    if !isempty(mast_files)
        masts = []
        for mast_file in mast_files
            # Get relative path from project directory
            rel_path = relpath(mast_file, dir)

            # Extract base name without extension for naming
            base_name = splitext(basename(mast_file))[1]

            # Create mast configuration
            mast_config = Dict{String, Any}(
                "input" => rel_path,
                "name" => base_name,
                "sensor" => "formats/sensor/nrg.toml"
            )

            push!(masts, mast_config)
        end
        config["masts"] = masts
    end

    # Generate meso configurations
    if !isempty(meso_files)
        mesos = []
        for meso_file in meso_files
            # Get relative path from project directory
            rel_path = relpath(meso_file, dir)

            # Extract base name without extension for naming
            base_name = splitext(basename(meso_file))[1]

            # Create meso configuration
            meso_config = Dict{String, Any}(
                "input" => rel_path,
                "name" => base_name,
                "sensor" => "formats/sensor/freemeso-meso.toml"
            )

            push!(mesos, meso_config)
        end
        config["mesos"] = mesos
    end

    # Write the configuration file
    output_path = joinpath(dir, "parse-sensors.toml")

    open(output_path, "w") do io
        # Write header comment
        println(io, "# Parse Sensors Configuration")
        println(io, "# This file defines which data files to process and their sensor formats")
        println(io, "")

        TOML.print(io, config)
    end

    # Print summary
    println("Generated parse-sensors.toml at: $output_path")
    if !isempty(mast_files)
        println("Found $(length(mast_files)) mast file(s):")
        for file in mast_files
            println("  - $(relpath(file, dir))")
        end
    else
        println("No mast files found in masts/ directory")
    end

    if !isempty(meso_files)
        println("Found $(length(meso_files)) meso file(s):")
        for file in meso_files
            println("  - $(relpath(file, dir))")
        end
    else
        println("No meso files found in mesos/ directory")
    end

    if isempty(mast_files) && isempty(meso_files)
        println("Warning: No data files found. Please copy your data files to:")
        println("  - masts/*.{csv,txt} for mast data")
        println("  - mesos/*.{csv,txt} for meso data")
    end
end

export execute

end