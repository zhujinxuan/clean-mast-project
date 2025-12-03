using Test
using CleanMastProject.Types.MastTimeSeries: TimeSeriesSource, adjust_relative_path, adjust_timeseries_source_paths

@testset "MastTimeSeries Path Utilities" begin
    @testset "adjust_relative_path" begin
        # Test relative path with ./ prefix
        @test adjust_relative_path("./data/file.csv", "../") == "../data/file.csv"

        # Test relative path without ./ prefix
        @test adjust_relative_path("data/file.csv", "../") == "../data/file.csv"

        # Test absolute path (Windows)
        @test adjust_relative_path("C:\\abs\\path\\file.csv", "../") == "C:\\abs\\path\\file.csv"

        # Test absolute path (Unix)
        @test adjust_relative_path("/abs/path/file.csv", "../") == "/abs/path/file.csv"

        # Test with different prefix
        @test adjust_relative_path("./data/file.csv", "../../") == "../../data/file.csv"

        # Test empty prefix
        @test adjust_relative_path("./data/file.csv", "") == "data/file.csv"

        # Test path without prefix
        @test adjust_relative_path("data/file.csv", "prefix/") == "prefix/data/file.csv"
    end

    @testset "adjust_timeseries_source_paths" begin
        # Test with relative paths
        source = TimeSeriesSource("./data/raw.csv", "./data/sensors.toml")
        adjusted = adjust_timeseries_source_paths(source, "../")
        @test adjusted.data == "../data/raw.csv"
        @test adjusted.sensors == "../data/sensors.toml"

        # Test with absolute paths (should remain unchanged) - Windows
        source_abs = TimeSeriesSource("C:\\abs\\raw.csv", "C:\\abs\\sensors.toml")
        adjusted_abs = adjust_timeseries_source_paths(source_abs, "../")
        @test adjusted_abs.data == "C:\\abs\\raw.csv"
        @test adjusted_abs.sensors == "C:\\abs\\sensors.toml"

        # Test with absolute paths (should remain unchanged) - Unix
        source_unix = TimeSeriesSource("/abs/raw.csv", "/abs/sensors.toml")
        adjusted_unix = adjust_timeseries_source_paths(source_unix, "../")
        @test adjusted_unix.data == "/abs/raw.csv"
        @test adjusted_unix.sensors == "/abs/sensors.toml"

        # Test with mixed paths
        source_mixed = TimeSeriesSource("./data/raw.csv", "C:\\abs\\sensors.toml")
        adjusted_mixed = adjust_timeseries_source_paths(source_mixed, "../")
        @test adjusted_mixed.data == "../data/raw.csv"
        @test adjusted_mixed.sensors == "C:\\abs\\sensors.toml"

        # Test with empty prefix
        source_empty = TimeSeriesSource("./data/raw.csv", "./data/sensors.toml")
        adjusted_empty = adjust_timeseries_source_paths(source_empty, "")
        @test adjusted_empty.data == "data/raw.csv"
        @test adjusted_empty.sensors == "data/sensors.toml"
    end
end
