"""Time series repository protocol (ABC).

ADR-GUARDRAILS: structure-001-subdomain-layout, persistence-001-parquet-storage
Compliance: Subdomain layout ✓ | Repository Pattern ✓ | Protocol-based ✓
Description: Repository protocol defining interface for time series data access
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from cleanmast.shared.timeseries.time_series_data import TimeSeriesData


class TimeSeriesRepository(Protocol):
    """Protocol defining interface for time series data repositories.

    Implementations:
        - ParquetRepository: Parquet-based storage with embedded metadata
        - Future: DatabaseRepository, CloudRepository, etc.

    Design Pattern:
        Repository pattern abstracts data access, allowing:
        - Easy swapping of storage backends
        - Testable code (mock repositories)
        - Consistent interface regardless of storage
    """

    @abstractmethod
    def load(self, data_path: str | Path, sensors_path: str | Path | None = None) -> TimeSeriesData:
        """Load time series data from repository.

        Args:
            data_path: Path to data file (format depends on implementation)
            sensors_path: Optional path to sensor metadata (for formats without embedded metadata)

        Returns:
            TimeSeriesData with DataFrame and sensor metadata

        Raises:
            FileNotFoundError: If data file doesn't exist
            ValueError: If data format is invalid or metadata missing
        """
        ...

    @abstractmethod
    def save(self, data_path: str | Path, data: TimeSeriesData, sensors_path: str | Path | None = None) -> None:
        """Save time series data to repository.

        Args:
            data_path: Path where data should be saved
            data: TimeSeriesData to save
            sensors_path: Optional path for sensor metadata file

        Raises:
            ValueError: If data is invalid
            IOError: If write fails
        """
        ...
