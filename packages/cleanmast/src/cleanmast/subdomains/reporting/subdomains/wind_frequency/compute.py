"""Wind frequency computation for the reporting domain.

LOGIC-PRESERVATION: Ported from assessment/subdomains/wind_frequency/services/_calculator.py.
All formulas, constants, and algorithms preserved exactly.
Pure functions only — no IO, no side effects, no stateful classes.

Key improvement: eliminates the `rows: list[dict]` pattern by building Polars
DataFrames per sensor and concatenating, instead of accumulating untyped dicts.
"""

from collections.abc import Sequence

import numpy as np
import polars as pl

from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.constants import (
    PRODUCTIVE_RANGE,
)

# Wind frequency constants
BIN_SIZE: float = 1.0
MAX_BIN: float = 28.0
HOURS_PER_YEAR: float = 8760.0
MIN_SAMPLES: int = 10
AIR_DENSITY: float = 1.225


def calculate_air_density_at_height(
    height: float, ground_density: float = AIR_DENSITY
) -> float:
    """Calculate air density at a specific height using the barometric formula.

    Formula:
        T = 288.15 - 0.0065 * height
        ratio = (T / 288.15) ** (9.81 / (287.05 * 0.0065))
        rho = ground_density * ratio

    Args:
        height: Height in meters above ground level
        ground_density: Air density at ground level in kg/m³

    Returns:
        Air density at the specified height in kg/m³
    """
    T = 288.15 - 0.0065 * height
    ratio = (T / 288.15) ** (9.81 / (287.05 * 0.0065))
    return float(ground_density * ratio)


def calculate_histogram(wind_speeds: Sequence[float]) -> dict[int, int]:
    """Create wind speed histogram with 1 m/s bins.

    Bins are: [0,1), [1,2), ..., [27,28), [28,∞)

    Args:
        wind_speeds: Wind speed measurements in m/s

    Returns:
        Dictionary mapping bin index to count. Only bins with count > 0 are included.
    """
    if not wind_speeds:
        return {}

    ws_array = np.array(wind_speeds, dtype=np.float64)
    bin_indices = np.floor(ws_array).astype(np.int64)
    bin_indices = np.clip(bin_indices, 0, int(MAX_BIN))

    histogram: dict[int, int] = {}
    for bin_idx in range(int(MAX_BIN) + 1):
        count = int(np.sum(bin_indices == bin_idx))
        if count > 0:
            histogram[bin_idx] = count

    return histogram


def calculate_power_frequency(
    wind_speeds: Sequence[float], air_density: float = AIR_DENSITY
) -> dict[int, float]:
    """Calculate power frequency distribution by wind speed bin.

    Power frequency is the proportion of total energy in each bin.
    Formula: power_frequency_bin = sum(power_in_bin) / total_power

    Args:
        wind_speeds: Wind speed measurements in m/s
        air_density: Air density in kg/m³

    Returns:
        Dictionary mapping bin index to power frequency for bins 0..MAX_BIN.
    """
    if not wind_speeds:
        return {}

    ws_array = np.array(wind_speeds, dtype=np.float64)
    power = 0.5 * air_density * ws_array**3
    total_power = np.sum(power)
    if total_power == 0:
        return {}

    bin_indices = np.floor(ws_array).astype(np.int64)
    bin_indices = np.clip(bin_indices, 0, int(MAX_BIN))

    power_freq: dict[int, float] = {}
    for bin_idx in range(int(MAX_BIN) + 1):
        mask = bin_indices == bin_idx
        bin_power_sum = np.sum(power[mask])
        power_freq[bin_idx] = float(bin_power_sum / total_power)

    return power_freq


def calculate_range_summary(
    wind_speeds: Sequence[float],
    min_speed: float | None = None,
    max_speed: float | None = None,
    air_density: float = AIR_DENSITY,
) -> dict[str, float]:
    """Calculate summary statistics for a wind speed range.

    Default range is the productive range for wind turbines: 3~25 m/s.

    Args:
        wind_speeds: Wind speed measurements in m/s
        min_speed: Minimum speed for range (default: PRODUCTIVE_RANGE[0])
        max_speed: Maximum speed for range (default: PRODUCTIVE_RANGE[1])
        air_density: Air density in kg/m³ for mean power density (default:
            standard sea-level density)

    Returns:
        Dictionary with count, frequency, mean_speed, mean_power, occurrence_hours.
    """
    empty_result = {
        "count": 0.0,
        "frequency": 0.0,
        "mean_speed": 0.0,
        "mean_power": 0.0,
        "occurrence_hours": 0.0,
    }

    if not wind_speeds:
        return empty_result

    min_val = min_speed if min_speed is not None else PRODUCTIVE_RANGE[0]
    max_val = max_speed if max_speed is not None else PRODUCTIVE_RANGE[1]

    ws_array = np.array(wind_speeds, dtype=np.float64)
    mask = (ws_array >= min_val) & (ws_array < max_val)
    range_ws = ws_array[mask]

    total_count = len(ws_array)
    range_count = len(range_ws)

    if range_count == 0:
        return empty_result

    frequency = range_count / total_count
    mean_speed = float(np.mean(range_ws))
    mean_power = float(0.5 * air_density * np.mean(range_ws**3))
    occurrence_hours = frequency * HOURS_PER_YEAR

    return {
        "count": float(range_count),
        "frequency": frequency,
        "mean_speed": mean_speed,
        "mean_power": mean_power,
        "occurrence_hours": occurrence_hours,
    }


