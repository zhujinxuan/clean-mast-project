"""Coverage counting against expected interval points in a TimeRange.

Mirrors the Julia cleaning-report concepts (``ReportCleanData.SensorCoverageInfo``,
``DetectedInterval``): raw/clean coverage percentages are computed against
the number of points a complete interval grid would produce over the
analysis window.
"""

from dataclasses import dataclass
from datetime import timedelta

import polars as pl

from cleanmast.shared.timeseries.time_range import TimeRange

DEFAULT_INTERVAL_MINUTES = 10


@dataclass(frozen=True)
class CoverageStats:
    """Valid-point count vs expected interval points for one column.

    Attributes:
        expected_points: Points a complete interval grid produces over the
            window (inclusive bounds).
        valid_points: Non-null observations of the column inside the window.
    """

    expected_points: int
    valid_points: int

    @property
    def coverage_ratio(self) -> float | None:
        """valid_points / expected_points; None when the window is empty."""
        if self.expected_points == 0:
            return None
        return self.valid_points / self.expected_points


def expected_points(
    window: TimeRange,
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
) -> int:
    """Number of interval grid points covering ``[window.min, window.max]``.

    Both bounds are inclusive: a 10-min grid over exactly one hour yields
    7 points (00:00 … 01:00), matching the inclusive window convention used
    by the analysis-window clipping in ``generate_report``.
    """
    if interval_minutes <= 0:
        raise ValueError(f"interval_minutes must be positive, got {interval_minutes}")
    span = window.max - window.min
    steps = span // timedelta(minutes=interval_minutes)
    return steps + 1


def count_valid_points(
    df: pl.DataFrame,
    column: str,
    window: TimeRange,
) -> int:
    """Count non-null values of ``column`` whose timestamp is inside ``window``.

    Parquet timestamps are tz-naive, so the window bounds are stripped of
    timezone info before comparison (same convention as
    ``generate_report._clip_input_to_window``). Unknown columns count as 0.
    """
    if "timestamp" not in df.columns or column not in df.columns:
        return 0
    start = window.min.replace(tzinfo=None)
    end = window.max.replace(tzinfo=None)
    in_window = df.filter(
        (pl.col("timestamp") >= start) & (pl.col("timestamp") <= end)
    )
    return int(in_window.get_column(column).is_not_null().sum())


def coverage_stats(
    df: pl.DataFrame,
    column: str,
    window: TimeRange,
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
) -> CoverageStats:
    """Coverage of ``column`` over ``window`` against the interval grid."""
    return CoverageStats(
        expected_points=expected_points(window, interval_minutes),
        valid_points=count_valid_points(df, column, window),
    )
