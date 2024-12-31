module CleanFiles

using ...Types.CleanMastConfig
using ...CleanMastConfig
using Dates

"""
Archive non-essential files in project directory
"""
function execute(dir::String)
    # Check if directory exists
    !isdir(dir) && error("Directory does not exist: $dir")
    
    # Parse config to get data file paths
    config = parse_config(dir)
    essential_paths = [
        joinpath(dir, "config.yaml"),
        joinpath(dir, config.mast.data_path),
        joinpath(dir, config.meso.data_path)
    ]
    
    # Check essential files exist
    for path in essential_paths
        !isfile(path) && error("Essential file not found: $path")
    end
    
    # Create archive directory with timestamp
    timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
    archive_dir = joinpath(dir, "archived", timestamp)
    
    # Get all files except essential files
    files_to_archive = filter(
        f -> isfile(f) && !(f in essential_paths),
        [joinpath(dir, f) for f in readdir(dir)]
    )
    
    if !isempty(files_to_archive)
        # Create archive directory
        mkpath(archive_dir)
        println("Created archive directory: $archive_dir")
        
        # Move files to archive
        for file in files_to_archive
            target = joinpath(archive_dir, basename(file))
            mv(file, target)
            println("Moved to archive: $(basename(file))")
        end
        
        println("Archived $(length(files_to_archive)) files")
    else
        println("No files to archive")
    end
end

export execute
end 