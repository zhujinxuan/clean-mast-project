"""IO layer for shared timeseries — repository protocol + file-based realization."""

from cleanmast.shared.timeseries.io.file_repository import (
    FileTimeSeriesRepository,
    load_timeseries,
    load_timeseries_parquet,
    save_timeseries,
    save_timeseries_parquet,
)
from cleanmast.shared.timeseries.io.repository import TimeSeriesRepository
from cleanmast.shared.timeseries.io.validation import (
    create_wind_schema,
    validate_timeseries,
)

__all__ = [
    "TimeSeriesRepository",
    "FileTimeSeriesRepository",
    "load_timeseries",
    "save_timeseries",
    "load_timeseries_parquet",
    "save_timeseries_parquet",
    "validate_timeseries",
    "create_wind_schema",
]
