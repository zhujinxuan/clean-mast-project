module TerminalFormatter

using TerminalLoggers
using Logging
using ..Utils: format_stacktrace

export create_terminal_logger

const ANSI_COLORS = Dict(
    :cyan => "\e[36m",
    :green => "\e[32m",
    :yellow => "\e[33m",
    :red => "\e[31m",
    :gray => "\e[90m",
    :bold => "\e[1m",
    :reset => "\e[0m"
)

function create_terminal_logger(
    job_name::String,
    worker_id::Int,
    min_level::Logging.LogLevel=Logging.Info;
    stream::IO=stderr
)
    meta_formatter = (level, _module, group, id, file, line) ->
        format_meta(level, job_name, worker_id, file, line)

    return TerminalLogger(stream, min_level; meta_formatter=meta_formatter)
end

function format_meta(level, job_name, worker_id, file, line)
    job_prefix = format_job_prefix(job_name, worker_id)
    level_str, level_color = format_level(level)

    prefix = "$job_prefix $level_str"
    suffix = ""

    return level_color, prefix, suffix
end

function format_job_prefix(job_name::String, worker_id::Int)::String
    cyan = ANSI_COLORS[:cyan]
    bold = ANSI_COLORS[:bold]
    reset = ANSI_COLORS[:reset]
    return "$(cyan)$(bold)[$(job_name):$(worker_id)]$(reset)"
end

function format_level(level::Logging.LogLevel)::Tuple{String, Symbol}
    if level == Logging.Debug
        return "DEBUG", :light_black
    elseif level == Logging.Info
        return "INFO ", :cyan
    elseif level == Logging.Warn
        return "WARN ", :yellow
    elseif level >= Logging.Error
        return "ERROR", :red
    else
        return "LOG  ", :normal
    end
end

end
