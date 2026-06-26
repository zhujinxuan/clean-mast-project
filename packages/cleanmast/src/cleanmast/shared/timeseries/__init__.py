# TODO: migrate ownership from dataingestion to shared/timeseries
"""Temporary facade for time series foundations.

Re-exports foundational time series types from dataingestion until they can be
properly migrated to shared/timeseries.
"""

from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    load_timeseries,
    load_timeseries_parquet,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)

__all__ = [
    "TimeSeriesData",
    "SensorColumn",
    "TimeSeriesSource",
    "load_timeseries",
    "load_timeseries_parquet",
]
