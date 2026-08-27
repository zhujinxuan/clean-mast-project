"""Pairwise scatter-panel computation for the imputation subsections.

Shared machinery for 2.3.5 同塔 / 2.3.6 异塔 / 2.3.7 中尺度: resolve the
corrected measured series (tower-shading output when present, else the
process-clean output), align frames on timestamps, and compute per-panel
OLS statistics via the shared ``linear_regression`` / ``correlation_matrix``
helpers. Pure polars math — no IO, no path resolution (stage series are
loaded and clipped at the ``load_datasets`` boundary).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

import polars as pl

from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.shared.timeseries.alignment import align_to_interval
from cleanmast.subdomains.reporting.model.analysis_input import (
    CleaningAnalysisPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.height_label import (
    get_height_display_name,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.correlation import (
    correlation_matrix,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.regression import (
    linear_regression,
)

#: Minimum complete pairs for a regression panel — mirrors the
#: representative-year ``_MIN_DATA_POINTS`` threshold.
MIN_PAIRS = 3

_SAMPLING_MINUTES: dict[str, float] = {"10min": 10.0, "1h": 60.0}

_PAIR_COLUMNS = {
    "x_label": pl.String,
    "y_label": pl.String,
    "x": pl.Float64,
    "y": pl.Float64,
}

_STAT_COLUMNS = {
    "x_label": pl.String,
    "y_label": pl.String,
    "slope": pl.Float64,
    "intercept": pl.Float64,
    "r": pl.Float64,
    "rmse": pl.Float64,
    "n_pairs": pl.Int64,
}

_MATRIX_COLUMNS = {
    "x_label": pl.String,
    "y_label": pl.String,
    "r": pl.Float64,
}


@dataclass(frozen=True)
class SameTowerResult:
    """Per-mast 2.3.5 exhibits data."""

    mast_name: str
    labels: list[str]  # ordered height labels, rows and columns
    matrix_long: pl.DataFrame  # full square incl. diagonal, keyed by labels
    panels: pl.DataFrame  # OLS stats per upper-triangle panel
    pairs: pl.DataFrame  # tidy scatter points per upper-triangle panel


@dataclass(frozen=True)
class CrossMastResult:
    """Per-ordered-mast-pair 2.3.6 exhibits data (y = mast_a, x = mast_b)."""

    mast_a: str
    mast_b: str
    x_labels: list[str]  # mast_b height labels (columns)
    y_labels: list[str]  # mast_a height labels (rows)
    panels: pl.DataFrame
    pairs: pl.DataFrame


@dataclass(frozen=True)
class MesoResult:
    """Per-mast 2.3.7 exhibits data (y = mast height, x = meso WS)."""

    mast_name: str
    meso_name: str
    y_labels: list[str]  # mast height labels (panels)
    panels: pl.DataFrame
    pairs: pl.DataFrame


def empty_pairs_frame() -> pl.DataFrame:
    """Schema-typed empty tidy-pairs frame (concat base for empty inputs)."""
    return pl.DataFrame(schema=_PAIR_COLUMNS)


def empty_stats_frame() -> pl.DataFrame:
    """Schema-typed empty panel-stats frame."""
    return pl.DataFrame(schema=_STAT_COLUMNS)


def resolve_ws_columns(
    sensors: list[SensorColumn],
    heights: list[float],
    df_columns: list[str],
) -> dict[float, str]:
    """Map each requested height to its WS avg column in the stage frame.

    Duplicate sensors at one height (e.g. boom N/S before tower-shading
    merges them) resolve deterministically to the first column name.
    Heights without a sensor or without a matching DataFrame column are
    dropped.
    """
    resolved: dict[float, str] = {}
    for height in heights:
        candidates = sorted(
            s.column_name
            for s in sensors
            if s.sensor_type == "WindSpeed"
            and s.stat_type == "avg"
            and s.height == height
            and s.column_name in df_columns
        )
        if candidates:
            resolved[height] = candidates[0]
    return resolved


def corrected_stage_series(
    payload: CleaningAnalysisPayload,
) -> TimeSeriesData | None:
    """The corrected measured series: tower-shading output, else clean output."""
    if payload.tower_shading_series is not None:
        return payload.tower_shading_series
    return payload.clean_series


def height_labels(heights: list[float]) -> list[str]:
    """Display labels for ordered heights (e.g. ``120m``)."""
    return [get_height_display_name(h) for h in heights]


def _labeled_frame(
    stage: TimeSeriesData,
    resolved: dict[float, str],
    label_prefix: str = "",
) -> tuple[pl.DataFrame, list[str]]:
    """Stage frame slimmed to ``timestamp`` + one column per height label.

    Labels carry an optional mast prefix so frames from different masts
    join without column-name collisions.
    """
    heights = sorted(resolved)
    labels = [f"{label_prefix}{lbl}" for lbl in height_labels(heights)]
    slim = stage.df.select(
        ["timestamp"]
        + [pl.col(resolved[h]).alias(lbl) for h, lbl in zip(heights, labels)]
    )
    return slim, labels


def upper_triangle(labels: list[str]) -> list[tuple[str, str]]:
    """(x, y) label pairs above the diagonal, row-major order."""
    return [
        (labels[j], labels[i])
        for i in range(len(labels))
        for j in range(i + 1, len(labels))
    ]


def rectangle_pairs(
    x_labels: list[str],
    y_labels: list[str],
) -> list[tuple[str, str]]:
    """All (x, y) label pairs across two ordered label lists."""
    return [(x, y) for y in y_labels for x in x_labels]


def tidy_pairs(
    df: pl.DataFrame,
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
) -> pl.DataFrame:
    """Complete (non-null) value pairs tagged with panel labels."""
    return df.select(
        pl.lit(x_label, dtype=pl.String).alias("x_label"),
        pl.lit(y_label, dtype=pl.String).alias("y_label"),
        pl.col(x_col).cast(pl.Float64).alias("x"),
        pl.col(y_col).cast(pl.Float64).alias("y"),
    ).drop_nulls()


def panel_stats(pairs: pl.DataFrame) -> pl.DataFrame:
    """One-row stats frame for a tidy-pairs frame, empty when unregressable.

    ``linear_regression`` failures (too few pairs, zero variance) map to
    an empty frame — the panel is skipped, not crashed on.
    """
    if pairs.height < MIN_PAIRS:
        return empty_stats_frame()
    try:
        reg = linear_regression(pairs, "x", "y")
    except ValueError:
        return empty_stats_frame()
    return pl.DataFrame(
        {
            "x_label": [pairs["x_label"][0]],
            "y_label": [pairs["y_label"][0]],
            "slope": [reg.slope],
            "intercept": [reg.intercept],
            "r": [reg.r],
            "rmse": [reg.rmse],
            "n_pairs": [reg.n],
        },
        schema=_STAT_COLUMNS,
    )


def build_panels(
    joined: pl.DataFrame,
    label_pairs: list[tuple[str, str]],
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Stats + tidy pairs for each (x_label, y_label) on a labeled frame.

    The frame's value columns ARE the labels. Panels whose complete-pair
    count falls below ``MIN_PAIRS`` contribute no stats and no points.
    """
    stats: list[pl.DataFrame] = []
    pairs: list[pl.DataFrame] = []
    for x_label, y_label in label_pairs:
        panel = tidy_pairs(joined, x_label, y_label, x_label, y_label)
        stat = panel_stats(panel)
        if stat.is_empty():
            continue
        stats.append(stat)
        pairs.append(panel)
    if not stats:
        return empty_stats_frame(), empty_pairs_frame()
    return pl.concat(stats), pl.concat(pairs)


