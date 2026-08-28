"""Tests for extreme wind computation — reporting domain.

Tests cover all pure compute functions ported from assessment.
"""

import math
from datetime import datetime

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.reporting.subdomains.extreme_wind.compute import (
    EXTREME_RANGE_LIMIT_MS,
    STANDARD_AIR_DENSITY,
    SUSTAINED_RANGE_LIMIT_MS,
    MastComparison,
    _classify_wind_class,
    _compute_density_at_height,
    _convert_to_standard,
    build_iec_class_table,
    build_site_conclusion_sentences,
    build_site_determination_table,
    build_summary_comparison,
    calculate_gumbel_return_period,
    calculate_method2,
    calculate_method3,
    extract_five_day_maxima,
    fit_gumbel_distribution,
)
from scipy.stats import gumbel_r

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
        m1 = pl.DataFrame({
            "height": [120.0, 120.0, 140.0, 140.0, 160.0, 160.0],
            "method": ["method1"] * 6,
            "wind_speed_type": ["sustained", "extreme"] * 3,
            "max_wind_speed": [30.0, 42.0, 35.0, 49.0, 40.0, 56.0],
            "standard_density_wind_speed": [30.0, 42.0, 35.0, 49.0, 40.0, 56.0],
            "observed_max": [0.0] * 6,
            "interpolation_marker": [""] * 6,
        })
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
        m1 = pl.DataFrame({
            "height": [100.0, 100.0],
            "method": ["method1", "method1"],
            "wind_speed_type": ["sustained", "extreme"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [30.0, 42.0],
            "observed_max": [0.0, 0.0],
            "interpolation_marker": ["", ""],
        })
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
# Site-level cross-mast conclusion (2.6.5)
# =============================================================================


def _comp(mast_name: str, values: dict[str, list[tuple[float, float]]]) -> MastComparison:
    """Build a MastComparison from {kind: [(height, conservative_max)]}."""
    frames: dict[str, pl.DataFrame] = {}
    for kind, pairs in values.items():
        frames[kind] = pl.DataFrame({
            "height": [h for h, _ in pairs],
            "conservative_max": [v for _, v in pairs],
        })
    return MastComparison(
        mast_name=mast_name, sustained=frames["sustained"], extreme=frames["extreme"]
    )


class TestRangeLimitConstants:
    def test_limits(self) -> None:
        assert SUSTAINED_RANGE_LIMIT_MS == 3.0
        assert EXTREME_RANGE_LIMIT_MS == 4.2
        assert EXTREME_RANGE_LIMIT_MS == pytest.approx(3.0 * 1.4)


class TestBuildSiteDeterminationTable:
    def test_cross_mast_max_per_height(self) -> None:
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0), (140.0, 31.0)],
                "extreme": [(120.0, 42.0), (140.0, 43.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 32.5)],
                "extreme": [(120.0, 45.5)],
            }),
        ]
        result = build_site_determination_table(comparisons)
        # Union of heights across masts, one row each
        assert result["height"].to_list() == [120.0, 140.0]
        # Cross-mast MAX of the conservative column
        assert result["cross_mast_max_sustained"].to_list() == [32.5, 31.0]
        assert result["cross_mast_max_extreme"].to_list() == [45.5, 43.0]
        assert result["wind_class"].to_list() == ["III", "III"]

    def test_classification_uses_classified_tier_thresholds(self) -> None:
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 40.0)],
                "extreme": [(120.0, 55.0)],
            }),
        ]
        result = build_site_determination_table(comparisons)
        assert result["wind_class"].to_list() == ["II"]

    def test_boundary_inclusive_classifies_into_tier(self) -> None:
        """(37.5, 52.5) sits exactly on the III boundary → III (<= rule)."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 37.5)],
                "extreme": [(120.0, 52.5)],
            }),
        ]
        result = build_site_determination_table(comparisons)
        assert result["wind_class"].to_list() == ["III"]

    def test_empty_comparisons_yield_empty_table(self) -> None:
        assert build_site_determination_table([]).is_empty()


class TestBuildSiteConclusionSentences:
    def test_single_class_path_when_masts_agree(self) -> None:
        """Ranges within limits → one sentence, worst height class site-wide."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0), (140.0, 31.0)],
                "extreme": [(120.0, 42.0), (140.0, 43.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 31.0)],
                "extreme": [(120.0, 43.5)],
            }),
        ]
        sentences = build_site_conclusion_sentences(comparisons)
        assert len(sentences) == 1
        assert "低于 37.5 m/s" in sentences[0]
        assert "低于 52.5 m/s" in sentences[0]
        assert "IEC III 类及以上等级" in sentences[0]
        assert "《GB/T 18451.1-2022 风力发电机组 设计要求》" in sentences[0]

    def test_zoned_path_when_classes_differ(self) -> None:
        """>= 3 m/s sustained range AND differing per-mast classes → zoned."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0)],
                "extreme": [(120.0, 42.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 40.0)],
                "extreme": [(120.0, 55.0)],
            }),
        ]
        sentences = build_site_conclusion_sentences(comparisons)
        assert len(sentences) == 3  # lead + one per mast
        assert any("MA 测风塔代表区域机位选择 IEC III 类及以上等级" in s for s in sentences)
        assert any("MB 测风塔代表区域机位选择 IEC II 类及以上等级" in s for s in sentences)
        assert not any("本项目可选择" in s for s in sentences)

    def test_agree_despite_large_range_path(self) -> None:
        """Range over the limit but all masts classify the same → single sentence."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0)],
                "extreme": [(120.0, 42.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 36.0)],
                "extreme": [(120.0, 50.0)],
            }),
        ]
        sentences = build_site_conclusion_sentences(comparisons)
        assert len(sentences) == 1
        assert "IEC III 类及以上等级" in sentences[0]

    def test_s_class_path(self) -> None:
        """Any value above the I thresholds → S 类场址专用 wording."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 55.0)],
                "extreme": [(120.0, 77.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 56.0)],
                "extreme": [(120.0, 78.0)],
            }),
        ]
        sentences = build_site_conclusion_sentences(comparisons)
        assert len(sentences) == 1
        assert "不低于 50.0 m/s" in sentences[0]
        assert "不低于 70.0 m/s" in sentences[0]
        assert "S 类" in sentences[0]
        assert "低于" not in sentences[0].split("不低于")[0]  # no 低于 before the S part

    def test_zoned_path_with_s_class_mast(self) -> None:
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0)],
                "extreme": [(120.0, 42.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 55.0)],
                "extreme": [(120.0, 77.0)],
            }),
        ]
        sentences = build_site_conclusion_sentences(comparisons)
        assert any("MA 测风塔代表区域机位选择 IEC III 类及以上等级" in s for s in sentences)
        assert any("MB 测风塔代表区域" in s and "IEC S 类" in s for s in sentences)

    def test_boundary_range_exactly_at_limit_is_disagreement(self) -> None:
        """Range == 3.0 (not <) already counts as 相差大."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0)],
                "extreme": [(120.0, 42.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 33.0)],
                "extreme": [(120.0, 43.0)],
            }),
        ]
        # Both masts classify III → large range but agreeing classes.
        sentences = build_site_conclusion_sentences(comparisons)
        assert len(sentences) == 1
        assert "IEC III 类及以上等级" in sentences[0]

    def test_extreme_range_over_limit_is_disagreement(self) -> None:
        """Sustained within limit but extreme range >= 4.2 → 相差大."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0)],
                "extreme": [(120.0, 42.0)],
            }),
            _comp("MB", {
                "sustained": [(120.0, 31.0)],
                "extreme": [(120.0, 46.2)],
            }),
        ]
        # Both masts classify III → agree-despite-large-range sentence.
        sentences = build_site_conclusion_sentences(comparisons)
        assert len(sentences) == 1
        assert "IEC III 类及以上等级" in sentences[0]

    def test_site_class_is_most_severe_height(self) -> None:
        """One height III, another II → site class II (most severe)."""
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0), (140.0, 40.0)],
                "extreme": [(120.0, 42.0), (140.0, 55.0)],
            }),
        ]
        sentences = build_site_conclusion_sentences(comparisons)
        assert "IEC II 类及以上等级" in sentences[0]

    def test_empty_comparisons_yield_no_sentences(self) -> None:
        assert build_site_conclusion_sentences([]) == []

    def test_masts_with_empty_comparison_frames_are_skipped(self) -> None:
        empty = MastComparison(
            mast_name="MB",
            sustained=pl.DataFrame({"height": [], "conservative_max": []}),
            extreme=pl.DataFrame({"height": [], "conservative_max": []}),
        )
        comparisons = [
            _comp("MA", {
                "sustained": [(120.0, 30.0)],
                "extreme": [(120.0, 42.0)],
            }),
            empty,
        ]
        sentences = build_site_conclusion_sentences(comparisons)
        assert len(sentences) == 1
        assert "IEC III 类及以上等级" in sentences[0]


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
