"""Tests for wind rose calculator — reporting domain.

Ported from tests/assessment/wind_rose/test_wind_rose_calculator.py.
Uses pure function `calculate_wind_rose()` instead of the stateful WindRoseCalculator class.
Test logic, inputs, expected values, assertions preserved exactly.
"""

import polars as pl
import polars.exceptions
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.wind_rose.compute import (
    SECTOR_COUNT,
    SECTOR_NAMES,
    calculate_wind_rose,
)


class TestWindRoseCalculator:
    """Tests for calculate_wind_rose pure function."""

    def _create_test_input(
        self,
        wind_speeds: list[float],
        wind_directions: list[float],
        timestamps: list[str] | None = None,
        height: float = 100.0,
    ) -> TimeSeriesData:
        if timestamps is None:
            timestamps = [f"2024-01-{i:02d}T00:00:00" for i in range(1, len(wind_speeds) + 1)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": wind_speeds,
            "WD_100m_avg": wind_directions,
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
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="",
                height=height,
                stat_type="avg",
                unit="deg",
            ),
        ]

        return TimeSeriesData(df=df, sensors=sensors)

    def test_sector_names_constant(self) -> None:
        assert len(SECTOR_NAMES) == SECTOR_COUNT
        assert SECTOR_NAMES[0] == "N"
        assert SECTOR_NAMES[4] == "E"
        assert SECTOR_NAMES[8] == "S"
        assert SECTOR_NAMES[12] == "W"

    def test_calculate_basic(self) -> None:
        wind_speeds = [5.0] * 16
        wind_directions = [0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5,
                          180.0, 202.5, 225.0, 247.5, 270.0, 292.5, 315.0, 337.5]
        input_data = self._create_test_input(wind_speeds, wind_directions)

        result = calculate_wind_rose(input_data, air_density=1.225)

        assert len(result) == SECTOR_COUNT

        expected_columns = {
            "month",
            "month_name",
            "sector",
            "sector_name",
            "height",
            "interpolation_marker",
            "frequency",
            "wind_power_density",
            "energy_frequency",
        }
        assert set(result.columns) == expected_columns

    def test_sector_calculation(self) -> None:
        wind_speeds = [10.0] * 16
        wind_directions = [0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5,
                          180.0, 202.5, 225.0, 247.5, 270.0, 292.5, 315.0, 337.5]
        input_data = self._create_test_input(wind_speeds, wind_directions)

        result = calculate_wind_rose(input_data, air_density=1.225)

        sectors = result.sort("sector")["sector"].to_list()
        assert sectors == list(range(SECTOR_COUNT))

        sector_names = result.sort("sector")["sector_name"].to_list()
        assert sector_names == SECTOR_NAMES

    def test_frequency_calculation(self) -> None:
        wind_speeds = [5.0] * 4
        wind_directions = [0.0, 0.0, 90.0, 180.0]
        input_data = self._create_test_input(wind_speeds, wind_directions)

        result = calculate_wind_rose(input_data, air_density=1.225)

        north_sector = result.filter(pl.col("sector") == 0)
        assert len(north_sector) == 1
        assert north_sector["frequency"][0] == 0.5

        east_sector = result.filter(pl.col("sector") == 4)
        assert len(east_sector) == 1
        assert east_sector["frequency"][0] == 0.25

    def test_power_density_calculation(self) -> None:
        wind_speed = 10.0
        air_density = 1.225
        wind_speeds = [wind_speed]
        wind_directions = [0.0]
        input_data = self._create_test_input(wind_speeds, wind_directions)

        result = calculate_wind_rose(input_data, air_density=air_density)

        expected_power = 0.5 * air_density * (wind_speed ** 3)
        actual_power = result["wind_power_density"][0]

        assert pytest.approx(actual_power, rel=0.001) == expected_power

    def test_skips_missing_wind_direction(self) -> None:
        wind_speeds = [5.0, 6.0, 7.0]
        timestamps = [f"2024-01-{i:02d}T00:00:00" for i in range(1, 4)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": wind_speeds,
            "WS_80m_avg": [4.0, 5.0, 6.0],
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

        result = calculate_wind_rose(time_series, air_density=1.225)
        assert len(result) == 0

    def test_ignores_null_wind_direction(self) -> None:
        wind_speeds = [5.0, 6.0, 7.0]
        wind_directions = [0.0, None, 180.0]
        timestamps = [f"2024-01-{i:02d}T00:00:00" for i in range(1, 4)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": wind_speeds,
            "WD_100m_avg": wind_directions,
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

        result = calculate_wind_rose(time_series, air_density=1.225)

        assert len(result) == 2

        frequencies = result["frequency"].to_list()
        assert pytest.approx(sum(frequencies), rel=0.001) == 1.0

    def test_preserves_interpolation_marker(self) -> None:
        wind_speeds = [5.0]
        wind_directions = [0.0]
        timestamps = ["2024-01-01T00:00:00"]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg_fill:extrapolated": wind_speeds,
            "WD_100m_avg": wind_directions,
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

        result = calculate_wind_rose(time_series, air_density=1.225)

        markers = result["interpolation_marker"].to_list()
        assert all(m == "外推" for m in markers)

    def test_empty_dataframe(self) -> None:
        df = pl.DataFrame({
            "timestamp": pl.Series([], dtype=pl.Datetime),
            "WS_100m_avg": pl.Series([], dtype=pl.Float64),
            "WD_100m_avg": pl.Series([], dtype=pl.Float64),
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

        result = calculate_wind_rose(time_series, air_density=1.225)
        assert len(result) == 0

    def test_wind_direction_boundary_conditions(self) -> None:
        wind_speeds = [5.0, 5.0, 5.0]
        wind_directions = [0.0, 360.0, 720.0]
        input_data = self._create_test_input(wind_speeds, wind_directions)

        result = calculate_wind_rose(input_data, air_density=1.225)

        sectors = result.sort("sector")["sector"].to_list()
        assert 0 in sectors

    def test_frequencies_sum_to_one_per_month(self) -> None:
        import random
        random.seed(42)
        timestamps = []
        wind_speeds = []
        wind_directions = []
        for i in range(100):
            month = (i % 12) + 1
            day = (i % 28) + 1
            timestamps.append(f"2024-{month:02d}-{day:02d}T00:00:00")
            wind_speeds.append(5.0)
            wind_directions.append(random.uniform(0, 360))

        input_data = self._create_test_input(wind_speeds, wind_directions, timestamps)

        result = calculate_wind_rose(input_data, air_density=1.225)

        for month in range(1, 13):
            month_data = result.filter(pl.col("month") == month)
            if len(month_data) > 0:
                month_frequencies = month_data["frequency"].to_list()
                total = sum(month_frequencies)
                assert pytest.approx(total, rel=0.001) == 1.0

    def test_energy_frequency_sums_to_100_per_month_height(self) -> None:
        wind_speeds = [5.0] * 16
        wind_directions = [0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5,
                          180.0, 202.5, 225.0, 247.5, 270.0, 292.5, 315.0, 337.5]
        input_data = self._create_test_input(wind_speeds, wind_directions)

        result = calculate_wind_rose(input_data, air_density=1.225)

        for month in result["month"].unique():
            for height in result["height"].unique():
                group = result.filter((pl.col("month") == month) & (pl.col("height") == height))
                if len(group) > 0:
                    total = group["energy_frequency"].sum()
                    assert pytest.approx(total, abs=0.001) == 1.0

    def test_energy_frequency_zero_sum_guard(self) -> None:
        wind_speeds = [0.0, 0.0, 0.0, 0.0]
        wind_directions = [0.0, 90.0, 180.0, 270.0]
        input_data = self._create_test_input(wind_speeds, wind_directions)

        result = calculate_wind_rose(input_data, air_density=1.225)

        assert len(result) == 4
        for value in result["energy_frequency"].to_list():
            assert value == 0.0
