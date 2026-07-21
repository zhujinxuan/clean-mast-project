"""Lightweight mast metadata entries for fill-heights planning.

Description: Minimal dataclass carrying mast name and output source
             for fill-heights planning — avoids importing heavy config types.
"""

from dataclasses import dataclass

from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource


@dataclass(frozen=True)
class MastPlanningEntry:
    """Minimal mast metadata for fill-heights planning (name + output source)."""

    name: str
    output: TimeSeriesSource
