"""Metadata for representative year calibration report atoms."""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl


@dataclass(frozen=True)
class RepresentativeYearAtomMeta:
    """Metadata for multi-mast summary table atom."""

    mast_name: str = "_all_masts"
    mast_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepYearSectorAtomMeta:
    """Metadata for per-mast sector table and figure atoms.

    Carries raw timeseries for scatter plotting — NOT validated by schema.
    """

    mast_name: str
    meso_name: str
    height: float
    mast_ws_col: str  # resolved from SensorColumn metadata
    meso_ws_col: str  # resolved from SensorColumn metadata
    wd_col: str  # resolved from SensorColumn metadata
    mast_df: pl.DataFrame
    meso_df: pl.DataFrame
    sector_slopes: list[float]  # 16 entries, index 0 = sector 1
    sector_intercepts: list[float]  # 16 entries
