using Test
using CleanMastProject.CleanMastLogging.CleanMastLogger.LogRotation
using Dates

@testset "Log Rotation Tests" begin
    @testset "prepare_log_file - creates new file" begin
        mktempdir() do tmpdir
            log_file = prepare_log_file(tmpdir, "test", 1; archive=false)

            @test endswith(log_file, "test.1.jsonl")
            log_dir = joinpath(tmpdir, "logs")
            @test isdir(log_dir)
        end
    end

    @testset "prepare_log_file - archives existing file" begin
        mktempdir() do tmpdir
            log_dir = joinpath(tmpdir, "logs")
            mkpath(log_dir)

            initial_log = joinpath(log_dir, "test.1.jsonl")
            write(initial_log, "old log content\n")

            log_file = prepare_log_file(tmpdir, "test", 1; archive=true, keep_days=30)

            @test log_file == initial_log
            content = read(log_file, String)
            @test !contains(content, "old log content")

            archive_dir = joinpath(log_dir, "archive")
            @test isdir(archive_dir)

            archives = readdir(archive_dir)
            @test length(archives) == 1
            @test startswith(archives[1], "test.1.")
            @test endswith(archives[1], ".jsonl")
            @test contains(read(joinpath(archive_dir, archives[1]), String), "old log content")
        end
    end

    @testset "cleanup_old_logs" begin
        mktempdir() do tmpdir
            archive_dir = joinpath(tmpdir, "archive")
            mkpath(archive_dir)

            recent_file = joinpath(archive_dir, "test.1.$(Dates.format(now(), "yyyymmddTHHMMSS.sss")).jsonl")
            write(recent_file, "recent")

            cleanup_old_logs(archive_dir, 30)

            @test isfile(recent_file)
        end
    end

    @testset "archive_all_worker_logs" begin
        mktempdir() do tmpdir
            log_dir = joinpath(tmpdir, "logs")
            mkpath(log_dir)

            write(joinpath(log_dir, "test.1.jsonl"), "worker 1 log\n")
            write(joinpath(log_dir, "test.2.jsonl"), "worker 2 log\n")
            write(joinpath(log_dir, "test.3.jsonl"), "worker 3 log\n")

            archive_all_worker_logs(tmpdir, "test", 4; keep_days=30)

            @test !isfile(joinpath(log_dir, "test.1.jsonl"))
            @test !isfile(joinpath(log_dir, "test.2.jsonl"))
            @test !isfile(joinpath(log_dir, "test.3.jsonl"))

            archive_dir = joinpath(log_dir, "archive")
            @test isdir(archive_dir)

            archives = readdir(archive_dir)
            @test length(archives) == 3

            for archive in archives
                @test startswith(archive, "test.")
                @test endswith(archive, ".jsonl")
            end
        end
    end
end
