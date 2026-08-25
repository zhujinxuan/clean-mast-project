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
    extreme_wind_10min_heights: list[float]
    extreme_wind_3s_heights: list[float]
    extreme_wind_gust_factors: list[ExtremeWindGustFactor]
    include_max_min: bool = True
    include_power: bool = True
    turbulence_heights: list[float] = field(default_factory=list)
    wind_frequency_heights: list[float] = field(default_factory=list)
    weibull_heights: list[float] = field(default_factory=list)
    representative_year_heights: list[float] = field(default_factory=list)
    wind_rose_heights: list[float] = field(default_factory=list)
    temporal_heights: list[float] = field(default_factory=list)
