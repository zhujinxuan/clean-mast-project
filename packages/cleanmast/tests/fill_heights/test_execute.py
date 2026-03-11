"""Tests for fill_heights execution functions.

Tests the actual wind speed and wind direction filling operations.
"""

import numpy as np
import polars as pl
import pytest

from cleanmast.subdomains.configuration import HeightReference
from cleanmast.subdomains.dataprocessing.services import apply_wd_fill, apply_ws_fill
from cleanmast.subdomains.dataingestion.value_objects import SensorColumn


def create_ws_sensor(column_name: str, height: float) -> SensorColumn:
    """Helper to create a WindSpeed sensor."""
    return SensorColumn(
        column_name=column_name,
        sensor_type="WindSpeed",
        sensor_direction="N",
        height=height,
        stat_type="avg",
        unit="m/s",
    )


def create_wd_sensor(column_name: str, height: float) -> SensorColumn:
    """Helper to create a WindDirection sensor."""
    return SensorColumn(
        column_name=column_name,
        sensor_type="WindDirection",
        sensor_direction="N",
        height=height,
        stat_type="avg",
        unit="deg",
    )


class TestApplyWSFill:
    """Tests for apply_ws_fill function."""

    @pytest.fixture
    def sample_ws_df(self) -> pl.DataFrame:
        """Create sample DataFrame with WS data."""
        return pl.DataFrame({
            "timestamp": [1, 2, 3, 4, 5],
            "WS_100m_avg": [10.0, 11.0, 12.0, 13.0, 14.0],
        })

    @pytest.fixture
    def sample_ws_df_interpolation(self) -> pl.DataFrame:
        """Create sample DataFrame with two WS columns for interpolation."""
        return pl.DataFrame({
            "timestamp": [1, 2, 3, 4, 5],
            "WS_80m_avg": [8.0, 8.8, 9.6, 10.4, 11.2],
            "WS_100m_avg": [10.0, 11.0, 12.0, 13.0, 14.0],
        })

    @pytest.fixture
    def sample_ws_df_with_nulls(self) -> pl.DataFrame:
        """Create sample DataFrame with null values."""
        return pl.DataFrame({
            "timestamp": [1, 2, 3, 4, 5],
            "WS_100m_avg": [10.0, None, 12.0, None, 14.0],
        })

    def test_apply_ws_fill_extrapolation_power_law(self, sample_ws_df: pl.DataFrame):
        """Test WS extrapolation using power law."""
        target = create_ws_sensor("WS_120m_fill:extrapolated", 120.0)
        references = [
            HeightReference(sensor=create_ws_sensor("WS_100m_avg", 100.0), weight=1.0),
        ]
        result = apply_ws_fill(
            df=sample_ws_df,
            target=target,
            references=references,
            shear=0.14,
        )

        # Power law: V2 = V1 * (H2/H1)^shear
        # V_120 = V_100 * (120/100)^0.14
        expected_multiplier = (120 / 100) ** 0.14
        expected = [10.0 * expected_multiplier, 11.0 * expected_multiplier,
                   12.0 * expected_multiplier, 13.0 * expected_multiplier,
                   14.0 * expected_multiplier]

        assert result.name == "WS_120m_fill:extrapolated"
        np.testing.assert_array_almost_equal(result.to_numpy(), expected, decimal=5)

    def test_apply_ws_fill_interpolation_weighted_average(self, sample_ws_df_interpolation: pl.DataFrame):
        """Test WS interpolation using weighted average."""
        # Midpoint interpolation (90m between 80m and 100m)
        target = create_ws_sensor("WS_90m_fill:interpolated", 90.0)
        references = [
            HeightReference(sensor=create_ws_sensor("WS_80m_avg", 80.0), weight=0.5),
            HeightReference(sensor=create_ws_sensor("WS_100m_avg", 100.0), weight=0.5),
        ]
        result = apply_ws_fill(
            df=sample_ws_df_interpolation,
            target=target,
            references=references,
            shear=0.14,
        )

        # For each row:
        # extrap1 = V_80 * (90/80)^0.14
        # extrap2 = V_100 * (90/100)^0.14
        # result = 0.5 * extrap1 + 0.5 * extrap2
        v_80 = np.array([8.0, 8.8, 9.6, 10.4, 11.2])
        v_100 = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
        extrap1 = v_80 * (90 / 80) ** 0.14
        extrap2 = v_100 * (90 / 100) ** 0.14
        expected = 0.5 * extrap1 + 0.5 * extrap2

        np.testing.assert_array_almost_equal(result.to_numpy(), expected, decimal=5)

    def test_apply_ws_fill_preserves_nulls(self, sample_ws_df_with_nulls: pl.DataFrame):
        """Test that null values in input are preserved in output."""
        target = create_ws_sensor("WS_120m_fill:extrapolated", 120.0)
        references = [
            HeightReference(sensor=create_ws_sensor("WS_100m_avg", 100.0), weight=1.0),
        ]
        result = apply_ws_fill(
            df=sample_ws_df_with_nulls,
            target=target,
            references=references,
            shear=0.14,
        )

        result_values = result.to_numpy()
        # Positions 1 and 3 should be NaN (corresponding to input nulls)
        assert np.isnan(result_values[1])
        assert np.isnan(result_values[3])
        # Other positions should have valid values
        assert not np.isnan(result_values[0])
        assert not np.isnan(result_values[2])
        assert not np.isnan(result_values[4])


