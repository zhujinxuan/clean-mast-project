"""Assembly functions for cleaning capability atoms.

Pure functions only — NO IO, no side effects. Wave 1 assembles a single
placeholder atom per subsection; Wave 2 extends this with the real
coverage / violation / regression atoms.
"""

import re
from collections.abc import Sequence
from datetime import datetime

import polars as pl

from cleanmast.shared.timeseries.sensor_column import SensorColumn
from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_data import TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.coverage import (
    count_valid_points,
    expected_points,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.scatter_pairs import (
    CrossMastResult,
    MesoResult,
    SameTowerResult,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.tower_shading import (
    find_avg_wind_direction_column,
    find_dual_channel_heights,
    tower_shading_comparison_frame,
    tower_shading_sector_stats,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model import (
    FLOW_INTRO_TEXT,
    TOWER_SHADING_METHOD_TEXT,
    TOWER_SHADING_METHOD_TEXT_NO_TABLE,
    CleaningAtomMeta,
    CleaningCoverageAtom,
    CleaningCoverageSchema,
    CleaningFlowIntroAtom,
    CleaningPlaceholderAtom,
    CleaningPlaceholderSchema,
    CleaningRulesAtom,
    CleaningRulesAtomMeta,
    CleaningRulesSchema,
    CleaningViolationsAtom,
    CleaningViolationsAtomMeta,
    CleaningViolationsSchema,
    CorrelationLongSchema,
    CorrelationMatrixAtom,
    CorrelationMatrixAtomMeta,
    EnabledCleaningRules,
    MastViolationStats,
    ScatterPanelSchema,
    ScatterRegressionAtom,
    ScatterRegressionAtomMeta,
    TowerShadingMethodAtom,
    TowerShadingMethodAtomMeta,
    TowerShadingMethodSchema,
    TowerShadingSectorSchema,
    TowerShadingSectorTableAtom,
    TowerShadingSectorTableAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.constants import (
    format_sensor_label,
    sensor_row_sort_key,
)


def build_cleaning_placeholder_atoms(
    mast_names: list[str],
    text: str,
) -> list[ReportAtom]:
    """Build the one-line placeholder atom for a 2.3.x subsection.

    Args:
        mast_names: Masts the subsection covers.
        text: Placeholder line rendered as the subsection body.

    Returns:
        A single-atom list so report generation succeeds end-to-end.
    """
    df = pl.DataFrame({"text": [text]})
    meta = CleaningAtomMeta(mast_names=list(mast_names), text=text)
    return [
        CleaningPlaceholderAtom.create(
            schema=CleaningPlaceholderSchema,
            df=df,
            meta=meta,
        )
    ]


def build_cleaning_overview_atoms(
    items: list[SingleMastAnalysisInput],
) -> list[ReportAtom]:
    """Build the 2.3.2 atoms: flow intro paragraph + stage coverage table.

    Args:
        items: One SingleMastAnalysisInput per cleaning-dataset mast. Masts
            whose ``cleaning_payload`` is None are skipped gracefully; the
            flow intro still renders.

    Returns:
        The flow-intro atom always; the coverage atom (stats sentence +
        point-count table) only when at least one mast has a payload.
        Stage series are the payload's pre-clipped ``*_series`` fields —
        no IO happens here.
    """
    mast_names = [item.mast_name for item in items]
    atoms: list[ReportAtom] = [
        CleaningFlowIntroAtom.create(
            schema=CleaningPlaceholderSchema,
            df=pl.DataFrame({"text": [FLOW_INTRO_TEXT]}),
            meta=CleaningAtomMeta(mast_names=mast_names, text=FLOW_INTRO_TEXT),
        )
    ]
    rows = _coverage_rows(items)
    if not rows:
        return atoms
    atoms.append(
        CleaningCoverageAtom.create(
            schema=CleaningCoverageSchema,
            df=pl.DataFrame(
                {
                    "mast_name": [r["mast_name"] for r in rows],
                    "height": [r["height"] for r in rows],
                    "expected_points": [r["expected_points"] for r in rows],
                    "raw_points": [r["raw_points"] for r in rows],
                    "clean_points": [r["clean_points"] for r in rows],
                    "final_points": [r["final_points"] for r in rows],
                },
                schema={
                    "mast_name": pl.String,
                    "height": pl.Float64,
                    "expected_points": pl.Int64,
                    "raw_points": pl.Int64,
                    "clean_points": pl.Int64,
                    "final_points": pl.Int64,
                },
            ),
            meta=CleaningAtomMeta(mast_names=mast_names, text=_stats_sentence(items)),
        )
    )
    return atoms


def _coverage_rows(
    items: list[SingleMastAnalysisInput],
) -> list[dict[str, object]]:
    """One row per mast × cleaning height with stage valid-point counts.

    Counts reuse ``compute.coverage`` against each stage's own sensor
    metadata: the column at a height is resolved from the stage's
    WindSpeed/avg sensors (dual-channel heights take the channel with the
    most valid points — coverage measures availability). The 清洗后 column
    counts tower-shading output when present, else process-clean output.
    A missing stage series yields None (rendered as —); heights come from
    ``cleaning_heights`` only.
    """
    rows: list[dict[str, object]] = []
    for item in items:
        payload = item.cleaning_payload
        if payload is None:
            continue
        window = payload.analysis_window
        clean_stage = (
            payload.tower_shading_series
            if payload.tower_shading_series is not None
            else payload.clean_series
        )
        expected = expected_points(window)
        for height in sorted(payload.cleaning_heights):
            rows.append({
                "mast_name": item.mast_name,
                "height": height,
                "expected_points": expected,
                "raw_points": _stage_valid_points(payload.raw_series, height, window),
                "clean_points": _stage_valid_points(clean_stage, height, window),
                "final_points": _stage_valid_points(item.time_series, height, window),
            })
    return rows


def _stage_valid_points(
    stage: TimeSeriesData | None,
    height: float,
    window: TimeRange,
) -> int | None:
    """Valid WS-avg points at ``height`` in a stage series; None if absent."""
    if stage is None:
        return None
    channels = [
        s
        for s in stage.sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg" and s.height == height
    ]
    if not channels:
        return 0
    return max(count_valid_points(stage.df, s.column_name, window) for s in channels)


def _stats_sentence(items: list[SingleMastAnalysisInput]) -> str:
    """Opening stats sentence: expected 10-min points per analysis window.

    Single shared window → the standard sentence. Distinct per-mast windows
    (each mast its own representative year) → one clause per window, mast
    names prefixed, joined before the shared closing clause.
    """
    windows: dict[tuple[str, str], tuple[TimeRange, list[str]]] = {}
    for item in items:
        payload = item.cleaning_payload
        if payload is None:
            continue
        window = payload.analysis_window
        key = (window.min.isoformat(), window.max.isoformat())
        entry = windows.setdefault(key, (window, []))
        entry[1].append(item.mast_name)
    if not windows:
        return ""
    closing = "各塔主测风层数据点统计见下表。"
    if len(windows) == 1:
        window, _ = next(iter(windows.values()))
        return (
            f"以代表年时间范围（{_fmt_date(window.min)} 至 {_fmt_date(window.max)}）"
            f"为基准，10 分钟间隔应有数据点 {expected_points(window)} 个；{closing}"
        )
    clauses = []
    for window, mast_names in windows.values():
        masts = "/".join(mast_names)
        clauses.append(
            f"{masts} 以代表年时间范围（{_fmt_date(window.min)} 至 "
            f"{_fmt_date(window.max)}）为基准，10 分钟间隔应有数据点 "
            f"{expected_points(window)} 个；"
        )
    return "".join(clauses) + closing


def _fmt_date(dt: datetime) -> str:
    """Format a datetime as YYYY-MM-DD for the stats sentence."""
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


def build_cleaning_rules_atoms(
    mast_names: list[str],
    enabled: EnabledCleaningRules | None,
    stats: Sequence[MastViolationStats | None],
    mast_sensors: Sequence[Sequence[SensorColumn]] | None = None,
) -> list[ReportAtom]:
    """Build the 2.3.3 atoms: rules table + one violations table per mast.

    Args:
        mast_names: Mast names in input order (one entry per stats item).
        enabled: Deduplicated enabled rules; None when process-clean.toml
            is absent — a note atom replaces the rules table.
        stats: One parsed stats entry (or None per mast) in input order.
        mast_sensors: Stage ``SensorColumn`` metadata per mast (input
            order) for the Chinese 数据列 labels; defaults to no
            metadata (rows fall back to raw column names).

    Returns:
        Atoms in render order: rules (or note), then one violations
        atom per mast (input order).
    """
    sensors_per_mast: list[Sequence[SensorColumn]] = (
        list(mast_sensors) if mast_sensors is not None else []
    )
    atoms: list[ReportAtom] = []
    if enabled is None:
        atoms.extend(
            build_cleaning_placeholder_atoms(
                mast_names,
                "未找到 process-clean.toml，无法读取清洗规则。",
            )
        )
    else:
        atoms.append(
            CleaningRulesAtom.create(
                schema=CleaningRulesSchema,
                df=pl.DataFrame(
                    enabled.rows,
                    schema={
                        "rule_name": pl.String,
                        "sensor_type": pl.String,
                        "height_min": pl.Float64,
                        "height_max": pl.Float64,
                        "condition": pl.String,
                    },
                ),
                meta=CleaningRulesAtomMeta(rules_source=enabled.source),
            )
        )

    for mast_name, mast_stats, sensors in zip(
        mast_names, stats, sensors_per_mast, strict=False
    ):
        atoms.append(_violation_atom(mast_name, mast_stats, sensors))
    return atoms


def _violation_atom(
    mast_name: str,
    mast_stats: MastViolationStats | None,
    sensors: Sequence[SensorColumn],
) -> CleaningViolationsAtom:
    """One mast's violations atom: labeled sorted rows, or a skip note.

    Rows sort by sensor type (风速 → 风向 → 温度 → 气压 → 其他), then
    height ascending, then rule name. A missing stats file yields an
    empty table atom carrying the 剔除统计从略 note as its summary.
    """
    labels = {s.column_name: format_sensor_label(s) for s in sensors}
    note = ""
    rows: list[tuple[SensorColumn | None, str, str, int]] = []
    if mast_stats is None:
        note = (
            f"{mast_name}：未找到 process-stats/process-clean-"
            f"{mast_name}.yaml，剔除统计从略。"
        )
    else:
        by_column = {s.column_name: s for s in sensors}
        for column in mast_stats.columns:
            sensor = by_column.get(column.column)
            for rule in column.rules:
                rows.append((sensor, column.column, rule.rule_name, rule.count))
        rows.sort(
            key=lambda r: sensor_row_sort_key(r[0], r[1], r[2]),
        )
    return CleaningViolationsAtom.create(
        schema=CleaningViolationsSchema,
        df=pl.DataFrame(
            [
                {
                    "column_name": column_name,
                    "rule_name": rule_name,
                    "violation_count": count,
                }
                for _, column_name, rule_name, count in rows
            ],
            schema={
                "column_name": pl.String,
                "rule_name": pl.String,
                "violation_count": pl.Int64,
            },
        ),
        meta=CleaningViolationsAtomMeta(
            mast_name=mast_name,
            column_labels=labels,
            note=note,
        ),
    )


def _intro_atom(text: str, mast_names: list[str]) -> CleaningPlaceholderAtom:
    """One-line body paragraph atom (intro sentence) for a 2.3.x section."""
    return CleaningPlaceholderAtom.create(
        schema=CleaningPlaceholderSchema,
        df=pl.DataFrame({"text": [text]}),
        meta=CleaningAtomMeta(mast_names=list(mast_names), text=text),
    )


def _slug(*parts: str) -> str:
    """Filename-safe slug joined from mast/meso names."""
    return "_".join(re.sub(r"\W+", "", p) for p in parts if p)


def build_same_tower_atoms(results: list[SameTowerResult]) -> list[ReportAtom]:
    """Build the 2.3.5 atoms: intro line + per-mast matrix table + scatter grid.

    Empty when no mast yields regressable panels (nothing rendered rather
    than an intro referencing absent exhibits).
    """
    if not results:
        return []
    atoms: list[ReportAtom] = [
        _intro_atom(
            "同塔不同高度层风速相关性见下表及下图。",
            [r.mast_name for r in results],
        )
    ]
    for result in results:
        atoms.append(
            CorrelationMatrixAtom.create(
                schema=CorrelationLongSchema,
                df=result.matrix_long,
                meta=CorrelationMatrixAtomMeta(
                    mast_name=result.mast_name,
                    labels=result.labels,
                    caption=(f"{result.mast_name} 同塔不同高度层风速相关系数矩阵"),
                ),
            )
        )
    for result in results:
        atoms.append(
            ScatterRegressionAtom.create(
                schema=ScatterPanelSchema,
                df=result.panels,
                meta=ScatterRegressionAtomMeta(
                    caption=f"{result.mast_name} 同塔不同高度层风速散点及回归直线",
                    chart_title=f"{result.mast_name} 同塔不同高度层风速相关性",
                    slug=_slug(result.mast_name, "same_tower"),
                    x_labels=result.labels,
                    y_labels=result.labels,
                    pairs_df=result.pairs,
                ),
            )
        )
    return atoms


def build_cross_mast_atoms(
    results: list[CrossMastResult],
) -> list[ReportAtom]:
    """Build the 2.3.6 atoms: intro line + per-ordered-pair scatter grid."""
    if not results:
        return []
    atoms: list[ReportAtom] = [
        _intro_atom(
            "各测风塔间风速相关性及回归系数见下图。",
            sorted({r.mast_a for r in results} | {r.mast_b for r in results}),
        )
    ]
    for result in results:
        atoms.append(
            ScatterRegressionAtom.create(
                schema=ScatterPanelSchema,
                df=result.panels,
                meta=ScatterRegressionAtomMeta(
                    caption=(f"{result.mast_a} ← {result.mast_b} 风速散点及回归直线"),
                    chart_title=(f"{result.mast_a} ← {result.mast_b} 风速相关性"),
                    slug=_slug(result.mast_a, result.mast_b, "cross"),
                    x_labels=result.x_labels,
                    y_labels=result.y_labels,
                    pairs_df=result.pairs,
                ),
            )
        )
    return atoms


def build_meso_atoms(results: list[MesoResult]) -> list[ReportAtom]:
    """Build the 2.3.7 atoms: intro line + per-mast height-panel scatter."""
    if not results:
        return []
    atoms: list[ReportAtom] = [
        _intro_atom(
            "根据 2.2.2 节所选 ERA5 数据源，各塔主测风层与 ERA5 数据的相关性分析见下图。",
            [r.mast_name for r in results],
        )
    ]
    for result in results:
        atoms.append(
            ScatterRegressionAtom.create(
                schema=ScatterPanelSchema,
                df=result.panels,
                meta=ScatterRegressionAtomMeta(
                    caption=(f"{result.mast_name} ← {result.meso_name} 风速散点及回归直线"),
                    chart_title=(f"{result.mast_name} ← {result.meso_name} 风速相关性"),
                    slug=_slug(result.mast_name, result.meso_name, "meso"),
                    x_labels=[result.meso_name],
                    y_labels=result.y_labels,
                    pairs_df=result.pairs,
                ),
            )
        )
    return atoms


def build_tower_shading_atoms(
    items: list[SingleMastAnalysisInput],
) -> list[ReportAtom]:
    """Build the 2.3.4 atoms: method paragraph + per-height sector tables.

    Masts without a tower-shading stage (``tower_shading_series is None``),
    without dual-channel heights, or without an avg wind-direction channel
    contribute no table — the method paragraph always renders. The method
    text is chosen from the unfiltered dual-channel scan (all WS-avg
    heights, not only ``cleaning_heights``): the no-table variant asserts
    各高度层均为单通道, so it may only render when no dual channel exists
    anywhere.
    """
    atoms: list[ReportAtom] = []
    has_dual_channel = False
    for item in items:
        payload = item.cleaning_payload
        if payload is None or payload.tower_shading_series is None:
            continue
        clean = payload.clean_series
        shading = payload.tower_shading_series
        if clean is None:
            continue
        wd_column = find_avg_wind_direction_column(shading.sensors)
        if wd_column is None:
            continue
        duals = find_dual_channel_heights(
            clean.df, shading.df, clean.sensors, shading.sensors
        )
        if duals:
            has_dual_channel = True
        for dual in duals:
            if not any(abs(dual.height - h) < 0.01 for h in payload.cleaning_heights):
                continue
            stats = tower_shading_sector_stats(
                clean.df,
                shading.df,
                dual,
                wd_column,
                payload.analysis_window,
            )
            frame = tower_shading_comparison_frame(stats)
            if frame.is_empty():
                continue
            label_1, label_2 = dual.channel_labels
            atoms.append(
                TowerShadingSectorTableAtom.create(
                    schema=TowerShadingSectorSchema,
                    df=frame,
                    meta=TowerShadingSectorTableAtomMeta(
                        mast_name=item.mast_name,
                        height=dual.height,
                        channel_1_label=label_1,
                        channel_2_label=label_2,
                    ),
                )
            )
    text = (
        TOWER_SHADING_METHOD_TEXT
        if has_dual_channel
        else TOWER_SHADING_METHOD_TEXT_NO_TABLE
    )
    return [
        TowerShadingMethodAtom.create(
            schema=TowerShadingMethodSchema,
            df=pl.DataFrame({"text": [text]}),
            meta=TowerShadingMethodAtomMeta(
                mast_names=[i.mast_name for i in items],
            ),
        ),
        *atoms,
    ]
