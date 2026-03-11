"""Tests for monthly statistics calculator service."""

import polars as pl
import pytest

from cleanmast.subdomains.analysis.services.monthly_stats_calculator import (
    MonthlyStatsCalculator,
)
from cleanmast.subdomains.analysis.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.analysis.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.analysis.value_objects.schemas import MonthlyWindSchema
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestMonthlyStatsCalculator:
    """Tests for MonthlyStatsCalculator."""

    def _create_test_input(
        self,
        wind_speed_values: list[float],
        timestamps: list[str] | None = None,
        height: float = 100.0,
        mast_name: str = "TestMast",
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
        parameters = AnalysisParameters(heights=[height])

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name=mast_name,
        )

    def _create_test_input_multi_height(
        self,
        ws_100m: list[float],
        ws_80m: list[float],
        timestamps: list[str] | None = None,
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
        parameters = AnalysisParameters(heights=[100.0, 80.0])

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

    def test_calculate_basic(self) -> None:
        wind_speeds = [5.0] * 12
        input_data = self._create_test_input(wind_speeds)

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        assert result.schema == MonthlyWindSchema
        assert result.metadata.mast_name == "TestMast"
        assert len(result.data) == 12

        expected_columns = {
            "month",
            "height",
            "interpolation_marker",
            "wind_speed_mean",
            "wind_speed_max",
            "wind_speed_min",
        }
        assert set(result.data.columns) == expected_columns

    def test_calculate_with_varying_wind_speeds(self) -> None:
        wind_speeds = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0]
        input_data = self._create_test_input(wind_speeds)

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        assert len(result.data) == 12

        months = result.data["month"].to_list()
        assert months == list(range(1, 13))

        heights = result.data["height"].to_list()
        assert all(h == 100.0 for h in heights)

    def test_calculate_multi_height(self) -> None:
        ws_100m = [5.0] * 12
        ws_80m = [4.5] * 12
        input_data = self._create_test_input_multi_height(ws_100m, ws_80m)

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        assert len(result.data) == 24

        heights = result.data["height"].unique().to_list()
        assert sorted(heights) == [80.0, 100.0]

    def test_calculate_mean_values(self) -> None:
        wind_speeds = [5.0, 6.0, 7.0, 5.0, 6.0, 7.0, 5.0, 6.0, 7.0, 5.0, 6.0, 7.0]
        input_data = self._create_test_input(wind_speeds)

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        sorted_data = result.data.sort("month")
        means = sorted_data["wind_speed_mean"].to_list()

        assert means == wind_speeds

    def test_calculate_max_min_values(self) -> None:
        wind_speeds = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0]
        input_data = self._create_test_input(wind_speeds)

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        sorted_data = result.data.sort("month")
        means = sorted_data["wind_speed_mean"].to_list()
        maxs = sorted_data["wind_speed_max"].to_list()
        mins = sorted_data["wind_speed_min"].to_list()

        assert means == wind_speeds
        assert maxs == wind_speeds
        assert mins == wind_speeds

    def test_calculate_with_multiple_values_per_month(self) -> None:
        timestamps = []
        wind_speeds = []
        for month in range(1, 4):
            for day in range(1, 4):
                timestamps.append(f"2024-{month:02d}-{day:02d}T00:00:00")
                wind_speeds.append(float(month * 10 + day))

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": wind_speeds,
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
        parameters = AnalysisParameters(heights=[100.0])
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        assert len(result.data) == 3

        month_1 = result.data.filter(pl.col("month") == 1)
        assert len(month_1) == 1
        assert month_1["wind_speed_mean"][0] == 12.0
        assert month_1["wind_speed_max"][0] == 13.0
        assert month_1["wind_speed_min"][0] == 11.0

    def test_calculate_ignores_non_wind_speed_sensors(self) -> None:
        timestamps = [f"2024-{i:02d}-15T00:00:00" for i in range(1, 4)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": [5.0, 6.0, 7.0],
            "WD_100m_avg": [0.0, 90.0, 180.0],
            "Temp_10m_avg": [15.0, 16.0, 17.0],
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
            SensorColumn(
                column_name="Temp_10m_avg",
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="C",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0, 10.0])
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        assert len(result.data) == 3
        assert all(h == 100.0 for h in result.data["height"].to_list())

    def test_calculate_preserves_interpolation_marker(self) -> None:
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
        parameters = AnalysisParameters(heights=[100.0])
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        calculator = MonthlyStatsCalculator()
        result = calculator.calculate(input_data)

        markers = result.data["interpolation_marker"].to_list()
        assert all(m == "外推" for m in markers)

    def test_metadata_contains_time_range(self) -> None:
        timestamps = [
            "2024-01-01T00:00:00",
            "2024-06-15T00:00:00",
            "2024-12-31T00:00:00",
        ]
        wind_speeds = [5.0, 6.0, 7.0]
        input_data = self._create_test_input(wind_speeds, timestamps)

        calculator = MonthlyStatsCalculator()
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
        parameters = AnalysisParameters(heights=[100.0])
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        calculator = MonthlyStatsCalculator()

        # Empty DataFrame should raise SchemaError during validation
        with pytest.raises(Exception):
            calculator.calculate(input_data)
