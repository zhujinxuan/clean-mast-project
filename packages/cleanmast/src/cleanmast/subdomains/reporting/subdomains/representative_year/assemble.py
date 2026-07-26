"""Assembly functions for representative year calibration atoms.

Pure functions only — NO IO, no side effects.
Takes computed results and wraps them in atom instances.
"""

from __future__ import annotations

from typing import TypedDict

import polars as pl

from cleanmast.shared.timeseries import SensorColumn
from cleanmast.subdomains.reporting.subdomains.representative_year.compute import (
    RepYearMastResult,
    RepYearMastSummary,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.report_meta import (
    RepresentativeYearAtomMeta,
    RepYearSectorAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_sector_figure_atom import (
    RepYearSectorFigureAtom,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_sector_table_atom import (
    RepYearSectorTableAtom,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_summary_atom import (
    RepYearSummaryAtom,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.schemas import (
    RepYearSectorSchema,
    RepYearSummarySchema,
)


class _RepYearSummaryRow(TypedDict):
    """Row type mirroring RepYearSummarySchema for DataFrame construction."""

    year_range: str
    mast_name: str
    meso_name: str
    climatology_mean_ws: float
    rep_year_mean_ws: float
    anomaly_percent: float
    needs_correction: bool


class _RepYearSectorRow(TypedDict):
    """Row type mirroring RepYearSectorSchema for DataFrame construction."""

    sector: str
    sector_index: int
    climatology_mean: float | None
    rep_year_mean: float | None
    meso_difference: float | None
    slope: float | None
    intercept: float | None
    adjustment: float | None
    data_points: int | None


def build_rep_year_summary_atom(
    summaries: list[RepYearMastSummary],
) -> RepYearSummaryAtom:
    """Build the all-mast summary table atom."""
    rows: list[_RepYearSummaryRow] = []
    for s in summaries:
        rows.append({
            "year_range": s.year_range,
            "mast_name": s.mast_name,
            "meso_name": s.meso_name,
            "climatology_mean_ws": s.climatology_mean_ws,
            "rep_year_mean_ws": s.rep_year_mean_ws,
            "anomaly_percent": s.anomaly_percent,
            "needs_correction": s.needs_correction,
        })
    df = pl.DataFrame(rows)
    mast_names = [s.mast_name for s in summaries]
    return RepYearSummaryAtom.create(
        RepYearSummarySchema, df,
        RepresentativeYearAtomMeta(mast_names=mast_names),
    )


def _find_sensor(
    sensors: list[SensorColumn],
    sensor_type: str,
    stat_type: str = "avg",
) -> str:
    """Resolve column_name from SensorColumn metadata by sensor_type and stat_type."""
    candidates = [
        s for s in sensors
        if s.sensor_type == sensor_type and s.stat_type == stat_type
    ]
    if not candidates:
        raise ValueError(f"No sensor with type={sensor_type!r}, stat={stat_type!r}")
    return candidates[0].column_name


def build_rep_year_sector_atoms(
    results: list[RepYearMastResult],
    mast_data: dict[str, pl.DataFrame],  # mast_name → raw timeseries DataFrame
    meso_data: dict[str, pl.DataFrame],  # mast_name → raw meso timeseries DataFrame
    mast_sensors: dict[str, list[SensorColumn]],  # mast_name → list of SensorColumn
    meso_sensors: dict[str, list[SensorColumn]],  # mast_name → list of SensorColumn
) -> tuple[list[RepYearSectorTableAtom], list[RepYearSectorFigureAtom]]:
    """Build per-mast sector table and figure atoms.

    Args:
        results: Per-mast calibration results from compute.
        mast_data: Raw timeseries DataFrames per mast (for scatter plotting).
        meso_data: Raw meso timeseries DataFrames per mast (for scatter plotting).
        mast_sensors: Sensor metadata per mast (for column name resolution).
        meso_sensors: Sensor metadata per meso (for column name resolution).

    Returns:
        (table_atoms, figure_atoms) — one table + one figure per result (per height).
    """
    table_atoms: list[RepYearSectorTableAtom] = []
    figure_atoms: list[RepYearSectorFigureAtom] = []

    for result in results:
        summary = result.summary

        # Build sector DataFrame
        rows: list[_RepYearSectorRow] = []
        for sector in result.sectors:
            rows.append({
                "sector": sector.sector,
                "sector_index": sector.sector_index,
                "climatology_mean": sector.climatology_mean,
                "rep_year_mean": sector.rep_year_mean,
                "meso_difference": sector.meso_difference,
                "slope": sector.slope,
                "intercept": sector.intercept,
                "adjustment": sector.adjustment,
                "data_points": sector.data_points,
            })
        df = pl.DataFrame(rows)

        # Resolve column names from sensor metadata
        mast_sensors_list = mast_sensors.get(summary.mast_name, [])
        meso_sensors_list = meso_sensors.get(summary.mast_name, [])
        mast_ws_col = _find_sensor(mast_sensors_list, "WindSpeed", "avg")
        meso_ws_col = _find_sensor(meso_sensors_list, "WindSpeed", "avg")
        wd_col = _find_sensor(meso_sensors_list, "WindDirection", "avg")

        meta = RepYearSectorAtomMeta(
            mast_name=summary.mast_name,
            meso_name=summary.meso_name,
            height=result.height,
            mast_ws_col=mast_ws_col,
            meso_ws_col=meso_ws_col,
            wd_col=wd_col,
            mast_df=mast_data.get(summary.mast_name, pl.DataFrame()),
            meso_df=meso_data.get(summary.mast_name, pl.DataFrame()),
            sector_slopes=[s.slope for s in result.sectors],
            sector_intercepts=[s.intercept for s in result.sectors],
        )

        # Table atom
        table_atoms.append(RepYearSectorTableAtom.create(
            RepYearSectorSchema, df, meta,
        ))

        # Figure atom (requires non-empty DataFrames)
        if not meta.mast_df.is_empty() and not meta.meso_df.is_empty():
            figure_atoms.append(RepYearSectorFigureAtom.create(
                RepYearSectorSchema, df, meta,
            ))

    return table_atoms, figure_atoms
