module CleanMastLogger

using Logging
using LoggingExtras

include("Utils.jl")
include("LogRotation.jl")
include("TerminalFormatter.jl")
include("JSONLLogger.jl")

using .Utils
using .LogRotation
using .TerminalFormatter
using .JSONLLogger

export create_cleanmast_logger

function create_cleanmast_logger(;
    job_name::String,
    worker_id::Int,
    config_dir::String,
    config_basename::String,
    terminal_level::Logging.LogLevel=Logging.Info,
    file_level::Logging.LogLevel=Logging.Debug,
    enable_terminal::Bool=true,
    enable_file::Bool=true,
    archive_logs::Bool=false,
    keep_days::Int=30,
    terminal_stream::IO=stderr
)
    loggers = []

    if enable_terminal
        terminal_logger = TerminalFormatter.create_terminal_logger(
            job_name,
            worker_id,
            terminal_level;
            stream=terminal_stream
        )
        push!(loggers, terminal_logger)
    end

    if enable_file
        log_file = LogRotation.prepare_log_file(
            config_dir,
            config_basename,
            worker_id;
            archive=archive_logs,
            keep_days=keep_days
        )

        jsonl_logger = JSONLLogger.JSONLFileLogger(
            log_file,
            job_name,
            worker_id;
            min_level=file_level
        )
        push!(loggers, jsonl_logger)
    end

    if length(loggers) == 0
        error("At least one logger (terminal or file) must be enabled")
    elseif length(loggers) == 1
        return loggers[1]
    else
        return TeeLogger(loggers...)
    end
end

end
