"""Configuration module for wt_timeseries.

This module provides Pydantic models for the wt-timeseries TOML configuration
file. It defines the configuration structure for generating time series CSV
files for Meteodyn WT software.

Example TOML structure:
    [[masts]]
    name = "TGL1"
    input.data = "./representative-year/filled/TGL1.parquet"
    csv_heights = [100.0, 120.0, 140.0]
    turbulence_heights = [80.0, 100.0, 120.0]
"""

from pathlib import Path
from typing import Union

import tomli
from pydantic import BaseModel, field_validator

from cleanmast.models.timeseries import TimeSeriesSource


class WtTimeSeriesMast(BaseModel):
    """Configuration for a single mast in wt-timeseries generation.

    Attributes:
        name: Unique mast identifier
        input: TimeSeriesSource pointing to the input parquet file
        csv_heights: List of heights (meters) for CSV generation.
            All values must be >= 100.0
        turbulence_heights: List of heights (meters) for turbulence files
    """

    name: str
    input: TimeSeriesSource
    csv_heights: list[float]
    turbulence_heights: list[float]

    @field_validator("csv_heights")
    @classmethod
    def validate_csv_heights(cls, v: list[float]) -> list[float]:
        """Validate all csv_heights are >= 100.0.

        Args:
            v: List of heights to validate

        Returns:
            Validated list of heights

        Raises:
            ValueError: If any height is less than 100.0
        """
        for height in v:
            if height < 100.0:
                raise ValueError(f"csv_heights must be >= 100.0, got {height}")
        return v


class WtTimeSeriesConfiguration(BaseModel):
    """Top-level configuration for wt-timeseries generation.

    Attributes:
        masts: List of mast configurations
    """

    masts: list[WtTimeSeriesMast]

    @field_validator("masts")
    @classmethod
    def validate_unique_mast_names(cls, v: list[WtTimeSeriesMast]) -> list[WtTimeSeriesMast]:
        """Validate all mast names are unique.

        Args:
            v: List of mast configurations

        Returns:
            Validated list of mast configurations

        Raises:
            ValueError: If duplicate mast names are found
        """
        names = [mast.name for mast in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate mast names found in configuration")
        return v


def load_wt_timeseries_config(config_path: Union[str, Path]) -> WtTimeSeriesConfiguration:
    """Load wt-timeseries configuration from TOML file.

    This function reads a TOML configuration file and resolves all relative
    input paths to absolute paths (relative to the TOML file directory).

    Args:
        config_path: Absolute or relative path to wt-timeseries configuration TOML file

    Returns:
        WtTimeSeriesConfiguration with resolved absolute paths

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If TOML parsing fails or configuration validation fails
        pydantic.ValidationError: If configuration structure is invalid

    Example:
        config = load_wt_timeseries_config("config/wt-timeseries.toml")
        for mast in config.masts:
            print(f"Mast: {mast.name}, Input: {mast.input.data}")
    """
    config_path = Path(config_path)
    config_dir = config_path.parent.resolve()

    with open(config_path, "rb") as f:
        data = tomli.load(f)

    # Resolve input paths to absolute
    for mast_data in data.get("masts", []):
        if "input" in mast_data and "data" in mast_data["input"]:
            input_path = Path(mast_data["input"]["data"])
            if not input_path.is_absolute():
                mast_data["input"]["data"] = str(config_dir / input_path)

    return WtTimeSeriesConfiguration(**data)
