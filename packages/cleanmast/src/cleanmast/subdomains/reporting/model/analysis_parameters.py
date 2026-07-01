"""Canonical analysis parameters for the reporting domain."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisParameters:
    """Configuration parameters for analysis calculations."""

    heights: list[float]
    air_density: float
    include_max_min: bool = True
    include_power: bool = True
