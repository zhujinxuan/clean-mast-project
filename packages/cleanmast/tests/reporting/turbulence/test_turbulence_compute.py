"""Tests for turbulence intensity computation functions.

Adapted from assessment tests. Key changes:
- No TurbulenceCalculator class → test pure functions directly
- No AnalysisResult → DataFrame output directly
- No AnalysisParameters/SingleMastAnalysisInput → pass df + sensors
- No _get_time_range (removed utility)
"""

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn
from cleanmast.subdomains.reporting.subdomains.turbulence.compute import (
    MIN_SAMPLES,
    MIN_WIND_SPEED,
    TI_REP_Z,
    analyze_by_wind_speed,
    calculate_representative_ti,
    calculate_ti_series,
    classify_iec_category,
    compute_iec_ti,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_turbulence_data() -> pl.DataFrame:
    """Create sample turbulence data DataFrame with avg + sd sensors."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]

    base_speeds = 8.0 + 3.0 * np.sin(np.linspace(0, 4 * np.pi, 1000))
    noise = np.random.normal(0, 0.5, 1000)
    wind_speeds = np.maximum(base_speeds + noise, 0.5)

    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds,
        # SD = 15% of avg
        "WS_100m_sd": wind_speeds * 0.15,
    })


@pytest.fixture
def sample_turbulence_data_multi_height() -> pl.DataFrame:
    """Create sample turbulence data with multiple heights."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]

    base_100m = 8.0 + 3.0 * np.sin(np.linspace(0, 4 * np.pi, 1000))
    base_120m = 9.0 + 3.5 * np.sin(np.linspace(0, 4 * np.pi, 1000))
    noise_100m = np.random.normal(0, 0.5, 1000)
    noise_120m = np.random.normal(0, 0.6, 1000)

    wind_speeds_100m = np.maximum(base_100m + noise_100m, 0.5)
    wind_speeds_120m = np.maximum(base_120m + noise_120m, 0.5)

    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds_100m,
        "WS_100m_sd": wind_speeds_100m * 0.15,
        "WS_120m_avg": wind_speeds_120m,
        "WS_120m_sd": wind_speeds_120m * 0.15,
    })


