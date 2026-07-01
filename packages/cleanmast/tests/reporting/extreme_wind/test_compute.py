"""Tests for extreme wind computation — reporting domain.

Tests cover all pure compute functions ported from assessment.
"""

import math
from datetime import datetime

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.reporting.subdomains.extreme_wind.compute import (
    STANDARD_AIR_DENSITY,
    _classify_wind_class,
    _compute_density_at_height,
    _convert_to_standard,
    build_iec_class_table,
    build_summary_comparison,
    calculate_gumbel_return_period,
    calculate_method1,
    calculate_method2,
    calculate_method3,
    extract_five_day_maxima,
    fit_gumbel_distribution,
)
from scipy.stats import gumbel_r

# =============================================================================
# Method 1 - Five Times Average Wind Speed
# =============================================================================


class TestCalculateMethod1:
    def test_basic_three_heights(self) -> None:
        """Test basic calculation at 120m, 140m, 160m."""
        df = calculate_method1(
            wind_speed_values=[6.0, 7.0, 8.0],
            heights=[120.0, 140.0, 160.0],
            air_density=STANDARD_AIR_DENSITY,
            reference_height=10.0,
        )

        assert len(df) == 6  # 3 heights x 2 wind_speed_types
        for height, expected_avg in [(120.0, 6.0), (140.0, 7.0), (160.0, 8.0)]:
            height_rows = df.filter(pl.col("height") == height)
            assert len(height_rows) == 2
            sustained_row = height_rows.filter(pl.col("wind_speed_type") == "sustained").row(0, named=True)
            extreme_row = height_rows.filter(pl.col("wind_speed_type") == "extreme").row(0, named=True)

            expected_sustained = 5.0 * expected_avg
            expected_extreme = 1.4 * expected_sustained
            assert math.isclose(sustained_row["max_wind_speed"], expected_sustained, rel_tol=1e-9)
            assert math.isclose(extreme_row["max_wind_speed"], expected_extreme, rel_tol=1e-9)

    def test_standard_density_conversion(self) -> None:
        """Lower density gives lower standard-density equivalent."""
        df = calculate_method1(
            wind_speed_values=[7.0],
            heights=[100.0],
            air_density=1.1,
            reference_height=10.0,
        )
        sustained_row = df.filter(pl.col("wind_speed_type") == "sustained").row(0, named=True)
        assert sustained_row["standard_density_wind_speed"] < sustained_row["max_wind_speed"]

    def test_all_method_values_are_method1(self) -> None:
        """Verify all rows have method='method1'."""
        df = calculate_method1(
            wind_speed_values=[5.0],
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
            reference_height=10.0,
        )
        assert all(m == "method1" for m in df["method"].to_list())


# =============================================================================
# Method 2 - Five-Day Maximum (Gumbel)
# =============================================================================


class TestExtractFiveDayMaxima:
    def test_known_timestamps_correct_maxima_count(self) -> None:
        timestamps = pl.Series([datetime(2024, 1, d) for d in range(1, 16)])
        wind_speeds = pl.Series([float(d) for d in range(1, 16)])
        result = extract_five_day_maxima(wind_speeds, timestamps)
        assert len(result) == 3
        assert result.to_list() == [5.0, 10.0, 15.0]


class TestFitGumbelDistribution:
    def test_synthetic_gumbel_data_within_tolerance(self) -> None:
        mu_true = 20.0
        beta_true = 3.0
        rng = np.random.default_rng(42)
        data = gumbel_r.rvs(loc=mu_true, scale=beta_true, size=500, random_state=rng)
        fit = fit_gumbel_distribution(data.tolist())
        assert fit is not None
        mu_fit, beta_fit = fit
        assert math.isclose(mu_fit, mu_true, rel_tol=0.06)
        assert math.isclose(beta_fit, beta_true, rel_tol=0.06)

    def test_insufficient_data_returns_none(self) -> None:
        assert fit_gumbel_distribution([1.0, 2.0, 3.0]) is None

    def test_near_zero_variance(self) -> None:
        result = fit_gumbel_distribution([10.0] * 20)
        assert result is not None


class TestCalculateGumbelReturnPeriod:
    def test_known_values(self) -> None:
        mu = 20.0
        beta = 3.0
        result = calculate_gumbel_return_period(mu, beta)
        t = 50.0 * 365.0 / 5.0
        p = 1.0 - 1.0 / t
        expected = mu - beta * math.log(-math.log(p))
        assert math.isclose(result, expected, rel_tol=1e-9)


