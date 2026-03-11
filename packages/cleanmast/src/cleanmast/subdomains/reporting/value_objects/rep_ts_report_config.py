"""Report configuration models.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓
"""

from pathlib import Path

import tomli
from pydantic import BaseModel

from cleanmast.subdomains.dataingestion.value_objects.time_series_source import TimeSeriesSource


class MastConfig(BaseModel):
    """Configuration for a single mast in the report."""
    
    name: str
    air_density: float
    input: TimeSeriesSource  # Reuse existing type!


class RepTsReportConfig(BaseModel):
    """Configuration for rep-ts report command."""
    
    masts: list[MastConfig]
    
    @classmethod
    def from_toml(cls, path: Path) -> "RepTsReportConfig":
        """Load config from TOML file."""
        with open(path, "rb") as f:
            data = tomli.load(f)
        return cls(**data)
