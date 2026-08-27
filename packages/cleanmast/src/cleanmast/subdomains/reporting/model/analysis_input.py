"""Canonical analysis input types for the reporting domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cleanmast.shared.timeseries import TimeSeriesData

from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import AnalysisParameters


@dataclass(frozen=True)
class RepresentativeYearCalibrationPayload:
    """Mesoscale data for representative year calibration."""

    meso_time_series: TimeSeriesData
    meso_name: str
    sampling_period: str  # "10min" or "1h"
    rep_year_start: datetime
    rep_year_end: datetime


@dataclass(frozen=True)
class CleaningAnalysisPayload:
    """Cleaning-pipeline stage sources for one mast (section 2.3.x).

    Attached by ``load_datasets`` for masts of the cleaning dataset. Paths
    are project-relative, exactly as authored in process-clean.toml /
    tower-shading.toml. ``analysis_window`` is the mast's rep-year window —
    the expected-points denominator for coverage statistics.
    The ``*_series`` fields are the same stages already LOADED and clipped
    to ``analysis_window`` by ``load_datasets`` (sections never load
    parquet); None when the mast has no such stage source.
    """

    raw_input: TimeSeriesSource | None
    clean_input: TimeSeriesSource | None
    tower_shading_input: TimeSeriesSource | None
    cleaning_heights: list[float]
    analysis_window: TimeRange
    raw_series: TimeSeriesData | None = None
    clean_series: TimeSeriesData | None = None
    tower_shading_series: TimeSeriesData | None = None


@dataclass(frozen=True)
class SingleMastAnalysisInput:
    """Input specification for single mast analysis."""

    time_series: TimeSeriesData
    parameters: AnalysisParameters
    mast_name: str
    representative_year_calibration_payload: RepresentativeYearCalibrationPayload | None = None
    cleaning_payload: CleaningAnalysisPayload | None = None
