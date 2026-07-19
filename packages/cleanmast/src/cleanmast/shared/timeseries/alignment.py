"""Unified timeseries alignment with circular wind direction interpolation.

Resamples mast and meso timeseries to a common interval, handling:
- WindSpeed: arithmetic mean (downsample) / linear interpolation (upsample)
- WindDirection: WS-weighted u/v vector mean (downsample) / standard u/v interpolation (upsample)

Wind direction uses sin/cos decomposition to handle the 0°/360° circular boundary.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import cast

import polars as pl

from cleanmast.shared.timeseries.sensor_column import SensorColumn
from cleanmast.shared.timeseries.time_series_data import TimeSeriesData

log = logging.getLogger(__name__)

_TOLERANCE = 0.01  # ±1% of target interval → treated as "equal"


# ── Public API ────────────────────────────────────────────────────────────


def align_to_interval(
    ts: TimeSeriesData, target_interval_minutes: float
) -> TimeSeriesData:
    """Align a timeseries to a target interval.

    Steps:
      1. Compute native interval
      2. Filter to avg WindSpeed/WindDirection sensors (exclude interpolated fills)
      3. Build filtered TimeSeriesData
      4. Downsample, upsample, or return as-is
    """
    if len(ts.df) < 2:
        log.warning("Timeseries has <2 rows, cannot compute interval; returning as-is")
        return ts

    actual = _compute_native_interval(ts.df)
    filtered_sensors = _filter_avg_sensors(ts)

    if not filtered_sensors:
        log.warning("All sensors filtered out; returning original timeseries")
        return ts

    col_names = [s.column_name for s in filtered_sensors]
    slim_df = ts.df.select(["timestamp"] + col_names)
    ts_filtered = TimeSeriesData(df=slim_df, sensors=filtered_sensors)

    lo = target_interval_minutes * (1 - _TOLERANCE)
    hi = target_interval_minutes * (1 + _TOLERANCE)

    if actual > hi:
        return _upsample_to_interval(ts_filtered, target_interval_minutes)
    elif actual < lo:
        return _downsample_to_interval(ts_filtered, target_interval_minutes)
    else:
        return ts_filtered


# ── Interval computation ──────────────────────────────────────────────────


def _compute_native_interval(df: pl.DataFrame) -> float:
    """Compute the most common time delta between consecutive timestamps (minutes)."""
    diffs = (
        df.select("timestamp")
        .sort("timestamp")
        .with_columns(pl.col("timestamp").diff().alias("diff_ts"))
        .drop_nulls()
        .with_columns(pl.col("diff_ts").dt.total_milliseconds().alias("ms"))
    )
    if len(diffs) == 0:
        raise ValueError("Cannot compute interval from a single-row DataFrame")

    mode_ms = diffs.group_by("ms").agg(pl.len().alias("count")).sort("count", descending=True)["ms"][0]
    return float(mode_ms / 60_000)


# ── Sensor filtering ──────────────────────────────────────────────────────


def _filter_avg_sensors(
    ts: TimeSeriesData,
    sensor_types: tuple[str, ...] = ("WindSpeed", "WindDirection"),
) -> list[SensorColumn]:
    """Keep only avg sensors of the given types, excluding interpolated fills."""
    return [
        s
        for s in ts.sensors
        if s.sensor_type in sensor_types
        and s.stat_type == "avg"
        and s.detect_interpolation_marker() == ""
    ]


# ── u/v helper functions ──────────────────────────────────────────────────


def _add_uv_helpers(
    df: pl.DataFrame,
    wd_col: str,
    height: float,
    ws_col: str | None = None,
) -> pl.DataFrame:
    """Add u/v helper columns for circular wind direction operations.

    Columns added: u_{height}m_helper, v_{height}m_helper.
    If ws_col provided, also adds ws_{height}m_helper.
    """
    h = int(height)
    rad = pl.col(wd_col).radians()
    cols = [
        rad.sin().alias(f"u_{h}m_helper"),
        rad.cos().alias(f"v_{h}m_helper"),
    ]
    if ws_col is not None:
        cols.append(pl.col(ws_col).alias(f"ws_{h}m_helper"))
    return df.with_columns(cols)


def _compute_from_uv(
    u_expr: pl.Expr,
    v_expr: pl.Expr,
    wd_col: str,
) -> pl.Expr:
    """Reconstruct wind direction from u/v expressions, normalized to [0, 360)."""
    return (
        (pl.arctan2(u_expr, v_expr).degrees() % 360)
        .alias(wd_col)
    )


def _drop_uv_helpers(df: pl.DataFrame, height: float) -> pl.DataFrame:
    """Drop all u/v/ws helper columns for the given height."""
    h = int(height)
    helpers = [f"u_{h}m_helper", f"v_{h}m_helper", f"ws_{h}m_helper"]
    existing = [c for c in helpers if c in df.columns]
    return df.drop(existing)


# ── Nearest WS finder ─────────────────────────────────────────────────────


def _find_nearest_ws(
    wd_height: float, wind_speed_sensors: list[SensorColumn]
) -> SensorColumn:
    """Find nearest-height WS sensor. If two equidistant, pick the higher one."""
    return min(
        wind_speed_sensors,
        key=lambda s: (abs(s.height - wd_height), -s.height),
    )


def _build_wd_to_ws_map(sensors: list[SensorColumn]) -> dict[str, str]:
    """Map each WD column_name to its nearest WS column_name."""
    ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed"]
    if not ws_sensors:
        return {}
    return {
        s.column_name: _find_nearest_ws(s.height, ws_sensors).column_name
        for s in sensors
        if s.sensor_type == "WindDirection"
    }


# ── Downsampling ──────────────────────────────────────────────────────────


def _downsample_to_interval(
    ts: TimeSeriesData, target_interval: float
) -> TimeSeriesData:
    """Downsample a timeseries to a longer interval.

    WindSpeed: arithmetic mean.
    WindDirection: WS-weighted u/v vector mean via nearest-height pairing.
    """
    df = ts.df.sort("timestamp")
    wd_to_ws = _build_wd_to_ws_map(ts.sensors)

    # Add u/v helpers for WD columns (and optionally ws helpers)
    # Add u/v helpers for WD columns
    for s in ts.sensors:
        if s.sensor_type == "WindDirection":
            ws_col = wd_to_ws.get(s.column_name)
            df = _add_uv_helpers(df, s.column_name, s.height, ws_col)

    # Build aggregation expressions
    aggs: list[pl.Expr] = []
    for s in ts.sensors:
        if s.sensor_type == "WindSpeed":
            aggs.append(pl.col(s.column_name).mean())
        elif s.sensor_type == "WindDirection":
            h = int(s.height)
            ws_col = wd_to_ws.get(s.column_name)
            u_h = f"u_{h}m_helper"
            v_h = f"v_{h}m_helper"
            if ws_col:
                # Weighted: sum(ws * u) / sum(ws), with fallback if sum(ws) == 0
                wu = f"_wu_{h}"
                wv = f"_wv_{h}"
                wt = f"_wt_{h}"
                ws_h = f"ws_{h}m_helper"
                df = df.with_columns([
                    (pl.col(ws_h) * pl.col(u_h)).alias(wu),
                    (pl.col(ws_h) * pl.col(v_h)).alias(wv),
                    pl.col(ws_h).alias(wt),
                ])
                aggs.append(
                    pl.when(pl.col(wt).sum() > 0)
                    .then(pl.col(wu).sum() / pl.col(wt).sum())
                    .otherwise(pl.col(u_h).mean())
                    .alias(f"_agg_u_{h}")
                )
                aggs.append(
                    pl.when(pl.col(wt).sum() > 0)
                    .then(pl.col(wv).sum() / pl.col(wt).sum())
                    .otherwise(pl.col(v_h).mean())
                    .alias(f"_agg_v_{h}")
                )
            else:
                # Unweighted fallback: simple mean of u/v
                aggs.append(pl.col(u_h).mean().alias(f"_agg_u_{h}"))
                aggs.append(pl.col(v_h).mean().alias(f"_agg_v_{h}"))
    grouped = df.group_by_dynamic("timestamp", every=f"{int(target_interval)}m").agg(aggs)

    # Reconstruct WD from aggregated u/v
    for s in ts.sensors:
        if s.sensor_type == "WindDirection":
            h = int(s.height)
            grouped = grouped.with_columns(
                _compute_from_uv(
                    pl.col(f"_agg_u_{h}"),
                    pl.col(f"_agg_v_{h}"),
                    s.column_name,
                )
            )
            grouped = grouped.drop([f"_agg_u_{h}", f"_agg_v_{h}"])

    # Drop all helper columns
    for s in ts.sensors:
        if s.sensor_type == "WindDirection":
            grouped = _drop_uv_helpers(grouped, s.height)

    return TimeSeriesData(df=grouped, sensors=ts.sensors)


# ── Upsampling ────────────────────────────────────────────────────────────


def _upsample_to_interval(
    ts: TimeSeriesData, target_interval: float
) -> TimeSeriesData:
    """Upsample a timeseries to a shorter interval.

    WindSpeed: linear interpolation.
    WindDirection: standard u/v circular interpolation via Polars interpolate().
    """
    df = ts.df.sort("timestamp")

    # Generate uniform timestamp grid using Python datetime arithmetic
    # (avoids Polars datetime_range typing issues)
    target_interval_td = timedelta(minutes=target_interval)
    t_min = cast(datetime, df["timestamp"].min())
    t_max = cast(datetime, df["timestamp"].max())
    n_points = int((t_max - t_min).total_seconds() / (target_interval * 60)) + 1
    timestamps = [t_min + target_interval_td * i for i in range(n_points)]
    grid = pl.DataFrame({"timestamp": timestamps})

    # Join original data onto grid (creates nulls at target timestamps)
    merged = grid.join(df, on="timestamp", how="left")

    # Interpolate WindSpeed columns
    for s in ts.sensors:
        if s.sensor_type == "WindSpeed":
            merged = merged.with_columns(pl.col(s.column_name).interpolate())

    # Interpolate WindDirection columns via u/v decomposition
    for s in ts.sensors:
        if s.sensor_type == "WindDirection":
            merged = _add_uv_helpers(merged, s.column_name, s.height)
            h = int(s.height)
            merged = merged.with_columns([
                pl.col(f"u_{h}m_helper").interpolate(),
                pl.col(f"v_{h}m_helper").interpolate(),
            ])
            merged = merged.with_columns(
                _compute_from_uv(
                    pl.col(f"u_{h}m_helper"),
                    pl.col(f"v_{h}m_helper"),
                    s.column_name,
                )
            )
            merged = _drop_uv_helpers(merged, s.height)

    # Drop extrapolated edges (leading/trailing nulls remain after interpolate)
    merged = merged.drop_nulls()

    return TimeSeriesData(df=merged, sensors=ts.sensors)
