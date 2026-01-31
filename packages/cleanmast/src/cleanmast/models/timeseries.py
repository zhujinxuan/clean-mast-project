"""Time series models for CleanMast."""

from dataclasses import dataclass
from datetime import datetime

import polars as pl
from pydantic import BaseModel

from .sensor import SensorColumn


class TimeSeriesSource(BaseModel):
    """Reference to time series data files.

    Used in configuration files to specify paths to data and sensor metadata.

    Attributes:
        data: Path to CSV file containing time series data
        sensors: Path to sensor metadata file (YAML/TOML/JSON)
    """

    data: str
    sensors: str


class TimeRange(BaseModel):
    """Time range specification.

    Attributes:
        min: Start of time range (inclusive)
        max: End of time range (inclusive)
    """

    min: datetime
    max: datetime


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
