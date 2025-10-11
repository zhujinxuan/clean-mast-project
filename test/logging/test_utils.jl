using Test
using CleanMastProject.CleanMastLogging.CleanMastLogger.Utils

@testset "Utils Tests" begin
    @testset "strip_ansi" begin
        @test strip_ansi("plain text") == "plain text"
        @test strip_ansi("\e[31mred text\e[0m") == "red text"
        @test strip_ansi("\e[1m\e[36mbold cyan\e[0m") == "bold cyan"
    end

    @testset "format_stacktrace" begin
        bt = try
            error("test error")
        catch e
            catch_backtrace()
        end

        stacktrace_lines = format_stacktrace(bt)
        @test length(stacktrace_lines) > 0
        @test all(line -> contains(line, "@"), stacktrace_lines)
        @test all(line -> contains(line, ":"), stacktrace_lines)
    end

    @testset "extract_error_info" begin
        exc = SystemError("open", 2)
        error_type, error_message, additional_info = extract_error_info(exc)

        @test error_type == "SystemError"
        @test contains(error_message, "open")
        @test haskey(additional_info, "errno")
    end
end
