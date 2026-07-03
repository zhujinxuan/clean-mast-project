"""Configuration module for wt_timeseries.

ADR-GUARDRAILS: structure-001-subdomain-layout, config-001-config-structs
Compliance: Subdomain layout ✓ | Value Object ✓ | Validation ✓
Description: Pydantic models for the wt-timeseries TOML configuration
"""

from pathlib import Path
from typing import Union

import tomli
from pydantic import BaseModel, field_validator

from cleanmast.infrastructure.path_utils import to_posix_path
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class WtTimeSeriesMast(BaseModel):
    """Configuration for a single mast in wt-timeseries generation."""

    name: str
    input: TimeSeriesSource
    csv_heights: list[float]
    turbulence_heights: list[float]

    @field_validator("csv_heights")
    @classmethod
    def validate_csv_heights(cls, v: list[float]) -> list[float]:
        """Validate all csv_heights are >= 100.0."""
        for height in v:
            if height < 100.0:
                raise ValueError(f"csv_heights must be >= 100.0, got {height}")
        return v


class WtTimeSeriesConfiguration(BaseModel):
    """Top-level configuration for wt-timeseries generation."""

    masts: list[WtTimeSeriesMast]

    @field_validator("masts")
    @classmethod
    def validate_unique_mast_names(cls, v: list[WtTimeSeriesMast]) -> list[WtTimeSeriesMast]:
        """Validate all mast names are unique."""
        names = [mast.name for mast in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate mast names found in configuration")
        return v


def load_wt_timeseries_config(config_path: Union[str, Path]) -> WtTimeSeriesConfiguration:
    """Load wt-timeseries configuration from TOML file.

    Note: Kept for backward compatibility during transition. The canonical
    discovery path is ``ProjectConfig.discover_wt_timeseries_config()``.
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
                mast_data["input"]["data"] = to_posix_path(config_dir / input_path)

    return WtTimeSeriesConfiguration(**data)
