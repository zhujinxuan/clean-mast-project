"""Infrastructure layer for dataingestion subdomain.

ADR-GUARDRAILS: structure-001-subdomain-layout, persistence-001-parquet-storage
Compliance: Infrastructure layer ✓
Description: I/O operations, external integrations, and technical concerns

This module contains:
- Parquet I/O operations
- CSV parsing
- External data source integrations
"""

from .timeseries_io import load_timeseries, save_timeseries
from .timeseries_validation import create_wind_schema, validate_timeseries

__all__ = [
    "load_timeseries",
    "save_timeseries",
    "create_wind_schema",
    "validate_timeseries",
]