def _highest_ws_column(sensors: list[SensorColumn]) -> str | None:
    """Highest WS avg sensor column (meso frames carry one WS level)."""
    candidates = [
        s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda s: s.height).column_name


def _sampling_minutes(sampling_period: str) -> float:
    try:
        return _SAMPLING_MINUTES[sampling_period]
    except KeyError:
        raise ValueError(
            f"unsupported meso sampling_period '{sampling_period}' "
            f"(expected one of {sorted(_SAMPLING_MINUTES)})"
        ) from None


def _matrix_long(
    stage: TimeSeriesData,
    columns: list[str],
    labels: list[str],
) -> pl.DataFrame:
    """Full-square correlation matrix melted to long label-keyed rows."""
    wide = correlation_matrix(stage.df, columns)
    col_to_label = dict(zip(columns, labels))
    rows: list[dict[str, object]] = []
    for row_col in columns:
        value_row = wide.filter(pl.col("column") == row_col)
        for col_col in columns:
            value = value_row.select(pl.col(col_col)).item()
            if value is not None and value != value:  # NaN → null
                value = None
            rows.append(
                {
                    "x_label": col_to_label[col_col],
                    "y_label": col_to_label[row_col],
                    "r": value,
                }
            )
    return pl.DataFrame(rows, schema=_MATRIX_COLUMNS)


