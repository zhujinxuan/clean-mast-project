"""Analysis input model for reporting.

Compliance: reporting model | Value Object
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cleanmast.shared.timeseries import TimeSeriesData

from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)


@dataclass(frozen=True)
class SingleMastAnalysisInput:
    """Input specification for single mast analysis."""

    time_series: TimeSeriesData
    parameters: AnalysisParameters
    mast_name: str


__all__ = ["SingleMastAnalysisInput"]
