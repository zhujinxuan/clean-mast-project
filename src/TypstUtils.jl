"""
    TypstUtils.jl

Utility functions for checking Typst availability and compiling Typst reports.
"""
module TypstUtils

export is_typst_available, compile_typst_report, compile_typst_files, typst_try_compile, typst_try_compile_all

"""
    is_typst_available() -> Bool

Check if Typst is available in the system PATH.
"""
function is_typst_available()::Bool
    try
        # Try to run typst --version to check if it's available
        result = read(`typst --version`, String)
        return !isempty(strip(result))
    catch
        return false
    end
end

"""
    compile_typst_report(typst_file::String; output_format::String="pdf") -> Bool

Compile a single Typst file to the specified format.

# Arguments
- `typst_file::String`: Path to the .typ file to compile
- `output_format::String`: Output format ("pdf" or "png"), defaults to "pdf"

# Returns
- `Bool`: true if compilation succeeded, false otherwise
"""
function compile_typst_report(typst_file::String; output_format::String="pdf")::Bool
    if !isfile(typst_file)
        @warn "Typst file not found: $typst_file"
        return false
    end

    if !is_typst_available()
        @info "Typst not found in PATH, skipping compilation of $typst_file"
        return false
    end

    try
        # Get the directory and base name
        file_dir = dirname(typst_file)
        base_name = splitext(basename(typst_file))[1]
        output_file = joinpath(file_dir, "$(base_name).$(output_format)")

        @info "Compiling Typst report: $typst_file → $output_file"

        # Run typst compile command
        if output_format == "pdf"
            run(`typst compile $typst_file $output_file`)
        elseif output_format == "png"
            run(`typst compile $typst_file $output_file --format png`)
        else
            @warn "Unsupported output format: $output_format"
            return false
        end

        @info "✅ Successfully compiled: $output_file"
        return true

    catch e
        @error "Failed to compile Typst report $typst_file: $e"
        return false
    end
end

"""
    compile_typst_files(directory::String; output_format::String="pdf", recursive::Bool=true) -> Int

Compile all .typ files in a directory.

# Arguments
- `directory::String`: Directory to search for .typ files
- `output_format::String`: Output format ("pdf" or "png"), defaults to "pdf"
- `recursive::Bool`: Whether to search subdirectories, defaults to true

# Returns
- `Int`: Number of successfully compiled files
"""
function compile_typst_files(directory::String; output_format::String="pdf", recursive::Bool=true)::Int
    if !isdir(directory)
        @warn "Directory not found: $directory"
        return 0
    end

    if !is_typst_available()
        @info "Typst not found in PATH, skipping compilation"
        return 0
    end

    # Find all .typ files
    typ_files = String[]
    if recursive
        for (root, dirs, files) in walkdir(directory)
            for file in files
                if endswith(file, ".typ")
                    push!(typ_files, joinpath(root, file))
                end
            end
        end
    else
        for file in readdir(directory)
            if endswith(file, ".typ")
                push!(typ_files, joinpath(directory, file))
            end
        end
    end

    if isempty(typ_files)
        @info "No .typ files found in $directory"
        return 0
    end

    @info "Found $(length(typ_files)) Typst files to compile in $directory"

    success_count = 0
    for typ_file in typ_files
        if compile_typst_report(typ_file; output_format=output_format)
            success_count += 1
        end
    end

    @info "📋 Typst compilation summary: $success_count/$(length(typ_files)) files compiled successfully"
    return success_count
end

"""
    compile_main_report(report_dir::String, main_report_name::String="report.typ"; output_format::String="pdf") -> Bool

Compile the main report file in a report directory.

# Arguments
- `report_dir::String`: Directory containing the main report
- `main_report_name::String`: Name of the main report file, defaults to "report.typ"
- `output_format::String`: Output format ("pdf" or "png"), defaults to "pdf"

# Returns
- `Bool`: true if compilation succeeded, false otherwise
"""
function compile_main_report(report_dir::String, main_report_name::String="report.typ"; output_format::String="pdf")::Bool
    main_report_path = joinpath(report_dir, main_report_name)
    return compile_typst_report(main_report_path; output_format=output_format)
end

"""
    typst_try_compile(report_dir::String, report_filename::String="report.typ"; output_format::String="pdf") -> Nothing

Generic function that tries to compile a Typst report with user-friendly messaging.
Checks if Typst is available, attempts compilation, and provides appropriate feedback.

# Arguments
- `report_dir::String`: Directory containing the Typst file
- `report_filename::String`: Name of the Typst file, defaults to "report.typ"
- `output_format::String`: Output format ("pdf" or "png"), defaults to "pdf"

# Examples
```julia
# Simple usage - compile report.typ in current directory
typst_try_compile("./reports")

# Custom filename
typst_try_compile("./reports", "analysis.typ")

# PNG output
typst_try_compile("./reports", "chart.typ"; output_format="png")
```
"""
function typst_try_compile(report_dir::String, report_filename::String="report.typ"; output_format::String="pdf")::Nothing
    if is_typst_available()
        println("📄 Compiling Typst report to $(uppercase(output_format))...")
        if compile_main_report(report_dir, report_filename; output_format=output_format)
            println("✅ Typst compilation successful!")
        else
            println("⚠️  Typst compilation failed, but $report_filename file is available")
            println("   Use Typst manually: typst compile $report_filename")
        end
    else
        println("ℹ️  Typst not found in PATH, skipping $(uppercase(output_format)) compilation")
        println("   Use Typst manually: typst compile $report_filename")
    end
end

"""
    typst_try_compile_all(directory::String; output_format::String="pdf", recursive::Bool=true) -> Nothing

Generic function that tries to compile all Typst files in a directory with user-friendly messaging.
Checks if Typst is available, attempts batch compilation, and provides appropriate feedback.

# Arguments
- `directory::String`: Directory to search for .typ files
- `output_format::String`: Output format ("pdf" or "png"), defaults to "pdf"
- `recursive::Bool`: Whether to search subdirectories, defaults to true

# Examples
```julia
# Compile all .typ files in reports directory
typst_try_compile_all("./reports")

# Non-recursive compilation
typst_try_compile_all("./reports"; recursive=false)

# PNG output
typst_try_compile_all("./reports"; output_format="png")
```
"""
function typst_try_compile_all(directory::String; output_format::String="pdf", recursive::Bool=true)::Nothing
    if is_typst_available()
        println("📄 Compiling Typst reports to $(uppercase(output_format))...")
        compiled_count = compile_typst_files(directory; output_format=output_format, recursive=recursive)
        if compiled_count > 0
            println("✅ Successfully compiled $compiled_count Typst report(s)!")
        else
            println("⚠️  No Typst files found or compilation failed")
        end
    else
        println("ℹ️  Typst not found in PATH, skipping $(uppercase(output_format)) compilation")
    end
end

end # module