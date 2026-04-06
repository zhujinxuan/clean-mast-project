"""Tests for wind temporal analyzer service.

Tests cover daily, monthly, and combined monthly-daily pattern analysis,
including aggregation logic and power calculations.
"""

from datetime import datetime, timedelta

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.services.calculators.wind_temporal_analyzer import (
    WindTemporalAnalyzer,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestDailyPattern:
    """Tests for daily 24-hour pattern analysis."""

    @pytest.fixture
    def analyzer(self) -> WindTemporalAnalyzer:
        """Create a WindTemporalAnalyzer instance."""
        return WindTemporalAnalyzer()

    @pytest.fixture
    def sample_input(self) -> SingleMastAnalysisInput:
        """Create sample input data with 24-hour pattern."""
        # Create 3 days of hourly data with clear daily pattern
        timestamps = [
            datetime(2023, 1, 1) + timedelta(hours=i) for i in range(72)
        ]  # 3 days
        
        # Wind speed varies by hour: higher during day (12-18), lower at night
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0, 120.0], air_density=1.225)

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

    def test_24_hours(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify result has exactly 24 rows (one per hour)."""
        result = analyzer.analyze_daily_pattern(sample_input)

        # Should have 24 hours x 2 heights = 48 rows
        assert len(result.data) == 48

        # Check we have all 24 hours for each height
        hours_100m = sorted(
            result.data.filter(pl.col("height") == 100.0)["hour"].to_list()
        )
        hours_120m = sorted(
            result.data.filter(pl.col("height") == 120.0)["hour"].to_list()
        )
        assert hours_100m == list(range(24))
        assert hours_120m == list(range(24))

    def test_hourly_aggregation(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify correct aggregation logic across multiple days."""
        result = analyzer.analyze_daily_pattern(sample_input)

        # For 100m height: day hours (6-18) should have mean_speed = 8.0,
        # night hours should have mean_speed = 5.0
        hour_12_data = result.data.filter(
            (pl.col("height") == 100.0) & (pl.col("hour") == 12)
        )
        assert len(hour_12_data) == 1
        # During day hours, wind speed is 8.0
        assert pytest.approx(hour_12_data["mean_speed"][0], rel=0.001) == 8.0

        hour_0_data = result.data.filter(
            (pl.col("height") == 100.0) & (pl.col("hour") == 0)
        )
        assert len(hour_0_data) == 1
        # During night hours, wind speed is 5.0
        assert pytest.approx(hour_0_data["mean_speed"][0], rel=0.001) == 5.0

    def test_power_calculation(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify 0.5 * ρ * v³ formula is applied correctly."""
        result = analyzer.analyze_daily_pattern(sample_input)

        # Check a specific hour and calculate expected power
        hour_12_100m = result.data.filter(
            (pl.col("height") == 100.0) & (pl.col("hour") == 12)
        )
        mean_speed = hour_12_100m["mean_speed"][0]
        expected_power = 0.5 * 1.225 * (mean_speed ** 3)

        assert pytest.approx(hour_12_100m["mean_power"][0], rel=0.001) == expected_power

    def test_schema_validation(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify result data conforms to TemporalPatternSchema."""
        result = analyzer.analyze_daily_pattern(sample_input)

        assert result.schema == TemporalPatternSchema
        
        # Verify all expected columns exist
        expected_columns = {
            "timestamp", "hour", "month", "wind_speed", "wind_power",
            "height", "mean_speed", "mean_power", "interpolation_marker"
        }
        assert set(result.data.columns) == expected_columns

    def test_metadata_contains_mast_name(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify metadata contains mast name."""
        result = analyzer.analyze_daily_pattern(sample_input)

        assert result.metadata.mast_name == "TestMast"

    def test_metadata_contains_time_range(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify metadata contains time range."""
        result = analyzer.analyze_daily_pattern(sample_input)

        assert "2023-01-01" in result.metadata.time_range
        assert "to" in result.metadata.time_range


class TestMonthlyPattern:
    """Tests for monthly 12-month pattern analysis."""

    @pytest.fixture
    def analyzer(self) -> WindTemporalAnalyzer:
        """Create a WindTemporalAnalyzer instance."""
        return WindTemporalAnalyzer()

    @pytest.fixture
    def sample_input(self) -> SingleMastAnalysisInput:
        """Create sample input data with seasonal pattern."""
        # Create one year of daily data
        timestamps = [
            datetime(2023, 1, 1) + timedelta(days=i) for i in range(365)
        ]
        
        # Wind speed varies by month: higher in winter (months 12, 1, 2)
        ws_100m = []
        ws_120m = []
        for ts in timestamps:
            month = ts.month
            # Winter months (12, 1, 2) have higher wind
            if month in [12, 1, 2]:
                ws_100m.append(10.0)
                ws_120m.append(12.0)
            # Summer months (6, 7, 8) have lower wind
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0, 120.0], air_density=1.225)

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

    def test_12_months(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify result has exactly 12 rows (one per month)."""
        result = analyzer.analyze_monthly_pattern(sample_input)

        # Should have 12 months x 2 heights = 24 rows
        assert len(result.data) == 24

        # Check we have all 12 months for each height
        months_100m = sorted(
            result.data.filter(pl.col("height") == 100.0)["month"].to_list()
        )
        months_120m = sorted(
            result.data.filter(pl.col("height") == 120.0)["month"].to_list()
        )
        assert months_100m == list(range(1, 13))
        assert months_120m == list(range(1, 13))

    def test_monthly_aggregation(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify correct seasonal aggregation."""
        result = analyzer.analyze_monthly_pattern(sample_input)

        # Winter months (Jan=1, Dec=12) should have higher wind
        jan_data = result.data.filter(
            (pl.col("height") == 100.0) & (pl.col("month") == 1)
        )
        assert pytest.approx(jan_data["mean_speed"][0], rel=0.001) == 10.0

        # Summer month (July=7) should have lower wind
        jul_data = result.data.filter(
            (pl.col("height") == 100.0) & (pl.col("month") == 7)
        )
        assert pytest.approx(jul_data["mean_speed"][0], rel=0.001) == 5.0


class TestMonthlyDailyPattern:
    """Tests for combined monthly-daily pattern analysis."""

    @pytest.fixture
    def analyzer(self) -> WindTemporalAnalyzer:
        """Create a WindTemporalAnalyzer instance."""
        return WindTemporalAnalyzer()

    @pytest.fixture
    def sample_input(self) -> SingleMastAnalysisInput:
        """Create sample input data with monthly-daily pattern."""
        # Create data for 3 months, every hour
        timestamps = []
        for month in [1, 6, 12]:  # Winter, Summer, Winter
            days_in_month = 31 if month in [1, 12] else 30
            for day in range(1, days_in_month + 1):
                for hour in range(24):
                    timestamps.append(datetime(2023, month, day, hour))

        # Wind speed varies by both month and hour
        ws_100m = []
        for ts in timestamps:
            month_factor = 1.5 if ts.month in [12, 1] else 1.0  # Higher in winter
            hour_factor = 1.2 if 6 <= ts.hour <= 18 else 0.8  # Higher during day
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0, 120.0], air_density=1.225)

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

    def test_288_combinations(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify 24 hours x 3 months (in data) x 2 heights = 144 data points."""
        result = analyzer.analyze_monthly_daily(sample_input)

        # We have 3 months in the data, not 12, so 24 x 3 x 2 = 144
        # But since we only have months 1, 6, 12 present:
        assert len(result.data) == 24 * 3 * 2  # 144 rows

    def test_grid_structure(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify correct hour/month combinations."""
        result = analyzer.analyze_monthly_daily(sample_input)

        # Check all hours present for each month
        for month in [1, 6, 12]:
            for height in [100.0, 120.0]:
                month_height_data = result.data.filter(
                    (pl.col("month") == month) & (pl.col("height") == height)
                )
                hours = sorted(month_height_data["hour"].to_list())
                assert len(hours) == 24
                assert hours == list(range(24))

    def test_combined_aggregation(self, analyzer: WindTemporalAnalyzer, sample_input: SingleMastAnalysisInput) -> None:
        """Verify aggregation considers both month and hour."""
        result = analyzer.analyze_monthly_daily(sample_input)

        # January midday should have highest wind
        jan_noon = result.data.filter(
            (pl.col("month") == 1) & (pl.col("hour") == 12) & (pl.col("height") == 100.0)
        )
        # 5.0 * 1.5 * 1.2 = 9.0
        assert pytest.approx(jan_noon["mean_speed"][0], rel=0.001) == 9.0

        # July midnight should have lowest wind
        jul_midnight = result.data.filter(
            (pl.col("month") == 6) & (pl.col("hour") == 0) & (pl.col("height") == 100.0)
        )
        # 5.0 * 1.0 * 0.8 = 4.0
        assert pytest.approx(jul_midnight["mean_speed"][0], rel=0.001) == 4.0


class TestWindTemporalAnalyzer:
    """Tests for WindTemporalAnalyzer edge cases and general functionality."""

    @pytest.fixture
    def analyzer(self) -> WindTemporalAnalyzer:
        """Create a WindTemporalAnalyzer instance."""
        return WindTemporalAnalyzer()

    def test_no_wind_speed_sensors(self, analyzer: WindTemporalAnalyzer) -> None:
        """Handles empty sensor list gracefully."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "temperature": [20.0] * 24,
        })

        sensors = [
            SensorColumn(
                column_name="temperature",
                sensor_type="Temperature",  # Not WindSpeed
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="degC",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[10.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        result = analyzer.analyze_daily_pattern(input_data)

        # Should return empty result
        assert len(result.data) == 0
        assert "No wind speed sensors found" in result.metadata.time_range

    def test_multiple_heights(self, analyzer: WindTemporalAnalyzer) -> None:
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[80.0, 100.0, 120.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        result = analyzer.analyze_daily_pattern(input_data)

        # Should have 24 hours x 3 heights = 72 rows
        assert len(result.data) == 72

        # Check all heights are present
        heights = sorted(result.data["height"].unique().to_list())
        assert heights == [80.0, 100.0, 120.0]

        # Each height should have correct mean speed
        for height, expected_speed in [(80.0, 8.0), (100.0, 9.0), (120.0, 10.0)]:
            height_data = result.data.filter(pl.col("height") == height)
            assert pytest.approx(height_data["mean_speed"].mean(), rel=0.001) == expected_speed

    def test_missing_column_handling(self, analyzer: WindTemporalAnalyzer) -> None:
        """Skip sensors whose columns don't exist in DataFrame."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": [9.0] * 24,
            # WS_120m_avg column is missing
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
                column_name="WS_120m_avg",  # This column doesn't exist
                sensor_type="WindSpeed",
                sensor_direction="",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0, 120.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        result = analyzer.analyze_daily_pattern(input_data)

        # Should only have data for the existing column (100m)
        assert len(result.data) == 24  # 24 hours x 1 height
        heights = result.data["height"].unique().to_list()
        assert heights == [100.0]

    def test_auto_calculate_air_density(self, analyzer: WindTemporalAnalyzer) -> None:
        """Auto-calculate air density when not provided."""
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        # No air density provided
        parameters = AnalysisParameters(heights=[100.0], air_density=None)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        # Should not raise exception
        result = analyzer.analyze_daily_pattern(input_data)
        
        # Result should have power calculated with some air density
        assert len(result.data) == 24
        assert all(p is not None for p in result.data["mean_power"].to_list())

    def test_result_has_created_at(self, analyzer: WindTemporalAnalyzer) -> None:
        """Verify result metadata includes created_at timestamp."""
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        result = analyzer.analyze_daily_pattern(input_data)

        assert result.metadata.created_at is not None
        # Should be recent
        from datetime import datetime as dt
        assert (dt.now() - result.metadata.created_at).total_seconds() < 60

    def test_empty_dataframe_result(self, analyzer: WindTemporalAnalyzer) -> None:
        """Test empty DataFrame result has correct schema."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "temperature": [20.0] * 24,  # No wind speed data
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[10.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

        result = analyzer.analyze_daily_pattern(input_data)

        # Empty result should still have correct columns
        assert set(result.data.columns) == {
            "timestamp", "hour", "month", "wind_speed", "wind_power",
            "height", "mean_speed", "mean_power", "interpolation_marker"
        }
