"""Time series source value object for CleanMast.

Description: Reference to time series data files
"""

from typing import Optional

from pydantic import BaseModel, field_validator


class TimeSeriesSource(BaseModel):
    """Reference to time series data files.

    Used in configuration files to specify paths to data and sensor metadata.

    Attributes:
        data: Path to CSV file containing time series data
        sensors: Path to sensor metadata file (YAML/TOML/JSON). Optional for Parquet files.
    """

    data: str
    sensors: Optional[str] = None

    @field_validator("sensors")
    @classmethod
    def sensors_required_for_csv(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure sensors is provided when data is a CSV file."""
        if v is None and info.data.get("data", "").endswith(".csv"):
            raise ValueError("sensors field is required when data is a CSV file")
        return v
