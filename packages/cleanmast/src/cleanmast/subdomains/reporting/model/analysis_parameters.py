from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisParameters:
    heights: list[float]
    air_density: float
    include_max_min: bool = True
    include_power: bool = True
