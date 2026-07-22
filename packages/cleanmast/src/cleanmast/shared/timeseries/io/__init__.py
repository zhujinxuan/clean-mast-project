"""IO layer for shared timeseries — repository protocol + validation helpers.

The file-based realization lives in ``cleanmast.infrastructure.file_repository``
(moved out of shared so the domain layer owns zero I/O).
"""

from cleanmast.shared.timeseries.io.repository import TimeSeriesRepository
from cleanmast.shared.timeseries.io.validation import (
    create_wind_schema,
    validate_timeseries,
)

__all__ = [
    "TimeSeriesRepository",
    "validate_timeseries",
    "create_wind_schema",
]