class TestCalculateMethod2:
    def test_synthetic_gumbel_data(self) -> None:
        rng = np.random.default_rng(42)
        mu_true = 15.0
        beta_true = 2.0
        data = gumbel_r.rvs(loc=mu_true, scale=beta_true, size=1000, random_state=rng)

        result = calculate_method2(
            five_day_maxima=data.tolist(),
            height=100.0,
            air_density=STANDARD_AIR_DENSITY,
            reference_height=10.0,
            wind_speed_type="sustained",
        )
        assert result is not None
        assert result["wind_speed_type"] == "sustained"
        assert result["method"] == "method2"
        assert result["height"] == 100.0
        assert result["sample_count"] == 1000
        assert len(result["sample_data"]) == 1000

    def test_insufficient_data_returns_none(self) -> None:
        result = calculate_method2(
            five_day_maxima=[1.0, 2.0],
            height=100.0,
            air_density=STANDARD_AIR_DENSITY,
            reference_height=10.0,
            wind_speed_type="sustained",
        )
        assert result is None


# =============================================================================
# Method 3 - Extreme Wind Model (EWM)
# =============================================================================


class TestCalculateMethod3:
    def test_basic_calculation(self) -> None:
        result = calculate_method3(
            observed_max=20.0,
            height=100.0,
            air_density=STANDARD_AIR_DENSITY,
            reference_height=10.0,
            wind_speed_type="sustained",
        )
        assert result["max_wind_speed"] == 25.0  # 20.0 * 1.25
        assert result["method"] == "method3"

    def test_standard_density_conversion(self) -> None:
        result = calculate_method3(
            observed_max=20.0,
            height=100.0,
            air_density=1.1,
            reference_height=10.0,
            wind_speed_type="sustained",
        )
        assert result["standard_density_wind_speed"] < result["max_wind_speed"]


# =============================================================================
# Summary
# =============================================================================


class TestBuildSummaryComparison:
    def test_three_heights_comparison(self) -> None:
        m1 = calculate_method1(
            wind_speed_values=[6.0, 7.0, 8.0],
            heights=[120.0, 140.0, 160.0],
            air_density=STANDARD_AIR_DENSITY,
            reference_height=10.0,
        )
        m3_data = [
            calculate_method3(
                observed_max=20.0, height=h,
                air_density=STANDARD_AIR_DENSITY,
                reference_height=10.0,
                wind_speed_type="sustained",
            )
            for h in [120.0, 140.0, 160.0]
        ]
        m3 = pl.DataFrame(m3_data)

        # Create empty method2 data
        empty_m2 = pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "method": pl.Series([], dtype=pl.String),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "max_wind_speed": pl.Series([], dtype=pl.Float64),
            "standard_density_wind_speed": pl.Series([], dtype=pl.Float64),
            "observed_max": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
        })

        result = build_summary_comparison(m1, empty_m2, m3, "sustained")
        assert len(result) == 3
        assert set(result["height"].to_list()) == {120.0, 140.0, 160.0}


class TestBuildIECClassTable:
    def test_basic_classification(self) -> None:
        m1 = calculate_method1(
            wind_speed_values=[6.0],
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
            reference_height=10.0,
        )
        empty = pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "method1": pl.Series([], dtype=pl.Float64),
            "method2": pl.Series([], dtype=pl.Float64),
            "method3": pl.Series([], dtype=pl.Float64),
            "conservative_max": pl.Series([], dtype=pl.Float64),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "interpolation_marker": pl.Series([], dtype=pl.String),
        })
        sus = build_summary_comparison(m1, empty, empty, "sustained")
        ext = build_summary_comparison(m1, empty, empty, "extreme")
        result = build_iec_class_table(sus, ext)
        assert len(result) >= 4  # 4 reference rows + per-height rows


class TestClassifyWindClass:
    def test_class_iii(self) -> None:
        assert _classify_wind_class(30.0, 40.0) == "III"

    def test_class_ii(self) -> None:
        assert _classify_wind_class(40.0, 55.0) == "II"

    def test_class_i(self) -> None:
        assert _classify_wind_class(45.0, 65.0) == "I"

    def test_class_s(self) -> None:
        assert _classify_wind_class(55.0, 80.0) == "S"


# =============================================================================
# Internal helpers
# =============================================================================


class TestInternalHelpers:
    def test_compute_density_at_height_same_height(self) -> None:
        result = _compute_density_at_height(70.0, 1.225, 70.0)
        assert pytest.approx(result, rel=1e-6) == 1.225

    def test_compute_density_at_height_higher(self) -> None:
        result = _compute_density_at_height(100.0, 1.225, 10.0)
        assert result < 1.225
        assert result > 0

    def test_convert_to_standard_same_density(self) -> None:
        result = _convert_to_standard(10.0, STANDARD_AIR_DENSITY)
        assert result == 10.0

    def test_convert_to_standard_lower_density(self) -> None:
        result = _convert_to_standard(10.0, 1.1)
        assert result < 10.0
