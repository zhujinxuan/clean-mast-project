"""WT TimeSeries configuration models - re-exported from shared/timeseries.

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
