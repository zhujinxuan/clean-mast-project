"""Analysis parameters value object for analysis configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisParameters:
    """Configuration parameters for analysis calculations."""

    heights: list[float]  # Heights to analyze
    air_density: float  # Air density override
    include_max_min: bool = True  # Include max/min in monthly stats
    include_power: bool = True  # Include power density calculations
