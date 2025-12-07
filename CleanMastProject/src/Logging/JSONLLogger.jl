module JSONLLogger

using Logging
using JSON
using Dates
using ..Utils: format_stacktrace, extract_error_info

export JSONLFileLogger

mutable struct JSONLFileLogger <: Logging.AbstractLogger
    job_name::String
    worker_id::Int
    log_file::String
    file_lock::ReentrantLock
    min_level::Logging.LogLevel
end

function JSONLFileLogger(
    log_file::String,
    job_name::String,
    worker_id::Int;
    min_level::Logging.LogLevel=Logging.Debug
)
    return JSONLFileLogger(
        job_name,
        worker_id,
        log_file,
        ReentrantLock(),
        min_level
    )
end

Logging.min_enabled_level(logger::JSONLFileLogger) = logger.min_level

Logging.shouldlog(logger::JSONLFileLogger, level, _module, group, id) =
    level >= logger.min_level

Logging.catch_exceptions(logger::JSONLFileLogger) = false

function Logging.handle_message(
    logger::JSONLFileLogger,
    level,
    message,
    _module,
    group,
    id,
    file,
    line;
    kwargs...
)
    log_entry = create_log_entry(
        logger.job_name,
        logger.worker_id,
        level,
        message,
        kwargs
    )

    lock(logger.file_lock) do
        # Convert to JSON string first (don't write partial data)
        json_string = try
            JSON.json(log_entry)
        catch e
            # JSON serialization failed, try sanitizing values
            sanitized_entry = sanitize_for_json(log_entry)
            JSON.json(sanitized_entry)
        end

        # Write complete JSON string atomically
        open(logger.log_file, "a") do io
            println(io, json_string)
        end
    end
end

function sanitize_for_json(entry::Dict)
    sanitized = copy(entry)
    for (key, value) in entry
        try
            # Test if this value can be serialized
            test_io = IOBuffer()
            JSON.print(test_io, Dict("test" => value))
        catch
            # Try string() conversion
            try
                sanitized[key] = string(value)
            catch
                # Try show() conversion
                try
                    io = IOBuffer()
                    show(io, value)
                    sanitized[key] = String(take!(io))
                catch
                    # Skip this key entirely
                    delete!(sanitized, key)
                end
            end
        end
    end
    return sanitized
end

function create_log_entry(
    job_name::String,
    worker_id::Int,
    level::Logging.LogLevel,
    message,
    kwargs
)
    entry = Dict{String, Any}(
        "timestamp" => Dates.format(now(), "yyyy-mm-ddTHH:MM:SS.sss") * "Z",
        "level" => string(level),
        "job_name" => job_name,
        "worker_id" => worker_id
    )

    message_str = string(message)
    if contains(message_str, '\n')
        entry["message"] = split(message_str, '\n')
    else
        entry["message"] = message_str
    end

    exception_info = get(kwargs, :exception, nothing)

    if level >= Logging.Error && exception_info === nothing
        try
            current_exceptions = Base.current_exceptions()
            if !isempty(current_exceptions)
                exc_info = current_exceptions[end]
                exception_info = (exc_info.exception, exc_info.backtrace)
            end
        catch
        end
    end

    if exception_info !== nothing
        exc, bt = exception_info
        error_type, error_message, additional_info = extract_error_info(exc)

        entry["error_type"] = error_type
        entry["error_message"] = error_message

        if !isempty(additional_info)
            merge!(entry, additional_info)
        end

        stacktrace_lines = format_stacktrace(bt)
        if !isempty(stacktrace_lines)
            entry["stacktrace"] = stacktrace_lines
        end
    end

    # Add all other kwargs to the log entry (skip non-serializable types)
    for (key, value) in kwargs
        key_str = string(key)
        # Skip exception as it's already handled above
        if key_str != "exception"
            # Try to add the value, but skip if it's not JSON-serializable
            # Skip non-serializable types
            if value isa Ptr || value isa DataType || value isa Module || value isa Function
                continue
            end

            # Add value - if JSON serialization fails later, it will be caught
            # and we'll try fallback conversions
            entry[key_str] = value
        end
    end

    return entry
end

end
