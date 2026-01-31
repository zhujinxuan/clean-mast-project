"""Tests for wind shear calculation functions."""

import math
from datetime import datetime

import numpy as np
import polars as pl
import pytest

from cleanmast.extrapolate.shear import (
    calculate_shear_exponent,
    extrapolate_wind_direction,
    extrapolate_wind_speed,
    fit_shear_from_heights,
)


class TestExtrapolateWindSpeed:
    """Tests for extrapolate_wind_speed function."""

    def test_basic_extrapolation(self):
        """Test basic power law extrapolation."""
        # V2 = V1 * (H2/H1)^shear
        # With shear=0.14, H1=100, H2=160, V1=10
        # V2 = 10 * (160/100)^0.14 = 10 * 1.6^0.14 ≈ 10.68
        result = extrapolate_wind_speed(
            wind_speed=10.0,
            reference_height=100.0,
            target_height=160.0,
            shear=0.14,
        )

        expected = 10.0 * (160.0 / 100.0) ** 0.14
        assert abs(result - expected) < 0.001

    def test_same_height(self):
        """Test extrapolation to same height returns same speed."""
        result = extrapolate_wind_speed(
            wind_speed=10.0,
            reference_height=100.0,
            target_height=100.0,
            shear=0.14,
        )

        assert result == 10.0

    def test_zero_shear(self):
        """Test with zero shear (uniform wind profile)."""
        result = extrapolate_wind_speed(
            wind_speed=10.0,
            reference_height=100.0,
            target_height=200.0,
            shear=0.0,
        )

        assert result == 10.0

    def test_downward_extrapolation(self):
        """Test extrapolation to lower height."""
        result = extrapolate_wind_speed(
            wind_speed=10.0,
            reference_height=100.0,
            target_height=50.0,
            shear=0.14,
        )

        # Lower height should give lower speed with positive shear
        assert result < 10.0

    def test_array_input(self):
        """Test with numpy array input."""
        wind_speeds = np.array([8.0, 10.0, 12.0])
        results = extrapolate_wind_speed(
            wind_speed=wind_speeds,
            reference_height=100.0,
            target_height=160.0,
            shear=0.14,
        )

        assert len(results) == 3
        assert results[1] > results[0]  # Higher speed extrapolates to higher speed


class TestCalculateShearExponent:
    """Tests for calculate_shear_exponent function."""

    def test_calculate_from_two_heights(self):
        """Test calculating shear from two height measurements."""
        # If V2/V1 = (H2/H1)^shear
        # ln(V2/V1) = shear * ln(H2/H1)
        # shear = ln(V2/V1) / ln(H2/H1)
        V1, H1 = 8.0, 80.0
        V2, H2 = 10.0, 100.0

        expected_shear = math.log(V2 / V1) / math.log(H2 / H1)
        result = calculate_shear_exponent(V1, H1, V2, H2)

        assert abs(result - expected_shear) < 0.001

    def test_typical_shear_value(self):
        """Test that typical measurements give reasonable shear."""
        # Typical wind shear is around 0.1-0.2
        result = calculate_shear_exponent(
            v1=9.0, h1=80.0,
            v2=10.0, h2=100.0,
        )

        assert 0.0 < result < 0.5  # Reasonable range

    def test_same_height_raises_error(self):
        """Test that same heights raise an error."""
        with pytest.raises(ValueError):
            calculate_shear_exponent(10.0, 100.0, 10.0, 100.0)


class TestFitShearFromHeights:
    """Tests for fit_shear_from_heights function."""

    def test_fit_from_three_heights(self):
        """Test fitting shear from three height measurements."""
        # Generate synthetic data with known shear
        true_shear = 0.14
        heights = np.array([80.0, 100.0, 120.0])
        ref_height = 80.0
        ref_speed = 8.0

        # V = V_ref * (H/H_ref)^shear
        speeds = ref_speed * (heights / ref_height) ** true_shear

        fitted_shear = fit_shear_from_heights(heights, speeds)

        assert abs(fitted_shear - true_shear) < 0.01

    def test_fit_from_noisy_data(self):
        """Test fitting shear from noisy measurements."""
        true_shear = 0.14
        heights = np.array([60.0, 80.0, 100.0, 120.0])
        ref_height = 60.0
        ref_speed = 7.0

        # Generate speeds with some noise
        np.random.seed(42)
        ideal_speeds = ref_speed * (heights / ref_height) ** true_shear
        noisy_speeds = ideal_speeds + np.random.normal(0, 0.1, len(heights))

        fitted_shear = fit_shear_from_heights(heights, noisy_speeds)

        # Should be close to true shear despite noise
        assert abs(fitted_shear - true_shear) < 0.05

    def test_fit_requires_at_least_two_heights(self):
        """Test that fitting requires at least two heights."""
        with pytest.raises(ValueError):
            fit_shear_from_heights(np.array([100.0]), np.array([10.0]))


class TestExtrapolateWindDirection:
    """Tests for extrapolate_wind_direction function."""

    def test_basic_extrapolation(self):
        """Test basic wind direction extrapolation."""
        # WD2 = WD1 + deg_diff_per_m * (H2 - H1)
        result = extrapolate_wind_direction(
            wind_direction=180.0,
            reference_height=100.0,
            target_height=160.0,
            deg_diff_per_m=0.05,
        )

        expected = 180.0 + 0.05 * (160.0 - 100.0)  # 180 + 3 = 183
        assert abs(result - expected) < 0.001

    def test_wrap_around_360(self):
        """Test that direction wraps around at 360 degrees."""
        result = extrapolate_wind_direction(
            wind_direction=350.0,
            reference_height=100.0,
            target_height=200.0,
            deg_diff_per_m=0.2,
        )

        # 350 + 0.2 * 100 = 370 -> should wrap to 10
        assert 0 <= result < 360
        expected = (350.0 + 0.2 * 100.0) % 360
        assert abs(result - expected) < 0.001

    def test_negative_direction_wraps(self):
        """Test that negative direction wraps correctly."""
        result = extrapolate_wind_direction(
            wind_direction=10.0,
            reference_height=200.0,
            target_height=100.0,
            deg_diff_per_m=0.2,
        )

        # 10 + 0.2 * (-100) = -10 -> should wrap to 350
        expected = (10.0 - 20.0) % 360
        assert abs(result - expected) < 0.001

    def test_zero_change(self):
        """Test with zero deg_diff_per_m."""
        result = extrapolate_wind_direction(
            wind_direction=180.0,
            reference_height=100.0,
            target_height=200.0,
            deg_diff_per_m=0.0,
        )

        assert result == 180.0

    def test_array_input(self):
        """Test with numpy array input."""
        directions = np.array([90.0, 180.0, 270.0])
        results = extrapolate_wind_direction(
            wind_direction=directions,
            reference_height=100.0,
            target_height=160.0,
            deg_diff_per_m=0.05,
        )

        assert len(results) == 3
        # All should shift by same amount
        shift = 0.05 * (160.0 - 100.0)
        for orig, result in zip(directions, results):
            expected = (orig + shift) % 360
            assert abs(result - expected) < 0.001
