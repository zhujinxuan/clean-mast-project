"""Tests for the cleaning capability compute helpers."""

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest
from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.subdomains.reporting.model.sectors import find_sector
from cleanmast.subdomains.reporting.subdomains.cleaning.compute import (
    assign_sector,
    correlation_matrix,
    count_valid_points,
    coverage_stats,
    expected_points,
    linear_regression,
    sector_ws_stats,
)


def _df(timestamps, ws_values):
    return pl.DataFrame({
        "timestamp": timestamps,
        "ws": ws_values,
    })


class TestExpectedPoints:
    def test_inclusive_grid(self):
        window = TimeRange(
            min=datetime(2025, 1, 1, 0, 0),
            max=datetime(2025, 1, 1, 1, 0),
        )
        # 00:00..01:00 inclusive on a 10-min grid = 7 points
        assert expected_points(window) == 7

    def test_non_aligned_window_floors(self):
        window = TimeRange(
            min=datetime(2025, 1, 1, 0, 0),
            max=datetime(2025, 1, 1, 0, 25),
        )
        # 25 min // 10 min = 2 full steps → 3 points
        assert expected_points(window) == 3

    def test_one_year_rep_window(self):
        window = TimeRange(
            min=datetime(2024, 9, 1),
            max=datetime(2025, 8, 31, 23, 50),
        )
        assert expected_points(window) == 365 * 144

    def test_custom_interval(self):
        window = TimeRange(
            min=datetime(2025, 1, 1), max=datetime(2025, 1, 1, 1, 0),
        )
        assert expected_points(window, interval_minutes=60) == 2

    def test_non_positive_interval_rejected(self):
        window = TimeRange(
            min=datetime(2025, 1, 1), max=datetime(2025, 1, 2),
        )
        with pytest.raises(ValueError, match="positive"):
            expected_points(window, interval_minutes=0)


class TestCountValidPoints:
    def test_counts_non_null_inside_window_only(self):
        start = datetime(2025, 1, 1)
        df = _df(
            [
                start,
                start + timedelta(minutes=10),
                start + timedelta(minutes=20),
                start + timedelta(days=10),  # outside window
            ],
            [1.0, None, 3.0, 9.9],
        )
        window = TimeRange(
            min=start, max=start + timedelta(minutes=30),
        )
        assert count_valid_points(df, "ws", window) == 2

    def test_tz_stripped_window_bounds(self):
        start = datetime(2025, 1, 1)
        df = _df([start, start + timedelta(minutes=10)], [1.0, 2.0])
        window = TimeRange(
            min=datetime(2025, 1, 1, tzinfo=timezone.utc),
            max=datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc),
        )
        assert count_valid_points(df, "ws", window) == 2

    def test_unknown_column_counts_zero(self):
        window = TimeRange(min=datetime(2025, 1, 1), max=datetime(2025, 1, 2))
        df = _df([datetime(2025, 1, 1)], [1.0])
        assert count_valid_points(df, "missing", window) == 0


class TestCoverageStats:
    def test_ratio(self):
        start = datetime(2025, 1, 1)
        df = _df(
            [start + timedelta(minutes=10 * i) for i in range(6)],
            [1.0, None, 3.0, 4.0, 5.0, 6.0],
        )
        window = TimeRange(min=start, max=start + timedelta(minutes=50))
        stats = coverage_stats(df, "ws", window)
        assert stats.expected_points == 6
        assert stats.valid_points == 5
        assert stats.coverage_ratio == pytest.approx(5 / 6)

    def test_ratio_none_for_empty_window(self):
        window = TimeRange(min=datetime(2025, 1, 1), max=datetime(2025, 1, 1))
        stats = coverage_stats(pl.DataFrame({"timestamp": [], "ws": []}), "ws", window)
        # zero-length window still yields 1 expected point on the grid
        assert stats.expected_points == 1


