# test/ParseSensors/test_dataframe_processor.jl

using Test
using DataFrames
using Dates
using CleanMastProject.Types.SensorColumns: ParsedSensor
using CleanMastProject.ParseSensors.DataFrameProcessor

include("fixtures/fixtures.jl")

@testset "DataFrameProcessor Tests" begin

    @testset "group_sensors_by_column_name" begin
        sensors = [
            ParsedSensor(
                :WindSpeed_120m_SE_avg, "", "WindSpeed", "SE", 120.0, "avg", "m/s",
                originalColumnNames=:Ch2_Anem_120m_SE_Avg
            ),
            ParsedSensor(
                :WindSpeed_120m_SE_avg, "", "WindSpeed", "SE", 120.0, "avg", "m/s",
                originalColumnNames=:Ch7_Anem_120m_SE_Avg
            ),
            ParsedSensor(
                :WindSpeed_100m_SE_avg, "", "WindSpeed", "SE", 100.0, "avg", "m/s",
                originalColumnNames=:Ch3_Anem_100m_SE_Avg
            )
        ]

        grouped = DataFrameProcessor.group_sensors_by_column_name(sensors)

        @test length(grouped) == 2
        @test length(grouped[:WindSpeed_120m_SE_avg]) == 2
        @test length(grouped[:WindSpeed_100m_SE_avg]) == 1
    end

    @testset "calculate_overlap_percentage" begin
        df = DataFrame(
            col1 = [1.0, 2.0, missing, 4.0, missing],
            col2 = [missing, 2.0, 3.0, 4.0, missing]
        )

        # Both have data in rows 2 and 4 (2/5 = 40%)
        overlap_pct = DataFrameProcessor.calculate_overlap_percentage(df, :col1, :col2)
        @test overlap_pct == 40.0

        # No overlap
        df_no_overlap = DataFrame(
            col1 = [1.0, 2.0, missing, missing],
            col2 = [missing, missing, 3.0, 4.0]
        )
        overlap_pct = DataFrameProcessor.calculate_overlap_percentage(df_no_overlap, :col1, :col2)
        @test overlap_pct == 0.0
    end

    @testset "merge_sensor_group - no warning" begin
        df = DataFrame(
            Ch2_Anem = [1.0, 2.0, missing],
            Ch7_Anem = [missing, missing, 3.0]
        )

        sensors = [
            ParsedSensor(:WindSpeed_120m_SE_avg, "", "WindSpeed", "SE", 120.0, "avg", "m/s",
                        originalColumnNames=Symbol("Ch2_Anem")),
            ParsedSensor(:WindSpeed_120m_SE_avg, "", "WindSpeed", "SE", 120.0, "avg", "m/s",
                        originalColumnNames=Symbol("Ch7_Anem"))
        ]

        # Should not warn (0% overlap)
        merged = DataFrameProcessor.merge_sensor_group(sensors, df)

        @test merged.columnName == :WindSpeed_120m_SE_avg
        @test length(merged.originalColumnNames) == 2
        @test Symbol("Ch2_Anem") in merged.originalColumnNames
        @test Symbol("Ch7_Anem") in merged.originalColumnNames
    end

    @testset "merge_sensor_group - with warning" begin
        # Create data with >10% overlap
        df = DataFrame(
            Ch2_Anem = vcat([1.0, 2.0, 3.0, 4.0], fill(missing, 6)),
            Ch7_Anem = vcat(fill(missing, 2), [3.0, 4.0, 5.0, 6.0, 7.0, 8.0], fill(missing, 2))
        )

        sensors = [
            ParsedSensor(:WindSpeed_120m_SE_avg, "", "WindSpeed", "SE", 120.0, "avg", "m/s",
                        originalColumnNames=Symbol("Ch2_Anem")),
            ParsedSensor(:WindSpeed_120m_SE_avg, "", "WindSpeed", "SE", 120.0, "avg", "m/s",
                        originalColumnNames=Symbol("Ch7_Anem"))
        ]

        # Should warn (rows 3-4 have overlap = 2/10 = 20%)
        @test_logs (:warn, r"Significant overlap detected") begin
            DataFrameProcessor.merge_sensor_group(sensors, df)
        end
    end

    @testset "merge_columns! - latter wins" begin
        df = DataFrame(
            timestamp = [1, 2, 3, 4, 5],
            Ch2 = [1.0, 2.0, missing, missing, missing],
            Ch7 = [missing, missing, 3.0, 4.0, 5.0]
        )

        DataFrameProcessor.merge_columns!(df, :merged, [:Ch2, :Ch7])

        @test "merged" in names(df)
        @test "Ch2" ∉ names(df)
        @test "Ch7" ∉ names(df)
        @test df.merged == [1.0, 2.0, 3.0, 4.0, 5.0]
    end

    @testset "merge_columns! - latter wins (both have data)" begin
        df = DataFrame(
            timestamp = [1, 2, 3],
            Ch2 = [1.0, 2.0, 3.0],
            Ch7 = [10.0, 20.0, 30.0]
        )

        DataFrameProcessor.merge_columns!(df, :merged, [:Ch2, :Ch7])

        # Ch7 should win (latter wins strategy)
        @test df.merged == [10.0, 20.0, 30.0]
    end

    @testset "transform_columns! - simple rename" begin
        df = DataFrame(timestamp = [DateTime(2024,1,1)])
        df[!, Symbol("Ch1_Anem_80m_NW_Avg_m/s")] = [5.0]

        sensors = [
            ParsedSensor(
                Symbol("WindSpeed_80m_NW_avg [m/s]"),
                "",
                "WindSpeed",
                "NW",
                80.0,
                "avg",
                "m/s",
                originalColumnNames=Symbol("Ch1_Anem_80m_NW_Avg_m/s")
            )
        ]

        df_result, sensors_result = transform_columns!(df, sensors)

        @test "WindSpeed_80m_NW_avg [m/s]" in names(df_result)
        @test "Ch1_Anem_80m_NW_Avg_m/s" ∉ names(df_result)
        @test df_result[1, Symbol("WindSpeed_80m_NW_avg [m/s]")] == 5.0
        @test length(sensors_result) == 1
    end

    @testset "transform_columns! - with multiplier" begin
        df = DataFrame(timestamp = [DateTime(2024,1,1)])
        df[!, Symbol("Ch1_Analog_10m_Avg_hPa")] = [1013.25]

        sensors = [
            ParsedSensor(
                Symbol("Pressure_10m_avg [Pa]"),
                "",
                "Pressure",
                "N/A",
                10.0,
                "avg",
                "Pa",
                originalColumnNames=Symbol("Ch1_Analog_10m_Avg_hPa"),
                multiplier=100.0
            )
        ]

        df_result, sensors_result = transform_columns!(df, sensors)

        @test df_result[1, Symbol("Pressure_10m_avg [Pa]")] ≈ 101325.0
    end

    @testset "transform_columns! - merge duplicates" begin
        df = DataFrame(timestamp = collect(1:200))
        df[!, Symbol("Ch2_Anem_120m_SE_Avg")] = vcat(rand(100), fill(missing, 100))
        df[!, Symbol("Ch7_Anem_120m_SE_Avg")] = vcat(fill(missing, 100), rand(100))

        sensors = [
            ParsedSensor(
                Symbol("WindSpeed_120m_SE_avg [m/s]"),
                "",
                "WindSpeed",
                "SE",
                120.0,
                "avg",
                "m/s",
                originalColumnNames=Symbol("Ch2_Anem_120m_SE_Avg")
            ),
            ParsedSensor(
                Symbol("WindSpeed_120m_SE_avg [m/s]"),
                "",
                "WindSpeed",
                "SE",
                120.0,
                "avg",
                "m/s",
                originalColumnNames=Symbol("Ch7_Anem_120m_SE_Avg")
            )
        ]

        df_result, sensors_result = transform_columns!(df, sensors)

        # Should have merged into one column
        @test "WindSpeed_120m_SE_avg [m/s]" in names(df_result)
        @test "Ch2_Anem_120m_SE_Avg" ∉ names(df_result)
        @test "Ch7_Anem_120m_SE_Avg" ∉ names(df_result)

        # Should have merged sensor metadata
        @test length(sensors_result) == 1
        @test length(sensors_result[1].originalColumnNames) == 2
        @test Symbol("Ch2_Anem_120m_SE_Avg") in sensors_result[1].originalColumnNames
        @test Symbol("Ch7_Anem_120m_SE_Avg") in sensors_result[1].originalColumnNames

        # Data should be merged (no missing in result)
        @test count(!ismissing, df_result[:, Symbol("WindSpeed_120m_SE_avg [m/s]")]) == 200
    end

    @testset "normalize_timestamp!" begin
        df = DataFrame(
            Timestamp = [DateTime(2024,1,1,0,0,0), DateTime(2024,1,1,0,10,0)],
            data = [1.0, 2.0]
        )

        normalize_timestamp!(df, "Timestamp")

        @test "timestamp" in names(df)
        @test "Timestamp" ∉ names(df)
        @test eltype(df.timestamp) == DateTime
    end
end
