using Test
using CleanMastProject.CleanMastLogging.CleanMastLogger.JSONLLogger
using Logging
using JSON

# Custom test types for serialization fallback testing
struct TypeWithBrokenString
    value::String
end
# Make JSON serialization fail by throwing error in JSON.lower()
JSON.lower(t::TypeWithBrokenString) = error("JSON serialization failed!")
Base.string(::TypeWithBrokenString) = error("string() is broken!")
Base.show(io::IO, t::TypeWithBrokenString) = print(io, "TypeWithBrokenString(", t.value, ")")

struct TypeWithBrokenShowAndString
    value::String
end
# Make JSON serialization fail
JSON.lower(t::TypeWithBrokenShowAndString) = error("JSON serialization failed!")
Base.string(::TypeWithBrokenShowAndString) = error("string() is broken!")
Base.show(io::IO, ::TypeWithBrokenShowAndString) = error("show() is broken!")

@testset "JSONL Logger Tests" begin
    @testset "Basic logging" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                @info "Test message 1"
                @warn "Test warning"
                @error "Test error"
            end

            @test isfile(log_file)
            lines = readlines(log_file)
            @test length(lines) == 3

            log1 = JSON.parse(lines[1])
            @test log1["level"] == "Info"
            @test log1["job_name"] == "test-job"
            @test log1["worker_id"] == 1
            @test log1["message"] == "Test message 1"
            @test haskey(log1, "timestamp")
        end
    end

    @testset "Multiline messages" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                @info "Line 1\nLine 2\nLine 3"
            end

            line = readline(log_file)
            log = JSON.parse(line)

            @test log["message"] isa Vector
            @test length(log["message"]) == 3
            @test log["message"][1] == "Line 1"
        end
    end

    @testset "Error with exception" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                try
                    error("Test error")
                catch e
                    @error "Caught error" exception=(e, catch_backtrace())
                end
            end

            line = readline(log_file)
            log = JSON.parse(line)

            @test log["level"] == "Error"
            @test haskey(log, "error_type")
            @test log["error_type"] == "ErrorException"
            @test haskey(log, "stacktrace")
            @test log["stacktrace"] isa Vector
        end
    end

    @testset "Kwargs serialization" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                # Normal serializable kwargs
                @info "Test" string_key="value" int_key=42 float_key=3.14 bool_key=true
            end

            line = readline(log_file)
            log = JSON.parse(line)

            @test log["string_key"] == "value"
            @test log["int_key"] == 42
            @test log["float_key"] == 3.14
            @test log["bool_key"] == true
        end
    end

    @testset "Non-serializable types are filtered" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                # These should be filtered out (Layer 1)
                @info "Test" ptr=Ptr{Nothing}(0) datatype=Int64 mod=Base func=sin normal="kept"
            end

            line = readline(log_file)
            log = JSON.parse(line)

            # Non-serializable types should be filtered
            @test !haskey(log, "ptr")
            @test !haskey(log, "datatype")
            @test !haskey(log, "mod")
            @test !haskey(log, "func")

            # Normal kwargs should be kept
            @test log["normal"] == "kept"
        end
    end

    @testset "Fallback to show() when string() fails" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                # This type's string() throws error, but show() works
                broken_type = TypeWithBrokenString("test_value")
                @info "Test" broken=broken_type normal="kept"
            end

            line = readline(log_file)
            log = JSON.parse(line)

            # Should fallback to show() representation
            @test haskey(log, "broken")
            @test log["broken"] == "TypeWithBrokenString(test_value)"
            @test log["normal"] == "kept"
        end
    end

    @testset "Skip kwargs when both string() and show() fail" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                # This type's both string() and show() throw errors
                fully_broken = TypeWithBrokenShowAndString("test_value")
                @info "Test" fully_broken=fully_broken normal="kept"
            end

            line = readline(log_file)
            log = JSON.parse(line)

            # Should skip the broken kwarg entirely
            @test !haskey(log, "fully_broken")
            @test log["normal"] == "kept"
        end
    end
end
