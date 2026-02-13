"""Extrapolation configuration models.

Pydantic models for the vertical-extrapolate.toml configuration file.
"""

import tomli
from pydantic import BaseModel

from ..models.timeseries import TimeSeriesSource


class WindSpeedReference(BaseModel):
    """Reference height configuration for wind speed extrapolation.

    Attributes:
        height: Reference height in meters (base for extrapolation)
        shear: Power law shear exponent (α in V2 = V1 * (H2/H1)^α)
        weight: Weight for averaging multiple references (default 1.0)
    """

    height: float
    shear: float
    weight: float = 1.0


class WindSpeedHeightConfig(BaseModel):
    """Configuration for extrapolating wind speed to a target height.

    Attributes:
        height: Target extrapolation height in meters
        references: List of reference configurations for this height
    """

    height: float
    references: list[WindSpeedReference]


class WindSpeedConfig(BaseModel):
    """Wind speed extrapolation configuration.

    Attributes:
        heights: List of target height configurations
    """

    heights: list[WindSpeedHeightConfig]


class WindDirectionReference(BaseModel):
    """Reference height configuration for wind direction extrapolation.

    Attributes:
        height: Reference height in meters
        deg_diff_per_m: Direction change per meter (degrees)
        weight: Weight for averaging multiple references (default 1.0)
    """

    height: float
    deg_diff_per_m: float
    weight: float = 1.0


class WindDirectionHeightConfig(BaseModel):
    """Configuration for extrapolating wind direction to a target height.

    Attributes:
        height: Target extrapolation height in meters
        references: List of reference configurations for this height
    """

    height: float
    references: list[WindDirectionReference]


class WindDirectionConfig(BaseModel):
    """Wind direction extrapolation configuration.

    Attributes:
        heights: List of target height configurations
    """

    heights: list[WindDirectionHeightConfig]


class MastExtrapolateConfig(BaseModel):
    """Mast configuration for extrapolation.

    Attributes:
        name: Mast identifier
        input: Input time series source (from reconstruct-meso output)
        output: Output time series destination
        windspeed: Wind speed extrapolation configuration for this mast
        winddirection: Wind direction extrapolation configuration for this mast
    """

    name: str
    input: TimeSeriesSource
    output: TimeSeriesSource
    windspeed: WindSpeedConfig
    winddirection: WindDirectionConfig


class ExtrapolateConfiguration(BaseModel):
    """Full configuration for wind extrapolation.

    This is the top-level configuration read from vertical-extrapolate.toml.

    Attributes:
        strategy: Strategy used to generate this config (e.g., "top3-constant-shear")
        masts: List of mast configurations to process
    """

    strategy: str = "top3-constant-shear"
    masts: list[MastExtrapolateConfig]


def load_extrapolate_config(config_path: str) -> ExtrapolateConfiguration:
    """Load extrapolation configuration from TOML file.

    Args:
        config_path: Path to vertical-extrapolate.toml file

    Returns:
        ExtrapolateConfiguration parsed from the file
    """
    with open(config_path, "rb") as f:
        data = tomli.load(f)

    return ExtrapolateConfiguration(**data)
