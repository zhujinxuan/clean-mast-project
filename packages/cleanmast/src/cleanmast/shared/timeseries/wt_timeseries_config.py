"""Configuration module for wt_timeseries.

ADR-GUARDRAILS: structure-001-subdomain-layout, config-001-config-structs
Compliance: Subdomain layout ✓ | Value Object ✓ | Validation ✓
Description: Pydantic models for the wt-timeseries TOML configuration
"""

from pydantic import BaseModel, field_validator

from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource


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
