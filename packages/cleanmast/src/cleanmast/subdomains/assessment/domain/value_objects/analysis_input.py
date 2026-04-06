"""Analysis input value objects for CleanMast.

Value objects that encapsulate the input specifications for various
analysis operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData

from .analysis_parameters import AnalysisParameters


@dataclass(frozen=True)
class SingleMastAnalysisInput:
    """Input specification for single mast analysis."""

    time_series: TimeSeriesData  # Raw time series data with sensor metadata
    parameters: AnalysisParameters  # Analysis configuration
    mast_name: str  # Mast identifier
