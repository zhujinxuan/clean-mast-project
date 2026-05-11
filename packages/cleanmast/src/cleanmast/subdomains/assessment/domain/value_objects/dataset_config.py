"""Flat dataset configuration models for the report config TOML redesign.

ADR-GUARDRAILS: ddd-t-002-entities-value-objects, types-001-strict-type-safety
Compliance: Value Object ✓ | Strict Types ✓ | Validation ✓
Description: Dataset-level config with mast references, decoupled from TimeSeriesSource.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class MastRef(BaseModel):
    """Reference to a mast within a dataset.

    Attributes:
        name: Mast identifier (e.g., "M6002").
        air_density: Air density value in kg/m³; must be strictly positive.
        input: Time series data source for this mast.
    """

    name: str
    air_density: float = Field(gt=0)
    input: TimeSeriesSource


class MesoRef(BaseModel):
    """Reference to a mesoscale data source for specific masts.

    Attributes:
        input: Time series data source for the mesoscale data (e.g., ERA5).
        target_masts: List of mast names this meso source applies to.
    """

    input: TimeSeriesSource
    target_masts: list[str]

    @model_validator(mode="after")
    def validate_target_masts(self) -> "MesoRef":
        """Validate target_masts list is non-empty."""
        if not self.target_masts:
            raise ValueError("target_masts must contain at least one mast name")
        return self


class DatasetConfig(BaseModel):
    """Configuration for a single dataset in the report.

    Attributes:
        name: Dataset identifier.
        masts: List of mast references within this dataset.
        mesos: Optional list of mesoscale data references.
        note: Optional note or description.
    """

    name: str
    masts: list[MastRef]
    mesos: list[MesoRef] | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_masts(self) -> "DatasetConfig":
        """Validate masts list: non-empty and no duplicate names."""
        if not self.masts:
            raise ValueError("masts must contain at least one MastRef")

        names = [mast.name for mast in self.masts]
        seen = set()
        for name in names:
            if name in seen:
                raise ValueError(f"Duplicate mast name '{name}' in dataset '{self.name}'")
            seen.add(name)

        return self
