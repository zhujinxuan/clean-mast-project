"""Tower shading configuration models (tower-shading.toml).

Mirrors the schema emitted by the Julia ``RecommendTowerShadingCommand``
(``CleanMastProject/src/TowerShading/RecommendTowerShadingCommand.jl``):
one ``[[masts]]`` entry per mast with ``input`` (the cleaned parquet) and
``output`` (``./tower-shading/{mast}.parquet``). Python is a READ-ONLY
consumer — the Julia pipeline authors this file.
"""

from pydantic import BaseModel, ConfigDict

from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)


class TowerShadingMast(BaseModel):
    """Per-mast entry in tower-shading.toml.

    Attributes:
        name: Mast identifier.
        input: Cleaned time series source (process-clean output).
        output: Tower-shading-corrected time series destination.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    input: TimeSeriesSource
    output: TimeSeriesSource


class TowerShadingConfiguration(BaseModel):
    """Full configuration read from tower-shading.toml.

    Attributes:
        masts: List of mast configurations to correct for tower shading.
    """

    model_config = ConfigDict(frozen=True)

    masts: list[TowerShadingMast]
