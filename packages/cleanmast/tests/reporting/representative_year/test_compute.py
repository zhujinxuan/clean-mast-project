"""Unit tests for extracted functions in compute.py."""

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.representative_year.compute import (
    _combine_sector_rows,
    _compute_per_sector_regression,
    _SectorMesoStats,
    _SectorRegResult,
)


def _make_sensor(name: str, sensor_type: str, height: float) -> SensorColumn:
    """Create a minimal SensorColumn for testing."""
    return SensorColumn(
        column_name=name,
        sensor_type=sensor_type,
        sensor_direction="",
        stat_type="avg",
        height=height,
        unit="m/s" if sensor_type == "WindSpeed" else "deg",
    )


class TestCombineSectorRows:
    """Tests for _combine_sector_rows — pure zip function."""

    def test_adjustment_equals_slope_times_diff(self):
        """adjustment = slope x diff for each sector."""
        stats = [
            _SectorMesoStats(sector_index=i, clim_mean=5.0, rep_mean=5.5, diff=-0.5)
            for i in range(1, 17)
        ]
        regs = [
            _SectorRegResult(sector_index=i, slope=1.2, intercept=0.1, data_points=100)
            for i in range(1, 17)
        ]
        rows = _combine_sector_rows(stats, regs, height=120.0)
        assert len(rows) == 16
        for row in rows:
            assert row.adjustment == pytest.approx(row.slope * row.meso_difference, abs=1e-4)
            assert row.climatology_mean == 5.0
            assert row.rep_year_mean == 5.5
            assert row.slope == 1.2
            assert row.data_points == 100

    def test_sector_indices_match(self):
        """Each row's sector_index matches the input stats/regs."""
        stats = [_SectorMesoStats(sector_index=i, clim_mean=0.0, rep_mean=0.0, diff=0.0) for i in range(1, 17)]
        regs = [_SectorRegResult(sector_index=i, slope=0.0, intercept=0.0, data_points=0) for i in range(1, 17)]
        rows = _combine_sector_rows(stats, regs, height=100.0)
        for i, row in enumerate(rows, 1):
            assert row.sector_index == i


class TestComputePerSectorRegression:
    """Tests for _compute_per_sector_regression."""

    @pytest.fixture
    def aligned_data(self) -> tuple:
        """Create synthetic aligned mast+meso data with 16 sectors."""
        n = 1600
        rng = np.random.default_rng(42)
        timestamps = [datetime(2025, 1, 1) + timedelta(minutes=10 * i) for i in range(n)]
        wd = np.tile(np.arange(0, 360, 22.5), n // 16 + 1)[:n]
        meso_ws = rng.normal(6.0, 1.0, n).clip(0)
        mast_ws = 0.9 * meso_ws + 0.5 + rng.normal(0, 0.1, n)

        mast_sensors = [_make_sensor("ws_120m_avg", "WindSpeed", 120.0)]
        meso_sensors = [
            _make_sensor("meso_ws", "WindSpeed", 100.0),
            _make_sensor("meso_wd", "WindDirection", 100.0),
        ]

        mast_df = pl.DataFrame({"timestamp": timestamps, "ws_120m_avg": mast_ws})
        meso_df = pl.DataFrame({"timestamp": timestamps, "meso_ws": meso_ws, "meso_wd": wd})

        mast_ts = TimeSeriesData(df=mast_df, sensors=mast_sensors)
        meso_ts = TimeSeriesData(df=meso_df, sensors=meso_sensors)

        return mast_ts, meso_ts, mast_sensors[0], meso_sensors[0], meso_sensors[1]

    def test_returns_16_results(self, aligned_data):
        """Returns exactly 16 sector results."""
        mast, meso, mast_ws, meso_ws, meso_wd = aligned_data
        train_min = datetime(2025, 1, 1)
        train_max = datetime(2025, 1, 2)
        results = _compute_per_sector_regression(
            mast, meso, mast_ws, meso_ws, meso_wd, train_min, train_max,
        )
        assert len(results) == 16
        indices = {r.sector_index for r in results}
        assert indices == set(range(1, 17))

    def test_slope_near_one_for_correlated_data(self, aligned_data):
        """Slope should be ~1 for data with mast = 0.9 x meso + 0.5."""
        mast, meso, mast_ws, meso_ws, meso_wd = aligned_data
        train_min = datetime(2025, 1, 1)
        train_max = datetime(2025, 1, 2)
        results = _compute_per_sector_regression(
            mast, meso, mast_ws, meso_ws, meso_wd, train_min, train_max,
        )
        slopes = [r.slope for r in results if r.slope > 0]
        avg_slope = sum(slopes) / len(slopes)
        assert 0.7 < avg_slope < 1.1
