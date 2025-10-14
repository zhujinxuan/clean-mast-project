module LogRotation

using Dates

export prepare_log_file, cleanup_old_logs, archive_all_worker_logs

function prepare_log_file(
    config_dir::String,
    config_basename::String,
    worker_id::Int;
    archive::Bool=true,
    keep_days::Int=30
)::String
    log_dir = joinpath(config_dir, "logs")
    mkpath(log_dir)

    log_file = joinpath(log_dir, "$(config_basename).$(worker_id).jsonl")

    if archive && isfile(log_file)
        archive_dir = joinpath(log_dir, "archive")
        mkpath(archive_dir)

        timestamp = Dates.format(now(), "yyyymmddTHHMMSS.sss")
        archive_file = joinpath(archive_dir,
            "$(config_basename).$(worker_id).$(timestamp).jsonl")

        mv(log_file, archive_file)

        cleanup_old_logs(archive_dir, keep_days)
    end

    touch(log_file)

    return log_file
end

function cleanup_old_logs(archive_dir::String, keep_days::Int)
    if !isdir(archive_dir)
        return
    end

    cutoff = now() - Day(keep_days)

    for file in readdir(archive_dir; join=true)
        if isfile(file) && endswith(file, ".jsonl")
            file_mtime = unix2datetime(mtime(file))
            if file_mtime < cutoff
                try
                    rm(file)
                catch e
                    @warn "Failed to delete old log archive" file=file error=e
                end
            end
        end
    end
end

"""
    archive_all_worker_logs(config_dir::String, config_basename::String, num_threads::Int; keep_days::Int=30)

Archive existing log files for all potential worker threads before starting parallel work.
This prevents race conditions when multiple workers try to archive the same log file.

# Arguments
- `config_dir::String`: Configuration directory containing logs
- `config_basename::String`: Base name for log files
- `num_threads::Int`: Number of threads (typically Threads.nthreads())
- `keep_days::Int`: Number of days to keep archived logs (default: 30)
"""
function archive_all_worker_logs(
    config_dir::String,
    config_basename::String,
    num_threads::Int;
    keep_days::Int=30
)
    log_dir = joinpath(config_dir, "logs")

    if !isdir(log_dir)
        return
    end

    archive_dir = joinpath(log_dir, "archive")

    for worker_id in 1:num_threads
        log_file = joinpath(log_dir, "$(config_basename).$(worker_id).jsonl")

        if isfile(log_file)
            mkpath(archive_dir)

            timestamp = Dates.format(now(), "yyyymmddTHHMMSS.sss")
            archive_file = joinpath(archive_dir,
                "$(config_basename).$(worker_id).$(timestamp).jsonl")

            mv(log_file, archive_file)
        end
    end

    if isdir(archive_dir)
        cleanup_old_logs(archive_dir, keep_days)
    end
end

end