def _empty_wind_frequency_dataframe() -> pl.DataFrame:
    """Create an empty DataFrame with WindFrequencySchema columns."""
    return pl.DataFrame({
        "height": pl.Series([], dtype=pl.Float64),
        "interpolation_marker": pl.Series([], dtype=pl.String),
        "bin_start": pl.Series([], dtype=pl.Float64),
        "bin_end": pl.Series([], dtype=pl.Float64),
        "bin_center": pl.Series([], dtype=pl.Float64),
        "frequency": pl.Series([], dtype=pl.Float64),
        "occurrence_hours": pl.Series([], dtype=pl.Float64),
        "power_frequency": pl.Series([], dtype=pl.Float64),
        "power_hours": pl.Series([], dtype=pl.Float64),
    })


def _process_sensor_data(
    df: pl.DataFrame,
    sensor: SensorColumn,
    ground_air_density: float,
) -> pl.DataFrame | None:
    """Process a single wind speed sensor into wind frequency bins.

    Eliminates the `rows: list[dict]` pattern by building a Polars DataFrame
    directly from grouped statistics.

    Args:
        df: Full time series DataFrame
        sensor: Wind speed sensor metadata
        ground_air_density: Mast ground air density (kg/m³) from config;
            extrapolated to the sensor height via the barometric formula.

    Returns:
        Polars DataFrame with WindFrequencySchema columns, or None if the sensor
        has insufficient data.
    """
    ws_col = sensor.column_name
    if ws_col not in df.columns:
        return None

    ws_series = df.filter(pl.col(ws_col).is_not_null())[ws_col]
    total_count = ws_series.len()
    if total_count < MIN_SAMPLES:
        return None

    ws_df = pl.DataFrame({"ws": ws_series}).with_columns(
        pl.col("ws").floor().cast(pl.Int64).clip(0, int(MAX_BIN)).alias("bin_idx")
    )

    histogram = ws_df.group_by("bin_idx").agg(pl.len().alias("count"))

    rho = calculate_air_density_at_height(sensor.height, ground_density=ground_air_density)
    ws_df = ws_df.with_columns((0.5 * rho * pl.col("ws").pow(3)).alias("power"))
    total_power = ws_df["power"].sum()

    if total_power == 0:
        power_freq = pl.DataFrame({
            "bin_idx": list(range(int(MAX_BIN) + 1)),
            "power_frequency": [0.0] * (int(MAX_BIN) + 1),
        })
    else:
        power_freq = ws_df.group_by("bin_idx").agg(
            (pl.col("power").sum() / total_power).alias("power_frequency")
        )

    all_bins = pl.DataFrame({"bin_idx": list(range(int(MAX_BIN) + 1))})
    result = (
        all_bins
        .join(histogram, on="bin_idx", how="left")
        .join(power_freq, on="bin_idx", how="left")
        .with_columns(
            pl.col("count").fill_null(0).alias("count"),
            pl.col("power_frequency").fill_null(0.0).alias("power_frequency"),
        )
        .with_columns((pl.col("count") / total_count).alias("frequency"))
        .with_columns(
            (pl.col("frequency") * HOURS_PER_YEAR).round(0).alias("occurrence_hours"),
            (pl.col("power_frequency") * HOURS_PER_YEAR).round(0).alias("power_hours"),
        )
        .with_columns(
            pl.col("bin_idx").cast(pl.Float64).alias("bin_start"),
            pl.when(pl.col("bin_idx") < int(MAX_BIN))
            .then(pl.col("bin_idx") + 1)
            .otherwise(100.0)
            .alias("bin_end"),
            (pl.col("bin_idx") + 0.5).alias("bin_center"),
            pl.lit(sensor.height).alias("height"),
            pl.lit(sensor.detect_interpolation_marker()).alias("interpolation_marker"),
        )
        .select([
            "height",
            "interpolation_marker",
            "bin_start",
            "bin_end",
            "bin_center",
            "frequency",
            "occurrence_hours",
            "power_frequency",
            "power_hours",
        ])
    )

    return result


def compute_wind_frequency(data: TimeSeriesData, ground_air_density: float) -> pl.DataFrame:
    """Compute wind frequency distribution for all wind speed sensors.

    Pure function — no IO, no side effects. Replaces the stateful
    WindFrequencyCalculator class from assessment.

    Args:
        data: TimeSeriesData containing DataFrame and sensor metadata
        ground_air_density: Mast ground air density (kg/m³) from config
            (written by the recommend phase); extrapolated per sensor height
            for power calculations.

    Returns:
        Polars DataFrame with WindFrequencySchema columns.
    """
    df = data.df
    sensors = data.sensors

    ws_avg_sensors = [
        s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]

    sensor_dfs: list[pl.DataFrame] = []
    for sensor in ws_avg_sensors:
        sensor_df = _process_sensor_data(df, sensor, ground_air_density)
        if sensor_df is not None:
            sensor_dfs.append(sensor_df)

    if not sensor_dfs:
        return _empty_wind_frequency_dataframe()

    return pl.concat(sensor_dfs)
