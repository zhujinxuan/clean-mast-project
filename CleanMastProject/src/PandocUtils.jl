"""
    PandocUtils.jl

Utility functions for checking Pandoc availability and converting Typst reports to DOCX.
"""
module PandocUtils

export is_pandoc_available, convert_typ_to_docx, convert_typ_files, pandoc_try_convert, pandoc_try_convert_all

"""
    is_pandoc_available() -> Bool

Check if Pandoc is available in the system PATH.
"""
function is_pandoc_available()::Bool
    try
        result = read(`pandoc --version`, String)
        return !isempty(strip(result))
    catch
        return false
    end
end

"""
    convert_typ_to_docx(typst_file::String) -> Bool

Convert a single Typst file to DOCX format.

# Arguments
- `typst_file::String`: Path to the .typ file to convert

# Returns
- `Bool`: true if conversion succeeded, false otherwise
"""
function convert_typ_to_docx(typst_file::String)::Bool
    if !isfile(typst_file)
        @warn "Typst file not found: $typst_file"
        return false
    end

    if !is_pandoc_available()
        @info "Pandoc not found in PATH, skipping conversion of $typst_file"
        return false
    end

    try
        file_dir = dirname(typst_file)
        typ_filename = basename(typst_file)
        base_name = splitext(typ_filename)[1]
        docx_filename = "$(base_name).docx"
        output_file = joinpath(file_dir, docx_filename)

        @info "Converting Typst to DOCX: $typst_file → $output_file"

        # Run pandoc from the directory containing the .typ file
        # This allows pandoc to resolve relative paths to images/resources
        run(Cmd(`pandoc $typ_filename -o $docx_filename -f typst -t docx`; dir=file_dir))

        @info "✅ Successfully converted: $output_file"
        return true

    catch e
        @error "Failed to convert Typst file $typst_file: $e"
        return false
    end
end

"""
    convert_typ_files(directory::String; recursive::Bool=true) -> Int

Convert all .typ files in a directory to DOCX format.

# Arguments
- `directory::String`: Directory to search for .typ files
- `recursive::Bool`: Whether to search subdirectories, defaults to true

# Returns
- `Int`: Number of successfully converted files
"""
function convert_typ_files(directory::String; recursive::Bool=true)::Int
    if !isdir(directory)
        @warn "Directory not found: $directory"
        return 0
    end

    if !is_pandoc_available()
        @info "Pandoc not found in PATH, skipping conversion"
        return 0
    end

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

    @info "Found $(length(typ_files)) Typst files to convert in $directory"

    success_count = 0
    for typ_file in typ_files
        if convert_typ_to_docx(typ_file)
            success_count += 1
        end
    end

    @info "📋 Pandoc conversion summary: $success_count/$(length(typ_files)) files converted successfully"
    return success_count
end

"""
    convert_main_report(report_dir::String, main_report_name::String="report.typ") -> Bool

Convert the main report file in a report directory to DOCX.

# Arguments
- `report_dir::String`: Directory containing the main report
- `main_report_name::String`: Name of the main report file, defaults to "report.typ"

# Returns
- `Bool`: true if conversion succeeded, false otherwise
"""
function convert_main_report(report_dir::String, main_report_name::String="report.typ")::Bool
    main_report_path = joinpath(report_dir, main_report_name)
    return convert_typ_to_docx(main_report_path)
end

"""
    pandoc_try_convert(report_dir::String, report_filename::String="report.typ") -> Nothing

Generic function that tries to convert a Typst report to DOCX with user-friendly messaging.
Checks if Pandoc is available, attempts conversion, and provides appropriate feedback.

# Arguments
- `report_dir::String`: Directory containing the Typst file
- `report_filename::String`: Name of the Typst file, defaults to "report.typ"

# Examples
```julia
# Simple usage - convert report.typ in current directory
pandoc_try_convert("./reports")

# Custom filename
pandoc_try_convert("./reports", "analysis.typ")
```
"""
function pandoc_try_convert(report_dir::String, report_filename::String="report.typ")::Nothing
    if is_pandoc_available()
        println("📄 Converting Typst report to DOCX...")
        if convert_main_report(report_dir, report_filename)
            println("✅ Pandoc conversion successful!")
        else
            println("⚠️  Pandoc conversion failed, but $report_filename file is available")
            println("   Convert manually: pandoc $report_filename -o $(splitext(report_filename)[1]).docx -f typst -t docx")
        end
    else
        println("ℹ️  Pandoc not found in PATH, skipping DOCX conversion")
        println("   Convert manually: pandoc $report_filename -o $(splitext(report_filename)[1]).docx -f typst -t docx")
    end
end

"""
    pandoc_try_convert_all(directory::String; recursive::Bool=true) -> Nothing

Generic function that tries to convert all Typst files in a directory to DOCX with user-friendly messaging.
Checks if Pandoc is available, attempts batch conversion, and provides appropriate feedback.

# Arguments
- `directory::String`: Directory to search for .typ files
- `recursive::Bool`: Whether to search subdirectories, defaults to true

# Examples
```julia
# Convert all .typ files in reports directory
pandoc_try_convert_all("./reports")

# Non-recursive conversion
pandoc_try_convert_all("./reports"; recursive=false)
```
"""
function pandoc_try_convert_all(directory::String; recursive::Bool=true)::Nothing
    if is_pandoc_available()
        println("📄 Converting Typst reports to DOCX...")
        converted_count = convert_typ_files(directory; recursive=recursive)
        if converted_count > 0
            println("✅ Successfully converted $converted_count Typst report(s) to DOCX!")
        else
            println("⚠️  No Typst files found or conversion failed")
        end
    else
        println("ℹ️  Pandoc not found in PATH, skipping DOCX conversion")
    end
end

end # module
