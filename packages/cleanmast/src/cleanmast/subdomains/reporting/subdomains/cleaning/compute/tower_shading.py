"""Tower-shading correction statistics (2.3.4 塔影效应处理).

Mirrors the Julia ``TowerShading.Core`` algorithm: at each height with two
or more wind-speed channels (within ±2 m), the tower-shading stage replaces
them with one merged column ``{sensorType}_{height}m_{statType}_{unit}``
holding the per-timestamp maximum of the source channels. This module
identifies those merged heights by comparing the clean and tower-shading
stage column sets, then computes the per-sector before/after comparison
table over the analysis window using the shared sector binning.
"""

from dataclasses import dataclass

import polars as pl

from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.subdomains.reporting.model.sectors import SECTOR_NAMES
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.sector_stats import (
    assign_sector,
)

#: Julia ``find_nearby_sensors`` default: sensors within ±2 m merge together.
NEARBY_HEIGHT_TOLERANCE_M = 2.0


@dataclass(frozen=True)
class DualChannelHeight:
    """One tower-shading-corrected height of a mast.

    Attributes:
        height: Preferred (merged) height in meters, as recorded on the
            merged sensor in the tower-shading stage.
        merged_column: Merged column name ``{sensorType}_{height}m_{statType}_{unit}``
            present in the tower-shading stage and absent from clean.
        source_columns: Clean-stage column names merged into it (ordered by
            column name for deterministic 通道1/通道2 assignment).
        channel_labels: Display labels for the source channels — the sensor
            directions (e.g. "ESE", "WNW") when discoverable, else 通道1/通道2.
    """

    height: float
    merged_column: str
    source_columns: list[str]
    channel_labels: list[str]

    @property
    def is_dual_channel(self) -> bool:
        """True when exactly two source channels were merged."""
        return len(self.source_columns) == 2


def _height_sort_key(height: float) -> tuple[float, float]:
    """Sort integer heights (e.g. 120.0, 140.0) before fractional ones."""
    return (0.0 if height == round(height) else 1.0, height)


def _clip_to_window(
    df: pl.DataFrame,
    window: TimeRange,
    columns: list[str],
) -> pl.DataFrame:
    """Select ``columns`` from a stage frame clipped to the analysis window.

    Timestamp comparison is tz-naive (same convention as
    ``generate_report._clip_input_to_window``).
    """
    selectable = [c for c in columns if c in df.columns]
    if not selectable or "timestamp" not in df.columns:
        return df.head(0)
    start = window.min.replace(tzinfo=None)
    end = window.max.replace(tzinfo=None)
    return df.select(
        pl.col(c) for c in ("timestamp", *selectable)
    ).filter(
        (pl.col("timestamp") >= start) & (pl.col("timestamp") <= end)
    )


def find_dual_channel_heights(
    clean_df: pl.DataFrame,
    shading_df: pl.DataFrame,
    clean_sensors,
    shading_sensors,
) -> list[DualChannelHeight]:
    """Identify tower-shading-corrected heights by column-set comparison.

    A corrected height shows up as a merged column
    ``WindSpeed_{h}m_avg [m/s]`` present in the tower-shading stage whose
    source channels (clean-stage WindSpeed avg columns at the same height,
    Julia ±2 m tolerance) exist in the clean stage.

    Args:
        clean_df: Clean-stage frame (column presence only).
        shading_df: Tower-shading-stage frame (column presence only).
        clean_sensors: ``SensorColumn`` metadata of the clean stage — the
            source-channel registry and the source of channel directions.
        shading_sensors: ``SensorColumn`` metadata of the tower-shading
            stage — carries the merged column's height.

    Returns:
        Dual-channel heights sorted by height; only entries with exactly
        two source channels (单高度双通道).
    """
    clean_cols = set(clean_df.columns)
    shading_cols = set(shading_df.columns)

    # Merged column candidates: avg wind speed, in shading, not in clean.
    merged_sensors = [
        s
        for s in shading_sensors
        if s.sensor_type == "WindSpeed"
        and s.stat_type == "avg"
        and s.column_name in shading_cols
        and s.column_name not in clean_cols
    ]

    # Clean-stage avg wind-speed channels grouped by height.
    clean_ws = [
        s
        for s in clean_sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]

    results: list[DualChannelHeight] = []
    for merged in merged_sensors:
        sources = [
            s
            for s in clean_ws
            if abs(s.height - merged.height) <= NEARBY_HEIGHT_TOLERANCE_M
        ]
        if len(sources) != 2:
            continue
        ordered = sorted(sources, key=lambda s: s.column_name)
        dirs = [s.sensor_direction for s in ordered]
        if dirs[0] and dirs[1] and dirs[0] != dirs[1]:
            labels = [dirs[0], dirs[1]]
        else:
            # Missing or duplicated directions do not identify the channels.
            labels = ["通道1", "通道2"]
        results.append(
            DualChannelHeight(
                height=merged.height,
                merged_column=merged.column_name,
                source_columns=[s.column_name for s in ordered],
                channel_labels=labels,
            )
        )

    results.sort(key=lambda d: _height_sort_key(d.height))
    return results