def analyze_same_tower(
    items: list[SingleMastAnalysisInput],
) -> list[SameTowerResult]:
    """2.3.5: pairwise height correlations on each mast's corrected series.

    Masts without a cleaning payload, without a corrected stage series, or
    with fewer than two resolvable heights are skipped.
    """
    results: list[SameTowerResult] = []
    for item in items:
        payload = item.cleaning_payload
        if payload is None:
            continue
        stage = corrected_stage_series(payload)
        if stage is None:
            continue
        resolved = resolve_ws_columns(
            stage.sensors, payload.cleaning_heights, stage.df.columns
        )
        if len(resolved) < 2:
            continue
        labeled, labels = _labeled_frame(stage, resolved)
        panels, pairs = build_panels(labeled, upper_triangle(labels))
        if panels.is_empty():
            continue
        results.append(
            SameTowerResult(
                mast_name=item.mast_name,
                labels=labels,
                matrix_long=_matrix_long(stage, [resolved[h] for h in sorted(resolved)], labels),
                panels=panels,
                pairs=pairs,
            )
        )
    return results


def analyze_cross_mast(
    items: list[SingleMastAnalysisInput],
) -> list[CrossMastResult]:
    """2.3.6: rectangle correlations for each ordered mast pair.

    y panels come from ``mast_a``'s heights, x panels from ``mast_b``'s,
    inner-joined on overlapping timestamps of the corrected series. Pairs
    with no regressable panel (no overlap, or below ``MIN_PAIRS`` on every
    panel) are skipped.
    """
    stages: dict[str, tuple[TimeSeriesData, dict[float, str]]] = {}
    for item in items:
        payload = item.cleaning_payload
        if payload is None:
            continue
        stage = corrected_stage_series(payload)
        if stage is None:
            continue
        resolved = resolve_ws_columns(
            stage.sensors, payload.cleaning_heights, stage.df.columns
        )
        if resolved:
            stages[item.mast_name] = (stage, resolved)
    if len(stages) < 2:
        return []

    frames: dict[str, tuple[pl.DataFrame, list[str]]] = {
        name: _labeled_frame(stage, resolved, label_prefix=f"{name} ")
        for name, (stage, resolved) in stages.items()
    }

    results: list[CrossMastResult] = []
    for mast_a, mast_b in permutations(dict.fromkeys(frames), 2):
        frame_a, y_labels = frames[mast_a]
        frame_b, x_labels = frames[mast_b]
        joined = frame_a.join(frame_b, on="timestamp", how="inner")
        panels, pairs = build_panels(joined, rectangle_pairs(x_labels, y_labels))
        if panels.is_empty():
            continue
        results.append(
            CrossMastResult(
                mast_a=mast_a,
                mast_b=mast_b,
                x_labels=x_labels,
                y_labels=y_labels,
                panels=panels,
                pairs=pairs,
            )
        )
    return results


def analyze_meso(items: list[SingleMastAnalysisInput]) -> list[MesoResult]:
    """2.3.7: mast heights vs the selected ERA5 source per mast.

    Follows the representative-year convention: both series aligned to the
    meso payload's sampling interval, then inner-joined on timestamps.
    Masts without a meso payload or corrected stage series are skipped.
    """
    results: list[MesoResult] = []
    for item in items:
        payload = item.cleaning_payload
        meso_payload = item.representative_year_calibration_payload
        if payload is None or meso_payload is None:
            continue
        stage = corrected_stage_series(payload)
        if stage is None:
            continue
        resolved = resolve_ws_columns(
            stage.sensors, payload.cleaning_heights, stage.df.columns
        )
        if not resolved:
            continue

        meso_ts = meso_payload.meso_time_series
        meso_ws_col = _highest_ws_column(meso_ts.sensors)
        if meso_ws_col is None or meso_ws_col not in meso_ts.df.columns:
            continue
        minutes = _sampling_minutes(meso_payload.sampling_period)
        aligned_mast = align_to_interval(stage, minutes)
        aligned_meso = align_to_interval(meso_ts, minutes)
        meso_label = meso_payload.meso_name
        labeled, labels = _labeled_frame(aligned_mast, resolved)
        joined = labeled.join(
            aligned_meso.df.select(
                ["timestamp", pl.col(meso_ws_col).alias(meso_label)]
            ),
            on="timestamp",
            how="inner",
        )

        panels, pairs = build_panels(
            joined, rectangle_pairs([meso_label], labels)
        )
        if panels.is_empty():
            continue
        results.append(
            MesoResult(
                mast_name=item.mast_name,
                meso_name=meso_payload.meso_name,
                y_labels=labels,
                panels=panels,
                pairs=pairs,
            )
        )
    return results
