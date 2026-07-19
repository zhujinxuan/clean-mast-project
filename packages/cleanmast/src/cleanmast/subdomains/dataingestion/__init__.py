"""DataIngestion subdomain - sensor data loading and validation."""

from cleanmast.shared.timeseries.io import (
    FileTimeSeriesRepository,
    TimeSeriesRepository,
    create_wind_schema,
    load_timeseries,
    load_timeseries_parquet,
    save_timeseries,
    save_timeseries_parquet,
    validate_timeseries,
)
from cleanmast.shared.timeseries.sensor_column import SensorColumn
from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_data import TimeSeriesData
from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)

__all__ = [
    "SensorColumn",
    "TimeSeriesData",
    "TimeSeriesSource",
    "TimeRange",
    "FileTimeSeriesRepository",
    "TimeSeriesRepository",
    "create_wind_schema",
    "load_timeseries",
    "load_timeseries_parquet",
    "save_timeseries",
    "save_timeseries_parquet",
    "validate_timeseries",
]
