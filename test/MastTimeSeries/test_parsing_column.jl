# 文件：./test/MastTimeSeries/test_parsing_column.jl

using Test
using YAML
using DataFrames
using Dates
using CleanMastProject.Types.Utils
using CleanMastProject.CleanMastConfig
using CleanMastProject.Types.CleanMastConfig
using CleanMastProject.Types.SensorColumns: ParsedSensor
using CleanMastProject.SensorParser

@testset "MastTimeSeries Tests" begin
    @testset "Apply Multipliers and Rename" begin
        df = DataFrame(
            "timestamp" => [DateTime(2024,1,1)],
            "Ch1_Anem_80m_315_Avg_mps" => [5.0],
            "Ch2_Vane_80m_315_Avg_deg" => [180.0],
            "Ch3_Analog_80m_Avg_hPa" => [1013.25]
        )

        sensors = [
            ParsedSensor(
                Symbol("Ch1_WindSpeed_80m_315_avg_m/s"),
                "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
                "WindSpeed",
                "315",
                80.0,
                "avg",
                "m/s",
                multiplier=1.0,
                originalColumnName=Symbol("Ch1_Anem_80m_315_Avg_mps")
            ),
            ParsedSensor(
                Symbol("Ch2_WindDirection_80m_315_avg_deg"),
                "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
                "WindDirection",
                "315",
                80.0,
                "avg",
                "deg",
                multiplier=1.0,
                originalColumnName=Symbol("Ch2_Vane_80m_315_Avg_deg")
            ),
            ParsedSensor(
                Symbol("Ch3_Pressure_80m_avg_Pa"),
                "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}",
                "Pressure",
                "",
                80.0,
                "avg",
                "Pa",
                multiplier=100.0,
                originalColumnName=Symbol("Ch3_Analog_80m_Avg_hPa")
            )
        ]

        # Apply transformations
        df_transformed = rename_and_apply_multipliers!(df, sensors)
        
        # Check column renames
        @test !("Ch1_Anem_80m_315_Avg_mps" in names(df_transformed))
        @test !("Ch2_Vane_80m_315_Avg_deg" in names(df_transformed))
        @test !("Ch3_Analog_80m_Avg_hPa" in names(df_transformed))
        
        @test "Ch1_WindSpeed_80m_315_avg_m/s" in names(df_transformed)
        @test "Ch2_WindDirection_80m_315_avg_deg" in names(df_transformed)
        @test "Ch3_Pressure_80m_avg_Pa" in names(df_transformed)
        
        # Check values after multipliers
        @test df_transformed[1, "Ch1_WindSpeed_80m_315_avg_m/s"] == 5.0  # No change
        @test df_transformed[1, "Ch2_WindDirection_80m_315_avg_deg"] == 180.0  # No change
        @test df_transformed[1, "Ch3_Pressure_80m_avg_Pa"] ≈ 101325.0  # 1013.25 * 100
    end

    @testset "Warning on Missing Original Column" begin
        df = DataFrame(
            "timestamp" => [DateTime(2024,1,1)],
            "existing_col" => [1.0]
        )

        sensors = [
            ParsedSensor(
                Symbol("new_col"),
                "",
                "Test",
                "",
                10.0,
                "avg",
                "",
                multiplier=1.0,
                originalColumnName=Symbol("missing_col")
            )
        ]

        # Should issue a warning but not error
        @test_logs (:warn, "Original column missing_col not found in DataFrame") rename_and_apply_multipliers!(df, sensors)
    end
end
