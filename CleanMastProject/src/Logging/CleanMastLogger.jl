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

export create_cleanmast_logger, WorkerLoggerManager, get_logger, cleanup!

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

mutable struct WorkerLoggerManager
    loggers::Vector{Union{Nothing, Logging.AbstractLogger}}
    config_dir::String
    config_basename::String
    terminal_level::Logging.LogLevel
    file_level::Logging.LogLevel
    enable_terminal::Bool
    enable_file::Bool
    archive_logs::Bool
    keep_days::Int
    terminal_stream::IO
end

function WorkerLoggerManager(
    config_dir::String,
    config_basename::String;
    terminal_level::Logging.LogLevel=Logging.Info,
    file_level::Logging.LogLevel=Logging.Debug,
    enable_terminal::Bool=true,
    enable_file::Bool=true,
    archive_logs::Bool=false,
    keep_days::Int=30,
    terminal_stream::IO=stderr,
    max_threads::Int=1000
)
    return WorkerLoggerManager(
        fill(nothing, max_threads),
        config_dir,
        config_basename,
        terminal_level,
        file_level,
        enable_terminal,
        enable_file,
        archive_logs,
        keep_days,
        terminal_stream
    )
end

function get_logger(manager::WorkerLoggerManager, tid::Int)
    if tid < 1 || tid > length(manager.loggers)
        error("Thread ID $tid out of bounds (1:$(length(manager.loggers))). " *
              "Increase max_threads parameter if needed.")
    end

    logger = manager.loggers[tid]

    if logger === nothing
        logger = create_cleanmast_logger(
            job_name=manager.config_basename,
            worker_id=tid,
            config_dir=manager.config_dir,
            config_basename=manager.config_basename,
            terminal_level=manager.terminal_level,
            file_level=manager.file_level,
            enable_terminal=manager.enable_terminal,
            enable_file=manager.enable_file,
            archive_logs=manager.archive_logs,
            keep_days=manager.keep_days,
            terminal_stream=manager.terminal_stream
        )
        manager.loggers[tid] = logger
    end

    return logger
end

function cleanup!(manager::WorkerLoggerManager)
    fill!(manager.loggers, nothing)
    return nothing
end

end
