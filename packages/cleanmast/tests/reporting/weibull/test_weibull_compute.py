"""Tests for Weibull compute module — reporting domain.

Ported from tests/assessment/weibull/test_weibull_fitter.py.
Test logic, inputs, expected values, assertions preserved exactly.
"""

from datetime import datetime, timedelta
from math import gamma as gamma_func

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.weibull.compute import (
    MIN_SAMPLES,
    WeibullFitResult,
    _method_of_moments,
    fit_weibull,
    weibull_pdf,
)


def _extract_wind_speeds(
    ts_data: TimeSeriesData,
) -> list[tuple[list[float], float, str | None]]:
    """Extract wind speed columns from time series data.

    Returns list of (wind_speeds, height, marker) tuples.
    """
    results = []
    for sensor in ts_data.sensors:
        if sensor.sensor_type == "WindSpeed" and sensor.stat_type == "avg":
            col = sensor.column_name
            if col in ts_data.df.columns:
                wind_speeds = ts_data.df[col].drop_nulls().to_list()
                results.append((wind_speeds, sensor.height, None))
    return results


# =============================================================================
# Test WeibullFitResult
# =============================================================================


class TestWeibullFitResult:
    def test_creation(self) -> None:
        result = WeibullFitResult(
            height=100.0,
            interpolation_marker=None,
            shape_k=2.0,
            scale_c=8.0,
            mean_speed=7.09,
            bin_centers=[0.5, 1.5],
            observed_density=[0.1, 0.2],
            fitted_density=[0.11, 0.19],
        )
        assert result.shape_k == 2.0
        assert result.scale_c == 8.0
        assert result.height == 100.0

    def test_immutability(self) -> None:
        result = WeibullFitResult(
            height=100.0,
            interpolation_marker=None,
            shape_k=2.0,
            scale_c=8.0,
            mean_speed=7.09,
            bin_centers=[0.5],
            observed_density=[0.1],
            fitted_density=[0.11],
        )
        with pytest.raises(AttributeError):
            result.shape_k = 3.0


# =============================================================================
# Test fit_weibull
# =============================================================================


class TestFitWeibull:
    def test_mle_fitting(self) -> None:
        np.random.seed(42)
        shape_k, scale_c = 2.0, 8.0
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)

        result = fit_weibull(wind_speeds.tolist(), height=100.0)

        assert result is not None
        assert abs(result.shape_k - shape_k) < 0.2
        assert abs(result.scale_c - scale_c) < 0.8

    def test_method_of_moments_fallback(self) -> None:
        wind_speeds = [5.0] * 100

        result = fit_weibull(wind_speeds, height=100.0)

        if result is not None:
            assert result.shape_k > 0
            assert result.scale_c > 0

    def test_insufficient_data(self) -> None:
        wind_speeds = [5.0, 6.0, 7.0, 8.0, 9.0]

        result = fit_weibull(wind_speeds, height=100.0)

        assert result is None

    def test_perfect_weibull_data(self) -> None:
        np.random.seed(42)

        test_cases = [
            (1.5, 6.0),
            (2.0, 8.0),
            (2.5, 10.0),
            (3.0, 7.0),
        ]

        for expected_k, expected_c in test_cases:
            wind_speeds = expected_c * np.random.weibull(expected_k, 2000)

            result = fit_weibull(wind_speeds.tolist(), height=100.0)

            assert result is not None, f"Failed for k={expected_k}, c={expected_c}"
            assert abs(result.shape_k - expected_k) < expected_k * 0.15, (
                f"Shape k mismatch: expected {expected_k}, got {result.shape_k}"
            )
            assert abs(result.scale_c - expected_c) < expected_c * 0.15, (
                f"Scale c mismatch: expected {expected_c}, got {result.scale_c}"
            )

    def test_histogram_calculation(self) -> None:
        np.random.seed(42)
        wind_speeds = 8.0 * np.random.weibull(2.0, 1000)

        result = fit_weibull(wind_speeds.tolist(), height=100.0)

        assert result is not None
        assert len(result.bin_centers) == len(result.observed_density)
        assert len(result.bin_centers) == len(result.fitted_density)

        assert sum(result.observed_density) > 0.8
        assert sum(result.observed_density) <= 1.05

        assert sum(result.fitted_density) > 0.8
        assert sum(result.fitted_density) <= 1.05

        assert all(d >= 0 for d in result.observed_density)
        assert all(d >= 0 for d in result.fitted_density)

    def test_multiple_heights(self) -> None:
        np.random.seed(42)
        ws_100m = 8.0 * np.random.weibull(2.0, 1000)
        np.random.seed(43)
        ws_120m = 9.0 * np.random.weibull(2.2, 1000)

        result_100m = fit_weibull(ws_100m.tolist(), height=100.0)
        result_120m = fit_weibull(ws_120m.tolist(), height=120.0, interpolation_marker="外推")

        assert result_100m is not None
        assert result_120m is not None

        assert result_100m.height == 100.0
        assert result_120m.height == 120.0

        assert result_100m.interpolation_marker is None
        assert result_120m.interpolation_marker == "外推"

        assert result_120m.scale_c > result_100m.scale_c

    def test_mean_speed_calculation(self) -> None:
        np.random.seed(42)
        shape_k, scale_c = 2.0, 8.0
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)

        result = fit_weibull(wind_speeds.tolist(), height=100.0)

        assert result is not None
        expected_mean = scale_c * gamma_func(1 + 1 / shape_k)
        assert abs(result.mean_speed - expected_mean) < expected_mean * 0.15

    def test_non_positive_values_filtered(self) -> None:
        wind_speeds = [-1.0, 0.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]

        result = fit_weibull(wind_speeds, height=100.0)

        assert result is not None
        assert result.shape_k > 0
        assert result.scale_c > 0

    def test_all_non_positive_values(self) -> None:
        wind_speeds = [-1.0, 0.0, -2.0, 0.0, -3.0]

        result = fit_weibull(wind_speeds, height=100.0)

        assert result is None

    def test_method_of_moments_direct(self) -> None:
        np.random.seed(42)
        shape_k, scale_c = 2.0, 8.0
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)

        mom_k, mom_c = _method_of_moments(wind_speeds.tolist())

        assert mom_k > 0
        assert mom_c > 0
        assert abs(mom_k - shape_k) < 0.3
        assert abs(mom_c - scale_c) < 1.2

    def test_weibull_pdf_calculation(self) -> None:
        k, c = 2.0, 8.0
        x = np.array([0.0, 4.0, 8.0, 12.0, 16.0])

        pdf_values = weibull_pdf(x, k, c)

        assert pdf_values[0] == 0.0
        assert all(pdf_values >= 0)
        max_idx = np.argmax(pdf_values)
        assert 1 <= max_idx <= 3

    def test_interpolation_marker_preserved(self) -> None:
        np.random.seed(42)
        wind_speeds = 8.0 * np.random.weibull(2.0, 1000)

        result = fit_weibull(wind_speeds.tolist(), height=140.0, interpolation_marker="内插")

        assert result is not None
        assert result.interpolation_marker == "内插"
        assert result.height == 140.0
