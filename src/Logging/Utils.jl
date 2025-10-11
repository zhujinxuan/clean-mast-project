module Utils

export format_stacktrace, strip_ansi, extract_error_info

function format_stacktrace(bt::Vector)::Vector{String}
    frames = stacktrace(bt)

    filtered_frames = filter(frames) do frame
        file_str = string(frame.file)
        !contains(file_str, "Logging.jl") &&
        !contains(file_str, "boot.jl") &&
        !contains(file_str, "client.jl")
    end

    return map(filtered_frames) do frame
        func = frame.func
        file = basename(string(frame.file))
        line = frame.line
        "$(func) @ $(file):$(line)"
    end
end

function strip_ansi(s::String)::String
    return replace(s, r"\e\[[0-9;]*m" => "")
end

function extract_error_info(exc::Exception)
    error_type = string(typeof(exc))
    error_message = sprint(showerror, exc)

    additional_info = Dict{String, Any}()

    if exc isa SystemError
        additional_info["errno"] = exc.errnum
        if !isnothing(exc.prefix)
            additional_info["prefix"] = exc.prefix
        end
    elseif exc isa LoadError
        additional_info["file"] = exc.file
        additional_info["line"] = exc.line
    end

    return error_type, error_message, additional_info
end

end
