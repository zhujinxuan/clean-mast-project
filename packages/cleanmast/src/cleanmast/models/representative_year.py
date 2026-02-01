"""RepresentativeYear configuration models.

These models match the Julia RepresentativeYearConfig types and allow
reading representative-year.toml configuration files.
"""

import tomli
from pydantic import BaseModel

from .reconstruct_meso import MesoSource
from .timeseries import TimeRange, TimeSeriesSource


class RepresentativeYearMesoModel(BaseModel):
    """Specification for a representative year model.

    Attributes:
        method: Reconstruction method (e.g., "16-sector")
        meso_name: Name of the meso source to use
        model_file: Path to the trained model file (.jld2)
    """

    method: str
    meso_name: str
    model_file: str


class RepresentativeYearMast(BaseModel):
    """Mast configuration for representative year calibration.

    Attributes:
        name: Mast identifier
        input: Input time series source (from reconstruct-meso output)
        output: Output time series destination
        time_range: Valid time range for calibration
        meso_model: Model specification for this mast
    """

    name: str
    input: TimeSeriesSource
    output: TimeSeriesSource
    time_range: TimeRange
    meso_model: RepresentativeYearMesoModel


class RepresentativeYearConfiguration(BaseModel):
    """Full configuration for representative year calibration.

    This is the top-level configuration read from representative-year.toml.

    Attributes:
        masts: List of mast configurations to process
        mesos: List of mesoscale data sources available
    """

    masts: list[RepresentativeYearMast]
    mesos: list[MesoSource]


def load_representative_year_config(config_path: str) -> RepresentativeYearConfiguration:
    """Load representative year configuration from TOML file.

    Args:
        config_path: Path to representative-year.toml file

    Returns:
        RepresentativeYearConfiguration parsed from the file
    """
    with open(config_path, "rb") as f:
        data = tomli.load(f)

    return RepresentativeYearConfiguration(**data)
