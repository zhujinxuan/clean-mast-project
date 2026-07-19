"""WT TimeSeries configuration models - re-exported from shared/timeseries.

ADR-GUARDRAILS: structure-001-subdomain-layout
This module re-exports from the canonical shared location for backward compatibility.
"""

from cleanmast.shared.timeseries.wt_timeseries_config import (
    WtTimeSeriesConfiguration,
    WtTimeSeriesMast,
)

__all__ = [
    "WtTimeSeriesMast",
    "WtTimeSeriesConfiguration",
]
