"""Time series repository protocol.

Description: Repository protocol defining interface for time series data access
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cleanmast.shared.timeseries.time_series_data import TimeSeriesData
    from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource


@runtime_checkable
class TimeSeriesRepository(Protocol):
    """Protocol defining interface for time series data repositories.

    Realization: FileTimeSeriesRepository (file-based store dispatching on
    TimeSeriesSource.data extension: .parquet → embedded metadata; .csv →
    sidecar metadata).

    Design Pattern:
        Repository pattern abstracts data access, allowing:
        - Easy swapping of storage backends
        - Testable code (mock repositories)
        - Consistent interface regardless of storage
    """

    def load(self, source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
        """Load time series data from repository.

        Args:
            source: TimeSeriesSource with paths to data and sensors files
            base_dir: Base directory for resolving relative paths

        Returns:
            TimeSeriesData with DataFrame and sensor metadata

        Raises:
            FileNotFoundError: If data or sensors file doesn't exist
            ValueError: If data format is invalid or metadata missing
        """
        ...

    def save(self, source: TimeSeriesSource, base_dir: str, data: TimeSeriesData) -> None:
        """Save time series data to repository.

        Args:
            source: TimeSeriesSource with paths to data and sensors files
            base_dir: Base directory for resolving relative paths
            data: TimeSeriesData to save

        Raises:
            ValueError: If data is invalid
            IOError: If write fails
        """
        ...