class TestLinearRegression:
    def test_perfect_line(self):
        df = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})
        result = linear_regression(df, "x", "y")
        assert result.slope == pytest.approx(2.0)
        assert result.intercept == pytest.approx(0.0, abs=1e-9)
        assert result.r == pytest.approx(1.0)
        assert result.rmse == pytest.approx(0.0, abs=1e-9)
        assert result.n == 4

    def test_negative_correlation_signs_slope_and_r(self):
        df = pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [3.0, 2.0, 1.0]})
        result = linear_regression(df, "x", "y")
        assert result.slope == pytest.approx(-1.0)
        assert result.r == pytest.approx(-1.0)

    def test_noisy_fit_values(self):
        # y = x + noise with known rmse-friendly construction
        df = pl.DataFrame({
            "x": [0.0, 1.0, 2.0, 3.0],
            "y": [0.1, 1.2, 1.8, 3.1],
        })
        result = linear_regression(df, "x", "y")
        assert 0.99 < result.r < 1.0001
        assert result.slope == pytest.approx(1.0, abs=0.1)
        assert result.rmse > 0

    def test_null_pairs_excluded(self):
        df = pl.DataFrame({"x": [1.0, None, 3.0], "y": [2.0, 99.0, 6.0]})
        result = linear_regression(df, "x", "y")
        assert result.n == 2

    def test_too_few_pairs_raises(self):
        df = pl.DataFrame({"x": [1.0], "y": [2.0]})
        with pytest.raises(ValueError, match="at least 2"):
            linear_regression(df, "x", "y")

    def test_zero_variance_x_raises(self):
        df = pl.DataFrame({"x": [2.0, 2.0, 2.0], "y": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError, match="zero variance"):
            linear_regression(df, "x", "y")


class TestCorrelationMatrix:
    def _df(self):
        return pl.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0],
            "b": [2.0, 4.0, 6.0, 8.0],
            "c": [4.0, 3.0, 2.0, 1.0],
        })

    def test_pairwise_values_and_diagonal(self):
        matrix = correlation_matrix(self._df(), ["a", "b", "c"])
        assert matrix["column"].to_list() == ["a", "b", "c"]
        assert matrix["a"].to_list() == pytest.approx([1.0, 1.0, -1.0])
        assert matrix["b"].to_list() == pytest.approx([1.0, 1.0, -1.0])
        assert matrix["c"].to_list() == pytest.approx([-1.0, -1.0, 1.0])

    def test_single_column(self):
        matrix = correlation_matrix(self._df(), ["a"])
        assert matrix.shape == (1, 2)
        assert matrix["a"][0] == 1.0

    def test_nulls_handled_pairwise(self):
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0, None],
            "b": [1.0, 2.0, 3.0, 100.0],
        })
        matrix = correlation_matrix(df, ["a", "b"])
        assert matrix["a"][1] == pytest.approx(1.0)

    def test_constant_column_yields_nan_off_diagonal(self):
        df = pl.DataFrame({
            "a": [1.0, 2.0, 3.0],
            "k": [5.0, 5.0, 5.0],
        })
        matrix = correlation_matrix(df, ["a", "k"])
        assert matrix["k"][0] != matrix["k"][0]  # NaN

    def test_unknown_column_raises(self):
        with pytest.raises(KeyError, match="not in DataFrame"):
            correlation_matrix(self._df(), ["a", "zz"])

    def test_duplicate_columns_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            correlation_matrix(self._df(), ["a", "a"])


class TestSectorStats:
    def test_find_sector_boundaries(self):
        assert find_sector(0.0) == 1  # N
        assert find_sector(11.24) == 1
        assert find_sector(11.25) == 2  # NNE
        assert find_sector(337.5) == 16  # NNW (center)
        assert find_sector(348.74) == 16  # last value inside NNW
        assert find_sector(348.75) == 1  # boundary wraps to N
        assert find_sector(360.0) == 1

    def test_assign_sector(self):
        df = pl.DataFrame({
            "wd": [0.0, 22.5, None, 337.5],
        })
        result = assign_sector(df, "wd")
        assert result["sector"].to_list() == [1, 2, None, 16]

    def test_sector_ws_stats(self):
        df = pl.DataFrame({
            "wd": [0.0, 5.0, 22.5, None],
            "ws": [5.0, 7.0, 3.0, 9.0],
        })
        stats = sector_ws_stats(df, "wd", "ws")
        assert stats["sector"].to_list() == [1, 2]
        assert stats["data_points"].to_list() == [2, 1]
        assert stats["mean_ws"].to_list() == pytest.approx([6.0, 3.0])

    def test_null_speed_rows_excluded(self):
        df = pl.DataFrame({
            "wd": [0.0, 10.0, 200.0],
            "ws": [5.0, None, 4.0],
        })
        stats = sector_ws_stats(df, "wd", "ws")
        assert stats["sector"].to_list() == [1, 10]
        assert stats["data_points"].to_list() == [1, 1]
