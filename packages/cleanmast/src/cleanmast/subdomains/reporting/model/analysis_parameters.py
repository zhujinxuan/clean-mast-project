"""Canonical analysis parameters for the reporting domain."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnalysisParameters:
    """Configuration parameters for analysis calculations."""

    air_density: float
    include_max_min: bool = True
    include_power: bool = True
    turbulence_heights: list[float] = field(default_factory=list)
