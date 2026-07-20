"""Canonical analysis input types for the reporting domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cleanmast.shared.timeseries import TimeSeriesData

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
class SingleMastAnalysisInput:
    """Input specification for single mast analysis."""

    time_series: TimeSeriesData
    parameters: AnalysisParameters
    mast_name: str
    representative_year_calibration_payload: RepresentativeYearCalibrationPayload | None = None
