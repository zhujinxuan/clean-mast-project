"""
Test utilities for CleanMastProject test suite.

Provides helper functions for creating temporary directories in the project root
to avoid Windows system temp directory cleanup issues.
"""
module TestUtils

using UUIDs

export mktempdir_project

"""
    mktempdir_project(test_name::String; cleanup::Bool=true)

Create a temporary directory in the project root's temp/ folder.

This avoids issues with Windows system temp directory cleanup that can cause
"directory not empty" errors during test runs.

# Arguments
- `test_name::String`: Name of the test (used as prefix for the directory)
- `cleanup::Bool=true`: Whether to clean up the directory after use (default: true)

# Returns
- Path to the created temporary directory

# Example
```julia
using .TestUtils: mktempdir_project

mktempdir_project("parquet_io") do tmpdir
    # Your test code here
    parquet_path = joinpath(tmpdir, "test.parquet")
    # ... test code ...
end
```
"""
function mktempdir_project(test_name::String)
    # Get project root (parent of test directory)
    project_root = normpath(joinpath(@__DIR__, ".."))
    temp_root = joinpath(project_root, "temp")
    
    # Create temp root if it doesn't exist
    if !isdir(temp_root)
        mkpath(temp_root)
    end
    
    # Create unique subdirectory
    uuid = string(uuid4())[1:8]
    temp_dir = joinpath(temp_root, "$(test_name)-$(uuid)")
    mkpath(temp_dir)
    
    return temp_dir
end

"""
    mktempdir_project(fn::Function, test_name::String)

Create a temporary directory and execute the function, optionally cleaning up afterward.
"""
function mktempdir_project(fn::Function, test_name::String; cleanup::Bool=true)
    temp_dir = mktempdir_project(test_name)
    try
        fn(temp_dir)
    finally
        if cleanup && isdir(temp_dir)
            try
                rm(temp_dir; recursive=true, force=true)
            catch e
                @warn "Failed to cleanup temp directory" temp_dir exception=e
            end
        end
    end
end

end # module
