"""Strategy-independent fitting functions for shear and direction change.

Description: Mathematical fitting functions for shear and direction change

This module contains the core mathematical fitting functions used to estimate
parameters from existing sensor data. These functions are "strategy-independent"
meaning they only compute parameters; they don't make decisions about which
parameters to use (that's the planner's job).
"""

import logging
from typing import Literal, cast

import numpy as np
import polars as pl

from cleanmast.shared.timeseries import (
    SensorColumn,
    TimeSeriesData,
)

logger = logging.getLogger(__name__)

DEFAULT_DEG_DIFF_PER_M_LIMIT: float = 22.5 / 20


def snap_to_limits(value: float, limit: float) -> float:
    """Snap a value to be within [-limit, limit]."""
    return max(-limit, min(limit, value))


def _get_avg_sensors(
    timeseries: TimeSeriesData, sensor_type: str
) -> list[SensorColumn]:
    """Filter sensors by type and avg stat_type."""
    return sorted(
        [
            s
            for s in timeseries.sensors
            if s.sensor_type == sensor_type and s.stat_type == "avg"
        ],
        key=lambda s: s.height
    )


def _find_nearby_ws_sensor(
    timeseries: TimeSeriesData,
    target_height: float,
    max_height_diff: float = 20.0,
) -> SensorColumn | None:
    """Find WS sensor closest to target height within max_height_diff."""
    ws_sensors = [
        s for s in timeseries.sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]

    if not ws_sensors:
        return None

    closest = min(ws_sensors, key=lambda s: abs(s.height - target_height))

    if abs(closest.height - target_height) <= max_height_diff:
        return closest
    return None


def get_top_sensors(
    timeseries: TimeSeriesData,
    sensor_type: Literal["WindSpeed", "WindDirection"],
    n: int = 3
) -> list[SensorColumn]:
    """Get top N sensors for a sensor type (avg only), sorted by height descending."""
    avg_sensors = _get_avg_sensors(timeseries, sensor_type)
    sorted_sensors = sorted(avg_sensors, key=lambda s: s.height, reverse=True)
    return sorted_sensors[:n]


def calculate_ws_shear(
    timeseries: TimeSeriesData,
    source_sensors: list[SensorColumn],
) -> float:
    """Calculate power law shear exponent from any set of sensors.

    Implements log-log linear regression to fit shear exponent.
    The power law: V2 = V1 * (H2/H1)^α

    Algorithm:
    1. Extract mean wind speeds at each source sensor
    2. Filter out sensors without data or with zero/negative speeds
    3. Transform to log space: ln(V), ln(H)
    4. Fit linear regression: ln(V) = intercept + α * ln(H)
    5. Return slope (α) as the shear exponent
    """
    if len(source_sensors) < 2:
        raise ValueError("At least 2 sensors required to fit shear")

    # Extract mean wind speeds at each sensor
    heights: list[float] = []
    speeds: list[float] = []

    for sensor in source_sensors:
        col = sensor.column_name
        if col not in timeseries.df.columns:
            continue

        mean_value = timeseries.df[col].drop_nulls().mean()
        if mean_value is not None:
            mean_float = cast(float, mean_value)
            if mean_float > 0:
                heights.append(sensor.height)
                speeds.append(mean_float)

    if len(heights) < 2:
        raise ValueError(
            f"Need at least 2 valid height measurements to fit shear, "
            f"got {len(heights)}"
        )

    # Fit linear regression on ln(V) vs ln(H)
    ln_heights = np.log(heights)
    ln_speeds = np.log(speeds)

    coeffs = np.polyfit(ln_heights, ln_speeds, 1)
    shear = coeffs[0]

    return float(shear)


def _degrees_to_vector(degrees: float) -> tuple[float, float]:
    """Convert wind direction in degrees to (u, v) unit vector components."""
    rad = np.radians(degrees)
    u = -np.sin(rad)
    v = -np.cos(rad)
    return float(u), float(v)