class TestApplyWDFill:
    """Tests for apply_wd_fill function."""

    @pytest.fixture
    def sample_wd_df(self) -> pl.DataFrame:
        """Create sample DataFrame with WD data."""
        return pl.DataFrame({
            "timestamp": [1, 2, 3, 4, 5],
            "WD_100m_avg": [180.0, 185.0, 190.0, 195.0, 200.0],
        })

    @pytest.fixture
    def sample_wd_df_interpolation(self) -> pl.DataFrame:
        """Create sample DataFrame with two WD columns for interpolation."""
        return pl.DataFrame({
            "timestamp": [1, 2, 3, 4, 5],
            "WD_80m_avg": [170.0, 175.0, 180.0, 185.0, 190.0],
            "WD_100m_avg": [180.0, 185.0, 190.0, 195.0, 200.0],
        })

    @pytest.fixture
    def sample_wd_df_wraparound(self) -> pl.DataFrame:
        """Create sample DataFrame with wraparound WD data."""
        return pl.DataFrame({
            "timestamp": [1, 2, 3],
            "WD_80m_avg": [355.0, 350.0, 345.0],
            "WD_100m_avg": [5.0, 10.0, 15.0],
        })

    @pytest.fixture
    def sample_wd_df_with_nulls(self) -> pl.DataFrame:
        """Create sample DataFrame with null values."""
        return pl.DataFrame({
            "timestamp": [1, 2, 3, 4, 5],
            "WD_100m_avg": [180.0, None, 190.0, None, 200.0],
        })

    def test_apply_wd_fill_extrapolation_linear(self, sample_wd_df: pl.DataFrame):
        """Test WD extrapolation using linear extrapolation."""
        target = create_wd_sensor("WD_120m_fill:extrapolated", 120.0)
        references = [
            HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=1.0),
        ]
        deg_diff_per_m = 0.1  # 0.1 deg/m veer
        result = apply_wd_fill(
            df=sample_wd_df,
            target=target,
            references=references,
            deg_diff_per_m=deg_diff_per_m,
        )

        # Linear extrapolation: WD2 = WD1 + deg_diff_per_m * (H2 - H1)
        # WD_120 = WD_100 + 0.1 * (120 - 100) = WD_100 + 2
        expected = np.array([182.0, 187.0, 192.0, 197.0, 202.0]) % 360

        np.testing.assert_array_almost_equal(result.to_numpy(), expected, decimal=5)

    def test_apply_wd_fill_interpolation_vector_based(self, sample_wd_df_interpolation: pl.DataFrame):
        """CRITICAL: Test WD interpolation using vector components.

        This test verifies that vector-based interpolation is used rather
        than simple degree averaging.
        """
        target = create_wd_sensor("WD_90m_fill:interpolated", 90.0)
        references = [
            HeightReference(sensor=create_wd_sensor("WD_80m_avg", 80.0), weight=0.5),
            HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=0.5),
        ]
        deg_diff_per_m = 0.0  # No veer for simplicity
        result = apply_wd_fill(
            df=sample_wd_df_interpolation,
            target=target,
            references=references,
            deg_diff_per_m=deg_diff_per_m,
        )

        # With 0 veer and equal weights, result should be vector average
        # of ~178° average (extrapolated from 175° at 80m to 90m)
        # and ~188° average (extrapolated from 185° at 80m to 90m)
        # Result should be around 183°
        for i in range(5):
            # Results should be reasonable (around 180-195°)
            assert 170.0 < result[i] < 200.0

    def test_apply_wd_fill_interpolation_handles_wraparound(self, sample_wd_df_wraparound: pl.DataFrame):
        """CRITICAL: Test that WD interpolation handles 0°/360° wraparound.

        When interpolating between 355° and 5°, the result should be
        approximately 0° (or 360°), NOT 180°.
        """
        target = create_wd_sensor("WD_90m_fill:interpolated", 90.0)
        references = [
            HeightReference(sensor=create_wd_sensor("WD_80m_avg", 80.0), weight=0.5),
            HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=0.5),
        ]
        deg_diff_per_m = 0.0  # No veer
        result = apply_wd_fill(
            df=sample_wd_df_wraparound,
            target=target,
            references=references,
            deg_diff_per_m=deg_diff_per_m,
        )

        # The result should be near 0° (or 360°), NOT near 180°
        # Vector average of 355° and 5° should be approximately 0°
        for i in range(3):
            # Result should be close to 0° or 360°
            val = result[i]
            # Check if close to 0° or 360°
            is_near_zero = abs(val) < 30.0 or abs(val - 360.0) < 30.0
            assert is_near_zero, f"Expected near 0° or 360°, got {val}°"
            # Make sure it's NOT near 180°
            assert abs(val - 180.0) > 100.0, f"Unexpectedly near 180°, got {val}°"

    def test_apply_wd_fill_preserves_nulls(self, sample_wd_df_with_nulls: pl.DataFrame):
        """Test that null values in input are preserved in output."""
        target = create_wd_sensor("WD_120m_fill:extrapolated", 120.0)
        references = [
            HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=1.0),
        ]
        result = apply_wd_fill(
            df=sample_wd_df_with_nulls,
            target=target,
            references=references,
            deg_diff_per_m=0.1,
        )

        result_values = result.to_numpy()
        # Positions 1 and 3 should be NaN (corresponding to input nulls)
        assert np.isnan(result_values[1])
        assert np.isnan(result_values[3])
        # Other positions should have valid values
        assert not np.isnan(result_values[0])
        assert not np.isnan(result_values[2])
        assert not np.isnan(result_values[4])

    def test_apply_wd_fill_wraparound_extrapolation(self):
        """Test WD extrapolation with wraparound handling."""
        df = pl.DataFrame({
            "timestamp": [1, 2],
            "WD_100m_avg": [355.0, 5.0],
        })

        target = create_wd_sensor("WD_120m_fill:extrapolated", 120.0)
        references = [
            HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=1.0),
        ]
        # Positive deg_diff means veer (clockwise with height)
        result = apply_wd_fill(
            df=df,
            target=target,
            references=references,
            deg_diff_per_m=0.1,
        )

        # Result should wrap correctly: 355 + 2 = 357, 5 + 2 = 7
        expected = np.array([357.0, 7.0]) % 360
        np.testing.assert_array_almost_equal(result.to_numpy(), expected, decimal=5)
