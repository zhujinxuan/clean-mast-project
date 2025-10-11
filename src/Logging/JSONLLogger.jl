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
        open(logger.log_file, "a") do io
            JSON.print(io, log_entry)
            println(io)
        end
    end
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

    return entry
end

end
