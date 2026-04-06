"""Tests for monthly power calculator service."""

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.services.calculators.monthly_power_calculator import (
    MonthlyPowerCalculator,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    MonthlyWindPowerSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestMonthlyPowerCalculator:
    """Tests for MonthlyPowerCalculator."""

    def _create_test_input(
        self,
        wind_speed_values: list[float],
        timestamps: list[str] | None = None,
        height: float = 100.0,
        air_density: float | None = None,
    ) -> SingleMastAnalysisInput:
        if timestamps is None:
            timestamps = [f"2024-{i:02d}-15T00:00:00" for i in range(1, 13)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": wind_speed_values,
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=height,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[height], air_density=air_density)

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

    def _create_test_input_multi_height(
        self,
        ws_100m: list[float],
        ws_80m: list[float],
        timestamps: list[str] | None = None,
        air_density: float | None = None,
    ) -> SingleMastAnalysisInput:
        if timestamps is None:
            timestamps = [f"2024-{i:02d}-15T00:00:00" for i in range(1, 13)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": ws_100m,
            "WS_80m_avg": ws_80m,
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0, 80.0], air_density=air_density)

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

    def test_calculate_basic(self) -> None:
        wind_speeds = [5.0] * 12
        input_data = self._create_test_input(wind_speeds, air_density=1.225)

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        assert result.schema == MonthlyWindPowerSchema
        assert result.metadata.mast_name == "TestMast"
        assert len(result.data) == 12

        expected_columns = {
            "month",
            "height",
            "interpolation_marker",
            "wind_power_density",
            "air_density_used",
        }
        assert set(result.data.columns) == expected_columns

    def test_power_density_calculation(self) -> None:
        wind_speed = 10.0
        air_density = 1.225
        timestamps = ["2024-01-15T00:00:00"]
        input_data = self._create_test_input([wind_speed], timestamps, air_density=air_density)

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        expected_power = 0.5 * air_density * (wind_speed ** 3)
        actual_power = result.data["wind_power_density"][0]

        assert pytest.approx(actual_power, rel=0.001) == expected_power

    def test_power_density_with_different_wind_speeds(self) -> None:
        air_density = 1.225
        # Use different months so each wind speed is in its own monthly group
        wind_speeds = [5.0, 10.0, 15.0]
        timestamps = ["2024-01-15T00:00:00", "2024-02-15T00:00:00", "2024-03-15T00:00:00"]
        input_data = self._create_test_input(wind_speeds, timestamps, air_density=air_density)

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        expected_powers = [0.5 * air_density * (ws ** 3) for ws in wind_speeds]
        # Sort by month to ensure correct order
        sorted_data = result.data.sort("month")
        actual_powers = sorted_data["wind_power_density"].to_list()

        for actual, expected in zip(actual_powers, expected_powers):
            assert pytest.approx(actual, rel=0.001) == expected

    def test_calculate_multi_height(self) -> None:
        ws_100m = [10.0] * 12
        ws_80m = [8.0] * 12
        air_density = 1.225
        input_data = self._create_test_input_multi_height(
            ws_100m, ws_80m, air_density=air_density
        )

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        assert len(result.data) == 24

        heights = result.data["height"].unique().to_list()
        assert sorted(heights) == [80.0, 100.0]

        data_100m = result.data.filter(pl.col("height") == 100.0)
        expected_power_100m = 0.5 * air_density * (10.0 ** 3)
        assert pytest.approx(data_100m["wind_power_density"][0], rel=0.001) == expected_power_100m

    def test_air_density_recorded_in_result(self) -> None:
        air_density = 1.189
        timestamps = ["2024-01-15T00:00:00"]
        input_data = self._create_test_input([5.0], timestamps, air_density=air_density)

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        recorded_density = result.data["air_density_used"][0]
        assert recorded_density == air_density

    def test_ignores_non_wind_speed_sensors(self) -> None:
        timestamps = [f"2024-{i:02d}-15T00:00:00" for i in range(1, 4)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": [5.0, 6.0, 7.0],
            "WD_100m_avg": [0.0, 90.0, 180.0],
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        assert len(result.data) == 3
        assert all(h == 100.0 for h in result.data["height"].to_list())

    def test_preserves_interpolation_marker(self) -> None:
        timestamps = [f"2024-{i:02d}-15T00:00:00" for i in range(1, 4)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg_fill:extrapolated": [5.0, 6.0, 7.0],
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg_fill:extrapolated",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        markers = result.data["interpolation_marker"].to_list()
        assert all(m == "外推" for m in markers)

    def test_metadata_contains_time_range(self) -> None:
        timestamps = [
            "2024-01-01T00:00:00",
            "2024-06-15T00:00:00",
            "2024-12-31T00:00:00",
        ]
        input_data = self._create_test_input([5.0, 6.0, 7.0], timestamps, air_density=1.225)

        calculator = MonthlyPowerCalculator()
        result = calculator.calculate(input_data)

        assert "2024-01-01" in result.metadata.time_range
        assert "2024-12-31" in result.metadata.time_range
        assert "to" in result.metadata.time_range

    def test_empty_dataframe(self) -> None:
        df = pl.DataFrame({
            "timestamp": pl.Series([], dtype=pl.Datetime),
            "WS_100m_avg": pl.Series([], dtype=pl.Float64),
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        calculator = MonthlyPowerCalculator()

        # Empty DataFrame should raise SchemaError during validation
        with pytest.raises(Exception):
            calculator.calculate(input_data)
