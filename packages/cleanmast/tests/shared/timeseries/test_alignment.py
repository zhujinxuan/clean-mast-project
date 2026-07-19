"""Tests for shared/timeseries/alignment.py — unified timeseries alignment."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.shared.timeseries.alignment import (
    _add_uv_helpers,
    _compute_from_uv,
    _compute_native_interval,
    _downsample_to_interval,
    _drop_uv_helpers,
    _filter_avg_sensors,
    _find_nearest_ws,
    _upsample_to_interval,
    align_to_interval,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

# ── Fixtures ──────────────────────────────────────────────────────────────


def _make_sensors(specs: list[tuple[str, str, str, float, str]]) -> list[SensorColumn]:
    """Build SensorColumn list from (column_name, sensor_type, direction, height, stat_type)."""
    return [
        SensorColumn(
            column_name=cn,
            sensor_type=st,
            sensor_direction=sd,
            height=h,
            stat_type=stat,
            unit="m/s" if st == "WindSpeed" else "deg",
        )
        for cn, st, sd, h, stat in specs
    ]


def _make_ts(
    timestamps: list[datetime],
    values: dict[str, list[float]],
    sensors: list[SensorColumn],
) -> TimeSeriesData:
    """Build a TimeSeriesData from timestamps, column values, and sensors."""
    df = pl.DataFrame({"timestamp": timestamps, **values})
    return TimeSeriesData(df=df, sensors=sensors)


# ── _compute_native_interval ──────────────────────────────────────────────


class TestComputeNativeInterval:
    def test_10min(self):
        ts = [datetime(2025, 1, 1, i // 6, (i % 6) * 10) for i in range(60)]
        df = pl.DataFrame({"timestamp": ts, "ws": [5.0] * 60})
        assert _compute_native_interval(df) == pytest.approx(10.0)

    def test_60min(self):
        ts = [datetime(2025, 1, 1, i, 0) for i in range(24)]
        df = pl.DataFrame({"timestamp": ts, "ws": [5.0] * 24})
        assert _compute_native_interval(df) == pytest.approx(60.0)

    def test_irregular_mode(self):
        # 48 × 10min gaps + 1 × 20min gap → mode is 10min
        ts = [datetime(2025, 1, 1, 0, 0) + timedelta(minutes=10 * i) for i in range(48)]
        ts.append(ts[-1] + timedelta(minutes=20))
        df = pl.DataFrame({"timestamp": ts, "ws": [5.0] * len(ts)})
        assert _compute_native_interval(df) == pytest.approx(10.0)

    def test_single_row_raises(self):
        df = pl.DataFrame({"timestamp": [datetime(2025, 1, 1)], "ws": [5.0]})
        with pytest.raises(ValueError):
            _compute_native_interval(df)


# ── _filter_avg_sensors ───────────────────────────────────────────────────


class TestFilterAvgSensors:
    def test_keeps_avg_ws_wd(self):
        sensors = _make_sensors([
            ("WindSpeed_100m_avg [m/s]", "WindSpeed", "", 100.0, "avg"),
            ("WindSpeed_100m_max [m/s]", "WindSpeed", "", 100.0, "max"),
            ("WindDirection_100m_avg [deg]", "WindDirection", "", 100.0, "avg"),
            ("Temperature_1m_avg [C]", "Temperature", "", 1.0, "avg"),
        ])
        ts = TimeSeriesData(df=pl.DataFrame({"timestamp": []}), sensors=sensors)
        result = _filter_avg_sensors(ts)
        assert len(result) == 2
        assert result[0].column_name == "WindSpeed_100m_avg [m/s]"
        assert result[1].column_name == "WindDirection_100m_avg [deg]"

    def test_excludes_interpolated(self):
        # _fill:interpolated must be at END of column name (regex r"_fill:(\w+)$")
        sensors = _make_sensors([
            ("WindSpeed_120m_avg [m/s]", "WindSpeed", "", 120.0, "avg"),
            ("WindSpeed_140m_avg [m/s]_fill:interpolated", "WindSpeed", "", 140.0, "avg"),
        ])
        ts = TimeSeriesData(df=pl.DataFrame({"timestamp": []}), sensors=sensors)
        result = _filter_avg_sensors(ts)
        assert len(result) == 1
        assert result[0].column_name == "WindSpeed_120m_avg [m/s]"


# ── _add_uv_helpers / _compute_from_uv / _drop_uv_helpers ─────────────────


class TestUVHelpers:
    def test_add_and_drop(self):
        df = pl.DataFrame({"timestamp": [datetime(2025, 1, 1)], "wd": [90.0]})
        result = _add_uv_helpers(df, "wd", 120.0)
        assert "u_120m_helper" in result.columns
        assert "v_120m_helper" in result.columns
        # sin(90°) ≈ 1, cos(90°) ≈ 0
        assert result["u_120m_helper"][0] == pytest.approx(1.0, abs=0.01)
        assert result["v_120m_helper"][0] == pytest.approx(0.0, abs=0.01)

        dropped = _drop_uv_helpers(result, 120.0)
        assert "u_120m_helper" not in dropped.columns
        assert "v_120m_helper" not in dropped.columns

    def test_add_with_ws(self):
        df = pl.DataFrame({
            "timestamp": [datetime(2025, 1, 1)],
            "wd": [45.0],
            "ws": [8.0],
        })
        result = _add_uv_helpers(df, "wd", 100.0, ws_col="ws")
        assert "ws_100m_helper" in result.columns
        assert result["ws_100m_helper"][0] == 8.0

    def test_compute_from_uv(self):
        u_val = np.sin(np.radians(90))
        v_val = np.cos(np.radians(90))
        expr = _compute_from_uv(pl.lit(u_val), pl.lit(v_val), "wd")
        result = pl.DataFrame({"placeholder": [1]}).with_columns(expr)
        assert result["wd"][0] == pytest.approx(90.0, abs=0.1)


# ── Circular interpolation ────────────────────────────────────────────────


class TestCircularInterpolation:
    def _wd_from_uv(self, u: float, v: float) -> float:
        """Helper: compute wind direction from u/v, normalized to [0, 360)."""
        return np.degrees(np.arctan2(u, v)) % 360

    def test_within_quadrant(self):
        """10° → 20° at midpoint should be ~15°."""
        u1, v1 = np.sin(np.radians(10)), np.cos(np.radians(10))
        u2, v2 = np.sin(np.radians(20)), np.cos(np.radians(20))
        result = self._wd_from_uv((u1 + u2) / 2, (v1 + v2) / 2)
        assert result == pytest.approx(15.0, abs=0.5)

    def test_crosses_north(self):
        """350° → 10° at midpoint should be ~0° (or ~360°)."""
        u1, v1 = np.sin(np.radians(350)), np.cos(np.radians(350))
        u2, v2 = np.sin(np.radians(10)), np.cos(np.radians(10))
        result = self._wd_from_uv((u1 + u2) / 2, (v1 + v2) / 2)
        # 360° and 0° are the same direction
        assert result == pytest.approx(0.0, abs=1.0) or result == pytest.approx(360.0, abs=1.0)

    def test_opposite_directions(self):
        """0° → 180° → atan2(0, 0) → degenerate (0° or undefined)."""
        u1, v1 = np.sin(np.radians(0)), np.cos(np.radians(0))
        u2, v2 = np.sin(np.radians(180)), np.cos(np.radians(180))
        u_mid = (u1 + u2) / 2
        v_mid = (v1 + v2) / 2
        # atan2(~0, ~0) → degenerate; result depends on floating point
        result = self._wd_from_uv(u_mid, v_mid)
        # Accept any value for degenerate case — the important thing is it doesn't crash
        assert 0 <= result < 360

    def test_vector_mean_near_north(self):
        """[350°, 10°, 0°] → ≈ 0° (or 360°)."""
        dirs = [350, 10, 0]
        u_mean = np.mean([np.sin(np.radians(d)) for d in dirs])
        v_mean = np.mean([np.cos(np.radians(d)) for d in dirs])
        result = self._wd_from_uv(u_mean, v_mean)
        assert result == pytest.approx(0.0, abs=2.0) or result == pytest.approx(360.0, abs=2.0)


# ── _find_nearest_ws ──────────────────────────────────────────────────────


class TestFindNearestWs:
    def test_exact_match(self):
        ws = _make_sensors([
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
            ("ws_120", "WindSpeed", "", 120.0, "avg"),
        ])
        result = _find_nearest_ws(120.0, ws)
        assert result.column_name == "ws_120"

    def test_nearest_below(self):
        ws = _make_sensors([
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
            ("ws_140", "WindSpeed", "", 140.0, "avg"),
        ])
        result = _find_nearest_ws(105.0, ws)
        assert result.column_name == "ws_100"

    def test_equidistant_prefers_higher(self):
        ws = _make_sensors([
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
            ("ws_120", "WindSpeed", "", 120.0, "avg"),
        ])
        result = _find_nearest_ws(110.0, ws)
        assert result.column_name == "ws_120"  # higher wins tiebreak


# ── Downsampling ──────────────────────────────────────────────────────────


class TestDownsample:
    def test_downsample_wd_weighted(self):
        """10min WD + WS at same height → WS-weighted vector mean."""
        base = datetime(2025, 1, 1)
        ts_10 = [base + timedelta(minutes=10 * i) for i in range(6)]
        sensors = _make_sensors([
            ("wd_100", "WindDirection", "", 100.0, "avg"),
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
        ])
        ts = _make_ts(
            ts_10,
            {"wd_100": [350.0, 10.0, 0.0, 5.0, 355.0, 3.0], "ws_100": [10.0] * 6},
            sensors,
        )
        result = _downsample_to_interval(ts, 60.0)
        wd_val = result.df["wd_100"][0]
        # All values near 0° → mean should be near 0°
        assert wd_val == pytest.approx(0.0, abs=5.0) or wd_val == pytest.approx(360.0, abs=5.0)

    def test_downsample_wd_unweighted_fallback(self):
        """10min WD, no WS at same height → unweighted vector mean."""
        base = datetime(2025, 1, 1)
        ts_10 = [base + timedelta(minutes=10 * i) for i in range(6)]
        sensors = _make_sensors([
            ("wd_100", "WindDirection", "", 100.0, "avg"),
        ])
        ts = _make_ts(
            ts_10,
            {"wd_100": [350.0, 10.0, 0.0, 5.0, 355.0, 3.0]},
            sensors,
        )
        result = _downsample_to_interval(ts, 60.0)
        assert "wd_100" in result.df.columns
        wd_val = result.df["wd_100"][0]
        assert wd_val == pytest.approx(0.0, abs=5.0) or wd_val == pytest.approx(360.0, abs=5.0)


# ── Upsampling ────────────────────────────────────────────────────────────


class TestUpsample:
    def test_upsample_ws(self):
        """60min WS data → 10min linear interpolation."""
        base = datetime(2025, 1, 1)
        ts_60 = [base + timedelta(minutes=60 * i) for i in range(3)]
        sensors = _make_sensors([
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
        ])
        ts = _make_ts(ts_60, {"ws_100": [0.0, 10.0, 20.0]}, sensors)
        result = _upsample_to_interval(ts, 10.0)
        vals = result.df["ws_100"].to_list()
        assert len(vals) > 3
        assert vals[0] == pytest.approx(0.0, abs=0.1)

    def test_upsample_wd_circular(self):
        """60min WD crossing north → 10min circular interpolation."""
        base = datetime(2025, 1, 1)
        ts_60 = [base + timedelta(minutes=60 * i) for i in range(3)]
        sensors = _make_sensors([
            ("wd_100", "WindDirection", "", 100.0, "avg"),
        ])
        # 350° → 10° → 30°
        ts = _make_ts(ts_60, {"wd_100": [350.0, 10.0, 30.0]}, sensors)
        result = _upsample_to_interval(ts, 10.0)
        vals = result.df["wd_100"].to_list()
        assert len(vals) > 3
        # Intermediate values should be near 0° (between 350° and 10°)
        for v in vals[:6]:
            assert v < 20.0 or v > 340.0


# ── align_to_interval ─────────────────────────────────────────────────────


class TestAlignToInterval:
    def test_noop_at_target(self):
        """Already at target → returns same data."""
        base = datetime(2025, 1, 1)
        ts_10 = [base + timedelta(minutes=10 * i) for i in range(12)]
        sensors = _make_sensors([
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
        ])
        ts = _make_ts(ts_10, {"ws_100": [5.0] * 12}, sensors)
        result = align_to_interval(ts, 10.0)
        assert len(result.df) == 12

    def test_downsample_integration(self):
        """10min → 60min: 72 points down to ~12."""
        base = datetime(2025, 1, 1)
        ts_10 = [base + timedelta(minutes=10 * i) for i in range(72)]
        sensors = _make_sensors([
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
        ])
        ts = _make_ts(ts_10, {"ws_100": [5.0] * 72}, sensors)
        result = align_to_interval(ts, 60.0)
        assert len(result.df) == 12  # 720min / 60min = 12

    def test_upsample_integration(self):
        """60min → 10min: 12 points up to ~72."""
        base = datetime(2025, 1, 1)
        ts_60 = [base + timedelta(minutes=60 * i) for i in range(12)]
        sensors = _make_sensors([
            ("ws_100", "WindSpeed", "", 100.0, "avg"),
        ])
        ts = _make_ts(ts_60, {"ws_100": [5.0] * 12}, sensors)
        result = align_to_interval(ts, 10.0)
        assert len(result.df) > 12
