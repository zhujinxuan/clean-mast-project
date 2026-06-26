"""Tests for wind temporal compute functions in the reporting domain.

Tests cover daily, monthly, and combined monthly-daily pattern analysis,
including aggregation logic and power calculations.
"""

from datetime import datetime, timedelta

import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.wind_temporal.compute import (
    analyze_daily_pattern,
    analyze_monthly_daily_pattern,
    analyze_monthly_pattern,
)


class TestDailyPattern:
    """Tests for daily 24-hour pattern analysis."""

    @pytest.fixture
    def sample_time_series(self) -> TimeSeriesData:
        """Create sample time series data with 24-hour pattern."""
        timestamps = [
            datetime(2023, 1, 1) + timedelta(hours=i) for i in range(72)
        ]

        ws_100m = [
            5.0 + 3.0 * (1 if 6 <= (i % 24) <= 18 else 0) for i in range(72)
        ]
        ws_120m = [
            6.0 + 3.5 * (1 if 6 <= (i % 24) <= 18 else 0) for i in range(72)
        ]

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": ws_100m,
            "WS_120m_avg": ws_120m,
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
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        return TimeSeriesData(df=df, sensors=sensors)

    def test_24_hours(self, sample_time_series: TimeSeriesData) -> None:
        """Verify result has exactly 24 rows per height."""
        result = analyze_daily_pattern(sample_time_series.df, sample_time_series.sensors)

        assert len(result) == 48

        hours_100m = sorted(
            result.filter(pl.col("height") == 100.0)["hour"].to_list()
        )
        hours_120m = sorted(
            result.filter(pl.col("height") == 120.0)["hour"].to_list()
        )
        assert hours_100m == list(range(24))
        assert hours_120m == list(range(24))

    def test_hourly_aggregation(self, sample_time_series: TimeSeriesData) -> None:
        """Verify correct aggregation logic across multiple days."""
        result = analyze_daily_pattern(sample_time_series.df, sample_time_series.sensors)

        hour_12_data = result.filter(
            (pl.col("height") == 100.0) & (pl.col("hour") == 12)
        )
        assert len(hour_12_data) == 1
        assert pytest.approx(hour_12_data["mean_speed"][0], rel=0.001) == 8.0

        hour_0_data = result.filter(
            (pl.col("height") == 100.0) & (pl.col("hour") == 0)
        )
        assert len(hour_0_data) == 1
        assert pytest.approx(hour_0_data["mean_speed"][0], rel=0.001) == 5.0

    def test_power_calculation(self, sample_time_series: TimeSeriesData) -> None:
        """Verify 0.5 * ρ * v³ formula is applied correctly."""
        result = analyze_daily_pattern(sample_time_series.df, sample_time_series.sensors)

        hour_12_100m = result.filter(
            (pl.col("height") == 100.0) & (pl.col("hour") == 12)
        )
        mean_speed = hour_12_100m["mean_speed"][0]
        expected_power = 0.5 * 1.225 * (mean_speed ** 3)

        assert pytest.approx(hour_12_100m["mean_power"][0], rel=0.001) == expected_power

    def test_schema_columns(self, sample_time_series: TimeSeriesData) -> None:
        """Verify result data has expected columns."""
        result = analyze_daily_pattern(sample_time_series.df, sample_time_series.sensors)

        expected_columns = {
            "timestamp", "hour", "month", "wind_speed", "wind_power",
            "height", "mean_speed", "mean_power", "interpolation_marker"
        }
        assert set(result.columns) == expected_columns


class TestMonthlyPattern:
    """Tests for monthly 12-month pattern analysis."""

    @pytest.fixture
    def sample_time_series(self) -> TimeSeriesData:
        """Create sample time series data with seasonal pattern."""
        timestamps = [
            datetime(2023, 1, 1) + timedelta(days=i) for i in range(365)
        ]

        ws_100m = []
        ws_120m = []
        for ts in timestamps:
            month = ts.month
            if month in [12, 1, 2]:
                ws_100m.append(10.0)
                ws_120m.append(12.0)
            elif month in [6, 7, 8]:
                ws_100m.append(5.0)
                ws_120m.append(6.0)
            else:
                ws_100m.append(7.5)
                ws_120m.append(9.0)

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": ws_100m,
            "WS_120m_avg": ws_120m,
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
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        return TimeSeriesData(df=df, sensors=sensors)

    def test_12_months(self, sample_time_series: TimeSeriesData) -> None:
        """Verify result has exactly 12 rows per height."""
        result = analyze_monthly_pattern(sample_time_series.df, sample_time_series.sensors)

        assert len(result) == 24

        months_100m = sorted(
            result.filter(pl.col("height") == 100.0)["month"].to_list()
        )
        months_120m = sorted(
            result.filter(pl.col("height") == 120.0)["month"].to_list()
        )
        assert months_100m == list(range(1, 13))
        assert months_120m == list(range(1, 13))

    def test_monthly_aggregation(self, sample_time_series: TimeSeriesData) -> None:
        """Verify correct seasonal aggregation."""
        result = analyze_monthly_pattern(sample_time_series.df, sample_time_series.sensors)

        jan_data = result.filter(
            (pl.col("height") == 100.0) & (pl.col("month") == 1)
        )
        assert pytest.approx(jan_data["mean_speed"][0], rel=0.001) == 10.0

        jul_data = result.filter(
            (pl.col("height") == 100.0) & (pl.col("month") == 7)
        )
        assert pytest.approx(jul_data["mean_speed"][0], rel=0.001) == 5.0