def _vector_to_degrees(u: float, v: float) -> float:
    """Convert (u, v) vector to wind direction in degrees."""
    degrees = np.degrees(np.arctan2(u, v))
    return float(degrees % 360)


def calculate_wd_deg_diff(
    timeseries: TimeSeriesData,
    source_sensors: list[SensorColumn],
    limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
    ws_threshold: float = 2.5,
) -> float:
    """Calculate deg_diff_per_m from any set of sensors using scattered data fit."""
    if len(source_sensors) < 2:
        raise ValueError("At least 2 sensors required to fit deg_diff")

    sorted_sensors = sorted(source_sensors, key=lambda s: s.height)
    base_sensor = sorted_sensors[0]
    base_height = base_sensor.height
    base_col = base_sensor.column_name

    # Find nearby WS sensor for wind speed filtering
    ws_sensor = _find_nearby_ws_sensor(timeseries, base_height)
    if ws_sensor is None:
        logger.warning(
            f"No nearby WS sensor found for WD at {base_height}m, "
            "proceeding without wind speed filtering"
        )
        base_df = timeseries.df
    else:
        base_df = timeseries.df.filter(pl.col(ws_sensor.column_name) > ws_threshold)

    data_frames: list[pl.DataFrame] = []

    for sensor in sorted_sensors[1:]:
        col = sensor.column_name
        height_diff = sensor.height - base_height

        deg_diff_expr = (
            ((pl.col(col) - pl.col(base_col) + 540) % 360) - 180
        )

        pair_df = base_df.select([
            pl.lit(height_diff).alias("h_diff"),
            deg_diff_expr.alias("deg_diff"),
        ]).drop_nulls()

        if len(pair_df) > 0:
            data_frames.append(pair_df)

    if not data_frames:
        raise ValueError("Insufficient valid data points for deg_diff fitting")

    scatter_df = pl.concat(data_frames)

    # Add base height constraint
    valid_count = len(scatter_df)
    constraint_df = pl.DataFrame({
        "h_diff": [0.0] * valid_count,
        "deg_diff": [0.0] * valid_count,
    })
    scatter_df = pl.concat([scatter_df, constraint_df])

    if len(scatter_df) < 2:
        raise ValueError("Insufficient valid data points for deg_diff fitting")

    coeffs = np.polyfit(
        scatter_df["h_diff"].to_numpy(),
        scatter_df["deg_diff"].to_numpy(),
        1
    )
    deg_diff_per_m = float(coeffs[0])

    return snap_to_limits(deg_diff_per_m, limit)


def fit_shear_top3(
    timeseries: TimeSeriesData,
) -> float:
    """Fit shear from top 3 existing layers."""
    sensors = get_top_sensors(timeseries, "WindSpeed", n=3)
    return calculate_ws_shear(timeseries, sensors)


def fit_shear_neighbors(
    timeseries: TimeSeriesData,
    lower: SensorColumn,
    higher: SensorColumn,
) -> float:
    """Fit shear from two neighboring layers."""
    return calculate_ws_shear(timeseries, [lower, higher])


def fit_deg_diff_top3(
    timeseries: TimeSeriesData,
    limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
    ws_threshold: float = 2.5,
) -> float:
    """Fit deg_diff_per_m from top 3 WD layers."""
    sensors = get_top_sensors(timeseries, "WindDirection", n=3)
    return calculate_wd_deg_diff(timeseries, sensors, limit, ws_threshold)


def fit_deg_diff_neighbors(
    timeseries: TimeSeriesData,
    lower: SensorColumn,
    higher: SensorColumn,
    limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
    ws_threshold: float = 2.5,
) -> float:
    """Fit deg_diff_per_m from two neighboring WD layers."""
    return calculate_wd_deg_diff(timeseries, [lower, higher], limit, ws_threshold)