def tower_shading_sector_stats(
    clean_df: pl.DataFrame,
    shading_df: pl.DataFrame,
    dual: DualChannelHeight,
    wd_column: str,
    window: TimeRange,
) -> pl.DataFrame:
    """Per-sector before/after statistics for one corrected height.

    Both stage frames are clipped to ``window`` first (the boundary already
    clips, this is a second line of defense for directly-built frames).
    Stages align on the 10-minute ``timestamp`` grid; direction comes from
    the clean stage. Rows where the direction or any of the three speed
    values is null are excluded.

    Args:
        clean_df: Clean-stage frame (before correction).
        shading_df: Tower-shading-stage frame (after correction).
        dual: The corrected height (merged + source columns).
        wd_column: Wind direction column name (degrees, avg).
        window: Analysis window for clipping.

    Returns:
        DataFrame sorted by ``sector`` (1–16) with columns ``sector``,
        ``data_points``, ``mean_before_1``, ``mean_before_2``, ``mean_after``
        (m/s). Sectors without observations are omitted.
    """
    needed_clean = [wd_column, *dual.source_columns]
    needed_shading = [dual.merged_column]
    clean = _clip_to_window(clean_df, window, needed_clean)
    shading = _clip_to_window(shading_df, window, needed_shading)

    col1, col2 = dual.source_columns
    joined = (
        clean.join(
            shading,
            on="timestamp",
            how="inner",
        )
        .drop_nulls(subset=[wd_column, col1, col2, dual.merged_column])
    )
    return (
        assign_sector(joined, wd_column)
        .group_by("sector")
        .agg(
            pl.len().alias("data_points"),
            pl.col(col1).mean().alias("mean_before_1"),
            pl.col(col2).mean().alias("mean_before_2"),
            pl.col(dual.merged_column).mean().alias("mean_after"),
        )
        .sort("sector")
    )


def overall_weighted_row(stats_df: pl.DataFrame) -> dict[str, float | int] | None:
    """Sample-count-weighted overall means from per-sector statistics.

    Args:
        stats_df: Output of :func:`tower_shading_sector_stats`.

    Returns:
        Dict with ``data_points`` and the weighted ``mean_before_1``,
        ``mean_before_2``, ``mean_after``; None when ``stats_df`` is empty.
    """
    if stats_df.is_empty():
        return None
    total = int(stats_df["data_points"].sum())
    if total == 0:
        return None
    weights = stats_df["data_points"] / total
    return {
        "data_points": total,
        "mean_before_1": float((stats_df["mean_before_1"] * weights).sum()),
        "mean_before_2": float((stats_df["mean_before_2"] * weights).sum()),
        "mean_after": float((stats_df["mean_after"] * weights).sum()),
    }


OVERALL_ROW_LABEL = "总体平均(加权)"


def _delta_pct(before: float, after: float) -> float | None:
    """Signed relative change ``(after - before) / before``; None at 0."""
    if before == 0:
        return None
    return (after - before) / before


def tower_shading_comparison_frame(
    stats_df: pl.DataFrame,
) -> pl.DataFrame:
    """Build the report-table frame: per-sector rows plus weighted overall.

    Columns: ``sector`` (compass label or ``总体平均(加权)``), ``data_points``,
    ``mean_before_1`` / ``mean_before_2`` / ``mean_after`` (m/s), signed
    ``delta_1`` / ``delta_2`` (m/s, after − before), ``pct_1`` / ``pct_2``
    (relative, null when the before-mean is 0), ``is_overall``.

    Args:
        stats_df: Output of :func:`tower_shading_sector_stats`.

    Returns:
        Frame sorted by sector with the weighted overall row appended;
        empty (no columns beyond schema order) when ``stats_df`` is empty.
    """
    rows: list[dict] = []
    for r in stats_df.iter_rows(named=True):
        rows.append({
            "sector": sector_name(r["sector"]),
            "data_points": r["data_points"],
            "mean_before_1": r["mean_before_1"],
            "mean_before_2": r["mean_before_2"],
            "mean_after": r["mean_after"],
            "delta_1": r["mean_after"] - r["mean_before_1"],
            "delta_2": r["mean_after"] - r["mean_before_2"],
            "pct_1": _delta_pct(r["mean_before_1"], r["mean_after"]),
            "pct_2": _delta_pct(r["mean_before_2"], r["mean_after"]),
            "is_overall": False,
        })
    overall = overall_weighted_row(stats_df)
    if overall is not None:
        rows.append({
            "sector": OVERALL_ROW_LABEL,
            "data_points": overall["data_points"],
            "mean_before_1": overall["mean_before_1"],
            "mean_before_2": overall["mean_before_2"],
            "mean_after": overall["mean_after"],
            "delta_1": overall["mean_after"] - overall["mean_before_1"],
            "delta_2": overall["mean_after"] - overall["mean_before_2"],
            "pct_1": _delta_pct(overall["mean_before_1"], overall["mean_after"]),
            "pct_2": _delta_pct(overall["mean_before_2"], overall["mean_after"]),
            "is_overall": True,
        })
    if not rows:
        return pl.DataFrame(
            schema={
                "sector": pl.String,
                "data_points": pl.Int64,
                "mean_before_1": pl.Float64,
                "mean_before_2": pl.Float64,
                "mean_after": pl.Float64,
                "delta_1": pl.Float64,
                "delta_2": pl.Float64,
                "pct_1": pl.Float64,
                "pct_2": pl.Float64,
                "is_overall": pl.Boolean,
            }
        )
    return pl.DataFrame(rows)


def sector_name(sector_index: int) -> str:
    """16-sector compass label for a 1-indexed sector (1=N … 16=NNW)."""
    return SECTOR_NAMES[sector_index - 1]


def find_avg_wind_direction_column(sensors) -> str | None:
    """Resolve the avg WindDirection column from sensor metadata.

    Mast convention: one avg direction channel (e.g.
    ``WindDirection_100m_N_avg [deg]``); ties resolve to the highest sensor.
    """
    candidates = [
        s
        for s in sensors
        if s.sensor_type == "WindDirection" and s.stat_type == "avg"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda s: s.height).column_name