@pytest.fixture
def sensors_single_height() -> list[SensorColumn]:
    return [
        SensorColumn(
            column_name="WS_100m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        ),
        SensorColumn(
            column_name="WS_100m_sd",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="sd",
            unit="m/s",
        ),
    ]


@pytest.fixture
def sensors_multi_height() -> list[SensorColumn]:
    return [
        SensorColumn(
            column_name="WS_100m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        ),
        SensorColumn(
            column_name="WS_100m_sd",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="sd",
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
        SensorColumn(
            column_name="WS_120m_sd",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=120.0,
            stat_type="sd",
            unit="m/s",
        ),
    ]


@pytest.fixture
def sensors_no_wind() -> list[SensorColumn]:
    return [
        SensorColumn(
            column_name="Temp_100m_avg",
            sensor_type="Temperature",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="C",
        ),
    ]


# =============================================================================
# Test Core TI Calculations
# =============================================================================


class TestCoreTICalculations:
    """Tests for core TI calculation functions."""

    def test_ti_series_calculation(self) -> None:
        """Test TI time series calculation."""
        np.random.seed(42)
        mean_ws = 8.0
        std_ws = 1.2
        wind_speeds = np.random.normal(mean_ws, std_ws, 1200)

        ti_series = calculate_ti_series(wind_speeds.tolist(), rolling_window=600)

        assert len(ti_series) == len(wind_speeds)

        middle_ti = ti_series[500]
        assert middle_ti is not None

        expected_ti = std_ws / mean_ws
        assert abs(middle_ti - expected_ti) < 0.1

    def test_ti_series_edge_values_none(self) -> None:
        """Test that edge values in TI series are None."""
        np.random.seed(42)
        wind_speeds = np.random.normal(8.0, 1.0, 1200)

        ti_series = calculate_ti_series(wind_speeds.tolist(), rolling_window=600)

        half_window = 300
        assert ti_series[0] is None
        assert ti_series[half_window - 1] is None
        assert ti_series[-1] is None
        assert ti_series[-half_window] is None

    def test_ti_series_insufficient_data(self) -> None:
        """Test TI series with insufficient data."""
        wind_speeds = [5.0] * 100

        ti_series = calculate_ti_series(wind_speeds, rolling_window=600)

        assert all(ti is None for ti in ti_series)

    def test_ti_series_minimum_wind_speed(self) -> None:
        """Test TI calculation clamps minimum wind speed."""
        wind_speeds = [0.1] * 1200

        ti_series = calculate_ti_series(wind_speeds, rolling_window=600)

        middle_ti = ti_series[600]
        assert middle_ti is not None
        assert middle_ti < 0.1

    def test_calculate_representative_ti(self) -> None:
        """Test representative TI (P90) calculation."""
        ti_values = [0.10, 0.12, 0.14, 0.16, 0.18] * 20

        rep_ti = calculate_representative_ti(ti_values)

        assert rep_ti is not None
        mean_ti = np.mean(ti_values)
        std_ti = np.std(ti_values, ddof=1)
        expected_rep = mean_ti + 1.28 * std_ti
        assert abs(rep_ti - expected_rep) < 0.01

    def test_calculate_representative_ti_with_none(self) -> None:
        """Test representative TI calculation with None values."""
        ti_values = [0.10, None, 0.12, None, 0.14] * 20

        rep_ti = calculate_representative_ti(ti_values)

        assert rep_ti is not None
        valid_ti = [ti for ti in ti_values if ti is not None]
        expected_rep = np.mean(valid_ti) + 1.28 * np.std(valid_ti, ddof=1)
        assert abs(rep_ti - expected_rep) < 0.01

    def test_calculate_representative_ti_insufficient_data(self) -> None:
        """Test representative TI returns None for insufficient data."""
        ti_values = [0.10, 0.12, 0.14, 0.16, 0.18]

        rep_ti = calculate_representative_ti(ti_values)

        assert rep_ti is None

    def test_calculate_iec_ti(self) -> None:
        """Test IEC reference TI calculation."""
        i_ref = 0.16
        wind_speed = 8.0

        iec_ti = compute_iec_ti(wind_speed, i_ref)

        assert iec_ti is not None
        expected = i_ref * (0.75 + 5.6 / wind_speed)
        assert abs(iec_ti - expected) < 0.001

    def test_calculate_iec_ti_zero_wind_speed(self) -> None:
        """Test IEC TI returns None for zero wind speed."""
        iec_ti = compute_iec_ti(0.0, 0.16)

        assert iec_ti is None

    def test_calculate_iec_ti_negative_wind_speed(self) -> None:
        """Test IEC TI returns None for negative wind speed."""
        iec_ti = compute_iec_ti(-5.0, 0.16)

        assert iec_ti is None


# =============================================================================
# Test IEC Category Classification
# =============================================================================


class TestIECCategoryClassification:
    """Tests for IEC category classification."""

    def test_classify_iec_category_high_turbulence(self) -> None:
        """Test classification for high turbulence (A+)."""
        rep_ti = 0.20
        wind_speed = 15.0

        category = classify_iec_category(rep_ti, wind_speed)

        assert category == "A+"

    def test_classify_iec_category_medium_turbulence(self) -> None:
        """Test classification for medium turbulence (B)."""
        rep_ti = 0.15
        wind_speed = 15.0

        category = classify_iec_category(rep_ti, wind_speed)

        assert category == "B"

    def test_classify_iec_category_low_turbulence(self) -> None:
        """Test classification for low turbulence (C)."""
        rep_ti = 0.10
        wind_speed = 15.0

        category = classify_iec_category(rep_ti, wind_speed)

        assert category == "C"

    def test_classify_iec_category_exactly_at_a_threshold(self) -> None:
        """Test classification uses strict > for thresholds."""
        rep_ti = 0.16 * (0.75 + 5.6 / 15.0)
        wind_speed = 15.0

        category = classify_iec_category(rep_ti, wind_speed)

        assert category == "A"

    def test_classify_iec_category_between_b_and_c(self) -> None:
        """Test classification returns B when rep_ti is above C but below B."""
        rep_ti = 0.14
        wind_speed = 15.0

        category = classify_iec_category(rep_ti, wind_speed)

        assert category == "B"

    def test_classify_iec_category_insufficient_data(self) -> None:
        """Test classification defaults to C for None representative TI."""
        category = classify_iec_category(None, 15.0)

        assert category == "C"

    def test_classify_iec_category_with_none_values(self) -> None:
        """Test classification handles None representative TI correctly."""
        category = classify_iec_category(None, 8.0)

        assert category == "C"


# =============================================================================
# Test Wind Speed Bin Analysis
# =============================================================================


class TestWindSpeedAnalysis:
    """Tests for wind speed bin turbulence analysis."""

    def test_analyze_by_wind_speed(
        self,
        sample_turbulence_data: pl.DataFrame,
        sensors_single_height: list[SensorColumn],
    ) -> None:
        """Test analysis by wind speed bins."""
        result = analyze_by_wind_speed(sample_turbulence_data, sensors_single_height)

        assert result is not None

        expected_columns = {
            "wind_speed_bin", "height", "interpolation_marker", "mean_ti",
            "std_ti", "representative_ti", "iec_category", "count",
        }
        assert set(result.columns) == expected_columns

        assert len(result) > 0

    def test_analyze_by_wind_speed_multiple_heights(
        self,
        sample_turbulence_data_multi_height: pl.DataFrame,
        sensors_multi_height: list[SensorColumn],
    ) -> None:
        """Test analysis with multiple heights."""
        result = analyze_by_wind_speed(
            sample_turbulence_data_multi_height, sensors_multi_height
        )

        assert result is not None
        assert len(result) > 0

        heights = result["height"].unique().to_list()
        assert 100.0 in heights
        assert 120.0 in heights

    def test_analyze_by_wind_speed_no_wind_sensors(
        self,
        sensors_no_wind: list[SensorColumn],
    ) -> None:
        """Test analysis with no wind speed sensors."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(100)],
            "Temp_100m_avg": [15.0] * 100,
        })

        result = analyze_by_wind_speed(df, sensors_no_wind)

        assert result is not None
        assert len(result) == 0

    def test_ti_values_in_valid_range(self) -> None:
        """Test that calculated TI values are in reasonable range."""
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(500)]
        wind_speeds = np.maximum(np.random.normal(8.0, 2.0, 500), 0.5)

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": wind_speeds,
            "WS_100m_sd": wind_speeds * 0.15,
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg", sensor_type="WindSpeed",
                sensor_direction="", height=100.0, stat_type="avg", unit="m/s",
            ),
            SensorColumn(
                column_name="WS_100m_sd", sensor_type="WindSpeed",
                sensor_direction="", height=100.0, stat_type="sd", unit="m/s",
            ),
        ]

        result = analyze_by_wind_speed(df, sensors)

        if len(result) > 0:
            mean_ti_values = result["mean_ti"].to_list()
            for ti in mean_ti_values:
                assert 0 <= ti < 0.5, f"TI value {ti} out of expected range"

    def test_iec_categories_are_valid(self) -> None:
        """Test that IEC categories are valid."""
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(500)]
        wind_speeds = np.maximum(np.random.normal(8.0, 2.0, 500), 0.5)

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": wind_speeds,
            "WS_100m_sd": wind_speeds * 0.15,
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg", sensor_type="WindSpeed",
                sensor_direction="", height=100.0, stat_type="avg", unit="m/s",
            ),
            SensorColumn(
                column_name="WS_100m_sd", sensor_type="WindSpeed",
                sensor_direction="", height=100.0, stat_type="sd", unit="m/s",
            ),
        ]

        result = analyze_by_wind_speed(df, sensors)

        valid_categories = {"A+", "A", "B", "C"}
        for row in result.iter_rows(named=True):
            assert row["iec_category"] in valid_categories


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_dataframe(self) -> None:
        """Test handling of empty DataFrame."""
        df = pl.DataFrame({
            "timestamp": pl.Series([], dtype=pl.Datetime),
            "WS_100m_avg": pl.Series([], dtype=pl.Float64),
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg", sensor_type="WindSpeed",
                sensor_direction="", height=100.0, stat_type="avg", unit="m/s",
            ),
        ]

        result = analyze_by_wind_speed(df, sensors)

        assert result is not None
        assert len(result) == 0

    def test_missing_column(self) -> None:
        """Test handling when sensor column doesn't exist in DataFrame."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(100)],
            "SomeOtherColumn": [5.0] * 100,
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg", sensor_type="WindSpeed",
                sensor_direction="", height=100.0, stat_type="avg", unit="m/s",
            ),
        ]

        result = analyze_by_wind_speed(df, sensors)

        assert result is not None
        # Should handle gracefully (skip missing column, return empty)

    def test_constants(self) -> None:
        """Test that module constants have expected values."""
        assert MIN_SAMPLES == 10
        assert TI_REP_Z == 1.28
        assert MIN_WIND_SPEED == 1.0

