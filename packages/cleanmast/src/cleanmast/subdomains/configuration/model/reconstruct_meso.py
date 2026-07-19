"""ReconstructMeso configuration models.

These models match the Julia ReconstructMesoConfig types and allow
reading reconstruct-meso.toml configuration files.
"""

from pydantic import BaseModel

from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)


class ReconstructMesoModelSpec(BaseModel):
    """Specification for a reconstruction model.

    Attributes:
        method: Reconstruction method (e.g., "1-sector", "constant-offset")
        meso_name: Name of the meso source to use
        model_file: Path to the trained model file (.jld2)
    """

    method: str
    meso_name: str
    model_file: str


class ReconstructMesoModels(BaseModel):
    """Wind speed and direction reconstruction models.

    Attributes:
        windspeed: Model spec for wind speed reconstruction
        winddirection: Model spec for wind direction reconstruction
    """

    windspeed: ReconstructMesoModelSpec
    winddirection: ReconstructMesoModelSpec


class MesoSource(BaseModel):
    """Mesoscale data source (TrainMesoSource in Julia).

    Attributes:
        name: Identifier for the meso source
        input: Path to meso data files
    """

    name: str
    input: TimeSeriesSource


class ReconstructMesoMast(BaseModel):
    """Mast configuration for mesoscale reconstruction.

    Attributes:
        name: Mast identifier
        input: Input time series source (from prior processing stage)
        output: Output time series destination
        time_range: Valid time range for reconstruction
        models: Wind speed and direction model specifications
    """

    name: str
    input: TimeSeriesSource
    output: TimeSeriesSource
    time_range: TimeRange
    models: ReconstructMesoModels


class ReconstructMesoConfiguration(BaseModel):
    """Full configuration for mesoscale reconstruction.

    This is the top-level configuration read from reconstruct-meso.toml.

    Attributes:
        masts: List of mast configurations to process
        mesos: List of mesoscale data sources available
    """

    masts: list[ReconstructMesoMast]
    mesos: list[MesoSource]
