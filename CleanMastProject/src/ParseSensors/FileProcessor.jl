# src/ParseSensors/FileProcessor.jl
"""
Functions for file-level introspection, such as detecting delimiters,
headers, and timestamp formats to prepare for data loading.
"""
module FileProcessor

using Dates
using ...Types.ParseSensorsConfig: SensorFormatConfig

export generate_csv_opts, detect_delimiter, detect_timestamp_format, find_header_line

"""
Convert string to Regex if it's enclosed in forward slashes, otherwise return the string as is.
"""
function string_to_regex_or_string(s::String)::Union{Regex,String}
    if startswith(s, "/") && endswith(s, "/")
        return Regex(s[2:end-1])
    end
    return s
end

"""
Check if a line appears to be a data line by checking if it starts with a date-like pattern.
"""
function is_data_line(line::String, delim::Union{String, Nothing})::Bool
    isempty(strip(line)) && return false
    
    # A data line is very likely to start with a standard date format like YYYY-MM-DD or YYYY/MM/DD
    # This is a much more reliable heuristic than just checking for any number.
    starts_with_date = occursin(r"^\s*[0-9]{4}[-/][0-9]{2}[-/][0-9]{2}", line)
    delims = !isnothing(delim) ? [delim] : [',', '\t', ';']
    has_delims = any(c -> occursin(c, line), delims)
    return starts_with_date && has_delims
end

"""
Find the number of lines to skip before data starts.
"""
function find_header_line(csv_filepath::String, header_line::Union{Int64,Nothing}, delim::Union{String, Nothing})::Union{Int64, Nothing}
    if !isnothing(header_line) 
        return header_line
    end
    
    consecutive_numeric = 0
    
    for (line_num, line) in enumerate(eachline(csv_filepath))
        if is_data_line(line, delim)
            consecutive_numeric += 1
            if consecutive_numeric == 5 # Require 5 consecutive data lines to be sure
                return line_num - 5
            end
        else
            consecutive_numeric = 0
        end
    end
    @warn "Could not automatically detect header line in $csv_filepath."
    return nothing
end

"""
Detect the most common delimiter in a set of lines from a CSV file.
"""
function detect_delimiter(csv_filepath::String, header_line::Int)::Union{String, Nothing}
    delimiters = Dict{String, Int64}("\t" => 0, "," => 0, ";" => 0)
    lines_to_check = 5
    
    open(csv_filepath, "r") do file
        for (i, line) in enumerate(eachline(file))
            i <= header_line && continue
            i > header_line + lines_to_check && break
            
            delimiters["\t"] += count("\t", line)
            delimiters[","] += count(",", line)
            delimiters[";"] += count(";", line)
        end
    end
    delim = argmax(delimiters)
    max_count = delimiters[delim]
    if max_count < 5
        @warn "No common delimiter found in $csv_filepath"
        return nothing
    end
    return delim
end

const COMMON_DATETIME_FORMATS = [
    "yyyy-mm-dd HH:MM:SS", "yyyy/mm/dd HH:MM:SS", "dd-mm-yyyy HH:MM:SS",
    "dd/mm/yyyy HH:MM:SS", "mm-dd-yyyy HH:MM:SS", "mm/dd/yyyy HH:MM:SS",
    "yyyy-mm-ddTHH:MM:SS", "yyyymmdd HH:MM:SS", "dd.mm.yyyy HH:MM:SS",
    "yyyymmddHHMMSS"
]

"""
Detect the timestamp format in a CSV file.
"""
function detect_timestamp_format(csv_filepath::String, header_line::Int64, timestamp_column::String, delim::String)::Union{String, Nothing}
    header = ""
    samples = String[]
    
    open(csv_filepath, "r") do file
        for (i, line) in enumerate(eachline(file))
            if i == header_line
                header = line
            elseif i > header_line && length(samples) < 10
                push!(samples, line)
            elseif length(samples) >= 10
                break
            end
        end
    end

    header_fields = split(header, delim)
    col_idx = findfirst(strip.(header_fields) .== timestamp_column)
    isnothing(col_idx) && throw(ErrorException("Timestamp column '$timestamp_column' not found in header: $header"))

    timestamps = [strip(split(line, delim)[col_idx]) for line in samples if length(split(line, delim)) >= col_idx]
    
    for format in COMMON_DATETIME_FORMATS
        try
            all(ts -> !isnothing(DateTime(ts, format)), timestamps) && return format
        catch
            continue
        end
    end
    
    @warn "Could not automatically detect timestamp format for column '$timestamp_column'."
    return nothing
end

"""
Generate CSV options for reading data files based on sensor format configuration.
"""
function generate_csv_opts(sensor_config::SensorFormatConfig, csv_file::String)::Dict{Symbol, Any}
    header_line = find_header_line(csv_file, sensor_config.skip_to, sensor_config.delim)
    
    delim = !isnothing(sensor_config.delim) ? sensor_config.delim : detect_delimiter(csv_file, header_line)
    dateformat = !isnothing(sensor_config.timestamp_format) ? sensor_config.timestamp_format : detect_timestamp_format(csv_file, header_line, sensor_config.timestamp_column, delim)
    isnothing(dateformat) && throw(ErrorException("Timestamp format could not be detected and was not specified."))

    return Dict{Symbol, Any}(
        :skipto => header_line + 1,
        :header => header_line,
        :dateformat => dateformat,
        :delim => delim
    )
end

end 