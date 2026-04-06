"""Report configuration models.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓
"""

from pathlib import Path

import tomli
from pydantic import BaseModel, Field

from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class MastConfig(BaseModel):
    """Configuration for a single mast in the report."""
    
    name: str
    air_density: float
    input: TimeSeriesSource  # Reuse existing type!


class ReportSubsectionsConfig(BaseModel):
    """Configuration for report subsections.
    
    Controls which analysis sections are included in the report.
    All subsections default to True for backward compatibility.
    """
    
    monthly_wind: bool = True
    monthly_power: bool = True
    wind_rose: bool = True
    vertical_profile: bool = True
    wind_frequency: bool = True
    weibull: bool = True
    turbulence: bool = True
    temporal: bool = True


class RepTsReportConfig(BaseModel):
    """Configuration for rep-ts report command."""
    
    masts: list[MastConfig]
    subsections: ReportSubsectionsConfig = Field(default_factory=ReportSubsectionsConfig)
    
    @classmethod
    def from_toml(cls, path: Path) -> "RepTsReportConfig":
        """Load config from TOML file."""
        with open(path, "rb") as f:
            data = tomli.load(f)
        return cls(**data)
