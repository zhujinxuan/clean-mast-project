"""Canonical analysis parameters for the reporting domain."""

from __future__ import annotations

from dataclasses import dataclass, field

from cleanmast.subdomains.reporting.model.extreme_wind_gust_factor import (
    ExtremeWindGustFactor,
)


@dataclass(frozen=True)
class AnalysisParameters:
    """Configuration parameters for analysis calculations."""

    air_density: float
    include_max_min: bool = True
    include_power: bool = True
    turbulence_heights: list[float] = field(default_factory=list)
    extreme_wind_10min_heights: list[float] | None = None
    extreme_wind_3s_heights: list[float] | None = None
    extreme_wind_gust_factors: list[ExtremeWindGustFactor] | None = None