class TestMonthlyDailyPattern:
    """Tests for combined monthly-daily pattern analysis."""

    @pytest.fixture
    def sample_time_series(self) -> TimeSeriesData:
        """Create sample time series data with monthly-daily pattern."""
        timestamps = []
        for month in [1, 6, 12]:
            days_in_month = 31 if month in [1, 12] else 30
            for day in range(1, days_in_month + 1):
                for hour in range(24):
                    timestamps.append(datetime(2023, month, day, hour))

        ws_100m = []
        for ts in timestamps:
            month_factor = 1.5 if ts.month in [12, 1] else 1.0
            hour_factor = 1.2 if 6 <= ts.hour <= 18 else 0.8
            ws_100m.append(5.0 * month_factor * hour_factor)

        ws_120m = [speed * 1.2 for speed in ws_100m]

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": ws_100m,
            "WS_120m_avg": ws_120m,
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
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        return TimeSeriesData(df=df, sensors=sensors)

    def test_288_combinations(self, sample_time_series: TimeSeriesData) -> None:
        """Verify 24 hours x 3 months x 2 heights = 144 data points."""
        result = analyze_monthly_daily_pattern(sample_time_series.df, sample_time_series.sensors)

        assert len(result) == 24 * 3 * 2

    def test_grid_structure(self, sample_time_series: TimeSeriesData) -> None:
        """Verify correct hour/month combinations."""
        result = analyze_monthly_daily_pattern(sample_time_series.df, sample_time_series.sensors)

        for month in [1, 6, 12]:
            for height in [100.0, 120.0]:
                month_height_data = result.filter(
                    (pl.col("month") == month) & (pl.col("height") == height)
                )
                hours = sorted(month_height_data["hour"].to_list())
                assert len(hours) == 24
                assert hours == list(range(24))

    def test_combined_aggregation(self, sample_time_series: TimeSeriesData) -> None:
        """Verify aggregation considers both month and hour."""
        result = analyze_monthly_daily_pattern(sample_time_series.df, sample_time_series.sensors)

        jan_noon = result.filter(
            (pl.col("month") == 1) & (pl.col("hour") == 12) & (pl.col("height") == 100.0)
        )
        assert pytest.approx(jan_noon["mean_speed"][0], rel=0.001) == 9.0

        jul_midnight = result.filter(
            (pl.col("month") == 6) & (pl.col("hour") == 0) & (pl.col("height") == 100.0)
        )
        assert pytest.approx(jul_midnight["mean_speed"][0], rel=0.001) == 4.0


class TestWindTemporalCompute:
    """Tests for wind temporal compute edge cases and general functionality."""

    def test_no_wind_speed_sensors(self) -> None:
        """Handles empty sensor list gracefully."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]

        df = pl.DataFrame({
            "timestamp": timestamps,
            "temperature": [20.0] * 24,
        })

        sensors = [
            SensorColumn(
                column_name="temperature",
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="degC",
            ),
        ]

        result = analyze_daily_pattern(df, sensors)

        assert len(result) == 0
        assert set(result.columns) == {
            "timestamp", "hour", "month", "wind_speed", "wind_power",
            "height", "mean_speed", "mean_power", "interpolation_marker"
        }

    def test_multiple_heights(self) -> None:
        """Correctly processes multiple sensor heights."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_80m_avg": [8.0] * 24,
            "WS_100m_avg": [9.0] * 24,
            "WS_120m_avg": [10.0] * 24,
        })

        sensors = [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        result = analyze_daily_pattern(df, sensors)

        assert len(result) == 72

        heights = sorted(result["height"].unique().to_list())
        assert heights == [80.0, 100.0, 120.0]

        for height, expected_speed in [(80.0, 8.0), (100.0, 9.0), (120.0, 10.0)]:
            height_data = result.filter(pl.col("height") == height)
            assert pytest.approx(height_data["mean_speed"].mean(), rel=0.001) == expected_speed

    def test_missing_column_handling(self) -> None:
        """Skip sensors whose columns don't exist in DataFrame."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": [9.0] * 24,
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
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        result = analyze_daily_pattern(df, sensors)

        assert len(result) == 24
        heights = result["height"].unique().to_list()
        assert heights == [100.0]

    def test_custom_air_density(self) -> None:
        """Use provided air density for power calculations."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": [10.0] * 24,
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

        result = analyze_daily_pattern(df, sensors, air_density=1.15)

        assert len(result) == 24
        expected_power = 0.5 * 1.15 * (10.0 ** 3)
        assert pytest.approx(result["mean_power"][0], rel=0.001) == expected_power

    def test_empty_dataframe_result(self) -> None:
        """Test empty DataFrame result has correct schema."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]

        df = pl.DataFrame({
            "timestamp": timestamps,
            "temperature": [20.0] * 24,
        })

        sensors = [
            SensorColumn(
                column_name="temperature",
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="degC",
            ),
        ]

        result = analyze_daily_pattern(df, sensors)

        assert set(result.columns) == {
            "timestamp", "hour", "month", "wind_speed", "wind_power",
            "height", "mean_speed", "mean_power", "interpolation_marker"
        }
