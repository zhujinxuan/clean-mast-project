"""Time series data entity for CleanMast.

ADR-GUARDRAILS: structure-001-subdomain-layout, data-001-symbol-columns
Compliance: Subdomain layout ✓ | Domain Entity ✓ | Sensor-based access ✓
Description: Entity representing time series data with sensor metadata
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


@dataclass
class TimeSeriesData:
    """Container for time series data with sensor metadata.

    Combines a Polars DataFrame with sensor column metadata.
    Not a Pydantic model since DataFrame doesn't serialize well.

    Attributes:
        df: Polars DataFrame with timestamp column and sensor data columns
        sensors: List of SensorColumn metadata describing each data column
    """

    df: pl.DataFrame
    sensors: list[SensorColumn]
