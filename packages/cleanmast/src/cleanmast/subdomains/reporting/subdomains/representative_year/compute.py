"""Representative year calibration computation for the reporting domain.

Computes per-sector calibration statistics from raw mast + meso data.
All computation on-the-fly — no pre-trained model loading.
Pure functions only — no IO, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence, cast

import polars as pl
from scipy import stats as scipy_stats

from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.shared.timeseries.alignment import align_to_interval
from cleanmast.subdomains.reporting.subdomains.representative_year.model.sectors import (
    SECTOR_NAMES,
    find_sector,
)

_MIN_DATA_POINTS = 3  # minimum rows per sector for regression


@dataclass(frozen=True)
class RepYearMastSummary:
    """Summary row for one mast-meso pair."""

    mast_name: str
    meso_name: str
    year_range: str  # "YYYYMM~YYYYMM"
    climatology_mean_ws: float
    rep_year_mean_ws: float
    anomaly_percent: float
    needs_correction: bool


@dataclass(frozen=True)
class RepYearSectorRow:
    """One row of the 16-sector table for a mast-meso pair."""

    sector: str
    sector_index: int  # 1-16, clockwise from N
    climatology_mean: float
    rep_year_mean: float
    meso_difference: float  # climatology_mean − rep_year_mean
    slope: float
    intercept: float
    adjustment: float  # slope × meso_difference
    data_points: int


@dataclass(frozen=True)
class RepYearMastResult:
    """Full result for one mast-meso pair that needs calibration."""

    summary: RepYearMastSummary
    height: float  # sensor height (m) for this result
    sectors: list[RepYearSectorRow]  # exactly 16 entries


@dataclass(frozen=True)
class _SectorMesoStats:
    """Per-sector meso statistics from ORIGINAL (unaligned) meso data."""

    sector_index: int  # 1-16
    clim_mean: float   # from ORIGINAL meso
    rep_mean: float    # from ORIGINAL meso
    diff: float        # clim_mean - rep_mean


@dataclass(frozen=True)
class _SectorRegResult:
    """Per-sector regression result from ALIGNED mast-meso data."""

    sector_index: int
    slope: float
    intercept: float
    data_points: int


# ── Helpers ────────────────────────────────────────────────────────────


def _find_highest_windspeed_sensor(sensors: list[SensorColumn]) -> SensorColumn:
    """Find the highest wind speed sensor with stat_type 'avg'."""
    candidates = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]
    if not candidates:
        raise ValueError("No WindSpeed sensor with stat_type 'avg' found")
    return max(candidates, key=lambda s: s.height)


def _find_direction_sensor(sensors: list[SensorColumn]) -> SensorColumn:
    """Find a wind direction sensor with stat_type 'avg'."""
    candidates = [s for s in sensors if s.sensor_type == "WindDirection" and s.stat_type == "avg"]
    if not candidates:
        raise ValueError("No WindDirection sensor with stat_type 'avg' found")
    return candidates[0]


def _find_climatology_timerange(
    min_timestamp: datetime, max_timestamp: datetime,
) -> tuple[datetime, datetime]:
    """Find climatology time range using only complete years (max 30)."""
    min_year = min_timestamp.year
    max_year = max_timestamp.year

    start_year = (
        min_year + 1
        if (min_timestamp - timedelta(days=1)).year == min_year
        else min_year
    )
    end_year = (
        max_year - 1
        if (max_timestamp + timedelta(days=1)).year == max_year
        else max_year
    )

    if end_year < start_year:
        raise ValueError(
            f"No complete years found in dataset. Time range: "
            f"{min_timestamp} to {max_timestamp}"
        )

    year_diff = end_year - start_year + 1
    if year_diff > 30:
        start_year = end_year - 29

    climatology_start = datetime(start_year, 1, 1, 0, 0, 0)
    climatology_end = datetime(end_year, 12, 31, 23, 59, 59)
    return climatology_start, climatology_end


# ── Main computation ───────────────────────────────────────────────────


def _compute_calibration_summary(
    item,
) -> RepYearMastSummary:
    """Compute summary from ORIGINAL (unaligned) meso data + rep-year window.

    Does NOT use aligned data — alignment is for regression only.
    """
    from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput

    assert isinstance(item, SingleMastAnalysisInput)
    payload = item.representative_year_calibration_payload
    assert payload is not None

    meso_ts = payload.meso_time_series
    mast_name = item.mast_name
    meso_name = payload.meso_name

    meso_ws_sensor = _find_highest_windspeed_sensor(meso_ts.sensors)

    # Climatology from meso data
    meso_df = meso_ts.df
    meso_start = cast(datetime, meso_df["timestamp"].min())
    meso_end = cast(datetime, meso_df["timestamp"].max())
    clim_start, clim_end = _find_climatology_timerange(meso_start, meso_end)

    clim_df = meso_df.filter(
        (pl.col("timestamp") >= clim_start) & (pl.col("timestamp") <= clim_end)
    )
    climatology_mean = cast(float, clim_df[meso_ws_sensor.column_name].mean())

    # Rep-year time range from payload (from config AnalysisWindow)
    # Strip timezone — parquet timestamps are timezone-naive
    rep_year_start = payload.rep_year_start.replace(tzinfo=None)
    rep_year_end = payload.rep_year_end.replace(tzinfo=None)

    rep_year_mean_df = meso_df.filter(
        (pl.col("timestamp") >= rep_year_start) & (pl.col("timestamp") <= rep_year_end)
    )
    rep_year_mean = cast(float, rep_year_mean_df[meso_ws_sensor.column_name].mean())

    # Check calibration needed
    anomaly = (rep_year_mean - climatology_mean) / climatology_mean * 100.0
    anomaly = round(anomaly, 2)
    needs_correction = abs(anomaly) > 2.0

    year_range = f"{rep_year_start.year}{rep_year_start.month:02d}~{rep_year_end.year}{rep_year_end.month:02d}"

    return RepYearMastSummary(
        mast_name=mast_name,
        meso_name=meso_name,
        year_range=year_range,
        climatology_mean_ws=round(climatology_mean, 2),
        rep_year_mean_ws=round(rep_year_mean, 2),
        anomaly_percent=anomaly,
        needs_correction=needs_correction,
    )


def _compute_meso_sector_stats(
    payload,
    summary: RepYearMastSummary,
) -> Sequence[_SectorMesoStats]:
    """Compute per-sector meso means from ORIGINAL (unaligned) meso data.

    Uses meso WD for sector assignment on original timestamps.
    """
    meso_ts = payload.meso_time_series
    meso_ws_sensor = _find_highest_windspeed_sensor(meso_ts.sensors)
    meso_wd_sensor = _find_direction_sensor(meso_ts.sensors)
    meso_df = meso_ts.df

    meso_start = cast(datetime, meso_df["timestamp"].min())
    meso_end = cast(datetime, meso_df["timestamp"].max())
    clim_start, clim_end = _find_climatology_timerange(meso_start, meso_end)

    # Strip timezone — parquet timestamps are timezone-naive
    rep_year_start = payload.rep_year_start.replace(tzinfo=None)
    rep_year_end = payload.rep_year_end.replace(tzinfo=None)

    # Add sector assignment on original data
    meso_with_sector = meso_df.with_columns(
        pl.col(meso_wd_sensor.column_name)
        .map_elements(lambda x: find_sector(x) if x is not None else 0, return_dtype=pl.Int32)
        .alias("_sector")
    ).filter(pl.col("_sector") > 0)

    ws_col = meso_ws_sensor.column_name
    stats: list[_SectorMesoStats] = []
    for sector_idx in range(1, 17):
        clim_sector = meso_with_sector.filter(
            (pl.col("_sector") == sector_idx)
            & (pl.col("timestamp") >= clim_start)
            & (pl.col("timestamp") <= clim_end)
        )
        rep_sector = meso_with_sector.filter(
            (pl.col("_sector") == sector_idx)
            & (pl.col("timestamp") >= rep_year_start)
            & (pl.col("timestamp") <= rep_year_end)
        )
        clim_mean = (
            round(cast(float, clim_sector[ws_col].mean()), 2)
            if len(clim_sector) > 0 else 0.0
        )
        rep_mean = (
            round(cast(float, rep_sector[ws_col].mean()), 2)
            if len(rep_sector) > 0 else 0.0
        )
        stats.append(_SectorMesoStats(
            sector_index=sector_idx,
            clim_mean=clim_mean,
            rep_mean=rep_mean,
            diff=round(clim_mean - rep_mean, 2),
        ))
    return stats


def _compute_per_sector_regression(
    mast_aligned: TimeSeriesData,
    meso_aligned: TimeSeriesData,
    mast_ws_sensor: SensorColumn,
    meso_ws_sensor: SensorColumn,
    meso_wd_sensor: SensorColumn,
    train_min: datetime,
    train_max: datetime,
) -> Sequence[_SectorRegResult]:
    """Compute per-sector linear regression from ALIGNED mast-meso data.

    Alignment happens upstream in _compute_sector_regression orchestrator.
    """
    mast_ws_col = mast_ws_sensor.column_name
    meso_ws_col = meso_ws_sensor.column_name

    # Join aligned dataframes
    aligned_df = mast_aligned.df.select(["timestamp", mast_ws_col]).join(
        meso_aligned.df, on="timestamp", how="inner"
    )

    # Add sector assignment
    aligned_df = aligned_df.with_columns(
        pl.col(meso_wd_sensor.column_name)
        .map_elements(lambda x: find_sector(x) if x is not None else 0, return_dtype=pl.Int32)
        .alias("_sector")
    ).filter(pl.col("_sector") > 0)

    # Filter to training period
    train_df = aligned_df.filter(
        (pl.col("timestamp") >= train_min) & (pl.col("timestamp") <= train_max)
    )

    results: list[_SectorRegResult] = []
    for sector_idx in range(1, 17):
        train_sector = train_df.filter(pl.col("_sector") == sector_idx)
        n_points = len(train_sector)
        if n_points >= _MIN_DATA_POINTS:
            x = train_sector[meso_ws_col].to_numpy()
            y = train_sector[mast_ws_col].to_numpy()
            mask = ~(pl.Series(x).is_null() | pl.Series(y).is_null())
            x_clean, y_clean = x[mask], y[mask]
            if len(x_clean) >= _MIN_DATA_POINTS:
                reg = scipy_stats.linregress(x_clean, y_clean)
                results.append(_SectorRegResult(
                    sector_index=sector_idx,
                    slope=round(reg.slope, 4),
                    intercept=round(reg.intercept, 4),
                    data_points=len(x_clean),
                ))
            else:
                results.append(_SectorRegResult(
                    sector_index=sector_idx, slope=0.0, intercept=0.0, data_points=0,
                ))
        else:
            results.append(_SectorRegResult(
                sector_index=sector_idx, slope=0.0, intercept=0.0, data_points=0,
            ))
    return results


def _combine_sector_rows(
    sector_stats: Sequence[_SectorMesoStats],
    reg_results: Sequence[_SectorRegResult],
    height: float,
) -> list[RepYearSectorRow]:
    """Zip sector statistics and regression results by sector_index."""
    rows: list[RepYearSectorRow] = []
    for stat, reg in zip(sector_stats, reg_results):
        adjustment = round(reg.slope * stat.diff, 4)
        rows.append(RepYearSectorRow(
            sector=SECTOR_NAMES[stat.sector_index - 1],
            sector_index=stat.sector_index,
            climatology_mean=stat.clim_mean,
            rep_year_mean=stat.rep_mean,
            meso_difference=stat.diff,
            slope=reg.slope,
            intercept=reg.intercept,
            adjustment=adjustment,
            data_points=reg.data_points,
        ))
    return rows


def _compute_sector_regression(
    item,
    summary: RepYearMastSummary,
) -> list[RepYearMastResult]:
    """Orchestrate per-sector regression for one mast-meso pair.

    Alignment happens HERE — only for regression, NOT for summary stats.
    """
    from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput

    assert isinstance(item, SingleMastAnalysisInput)
    payload = item.representative_year_calibration_payload
    assert payload is not None

    mast_ts = item.time_series
    meso_ts = payload.meso_time_series

    # Qualifying mast WS sensors — filtered to configured analysis_heights
    analysis_heights_set = set(item.parameters.analysis_heights)
    mast_ws_sensors = [
        s for s in mast_ts.sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
        and s.height in analysis_heights_set
        and s.detect_interpolation_marker() == ""
    ]
    if not mast_ws_sensors:
        return []

    meso_ws_sensor = _find_highest_windspeed_sensor(meso_ts.sensors)
    meso_wd_sensor = _find_direction_sensor(meso_ts.sensors)

    # Training time range from mast data
    mast_df = mast_ts.df
    train_min = cast(datetime, mast_df["timestamp"].min())
    train_max = cast(datetime, mast_df["timestamp"].max())

    # Align mast and meso to common interval for regression
    sampling_minutes = _parse_sampling_period(payload.sampling_period)
    aligned_mast = align_to_interval(mast_ts, sampling_minutes)
    aligned_meso = align_to_interval(meso_ts, sampling_minutes)

    # Per-sector meso stats from ORIGINAL data (once, shared across heights)
    sector_stats = _compute_meso_sector_stats(payload, summary)

    results: list[RepYearMastResult] = []
    for mast_ws_sensor in mast_ws_sensors:
        reg_results = _compute_per_sector_regression(
            aligned_mast, aligned_meso,
            mast_ws_sensor, meso_ws_sensor, meso_wd_sensor,
            train_min, train_max,
        )
        rows = _combine_sector_rows(sector_stats, reg_results, mast_ws_sensor.height)
        results.append(RepYearMastResult(
            summary=summary, height=mast_ws_sensor.height, sectors=rows,
        ))
    return results


def analyze_representative_year_calibration(
    inputs: list,
) -> tuple[list[RepYearMastSummary], list[RepYearMastResult]]:
    """Analyze representative year calibration for all provided masts.

    Summary stats use ORIGINAL data. Regression uses ALIGNED data.
    """
    summaries: list[RepYearMastSummary] = []
    results: list[RepYearMastResult] = []

    for item in inputs:
        payload = item.representative_year_calibration_payload
        if payload is None:
            continue

        summary = _compute_calibration_summary(item)
        summaries.append(summary)

        if summary.needs_correction:
            results.extend(_compute_sector_regression(item, summary))

    return summaries, results


def _parse_sampling_period(sampling_period: str) -> float:
    """Parse sampling period string to minutes."""
    sp = sampling_period.strip().lower()
    if sp == "10min":
        return 10.0
    elif sp == "1h" or sp == "60min":
        return 60.0
    else:
        raise ValueError(
            f"Unsupported sampling_period: '{sampling_period}'. "
            "Expected '10min' or '1h'."
        )
