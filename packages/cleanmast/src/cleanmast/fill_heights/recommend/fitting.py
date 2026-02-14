"""Strategy-independent fitting functions for shear and direction change.

This module contains the core mathematical fitting functions used to estimate
parameters from existing sensor data. These functions are "strategy-independent"
meaning they only compute parameters; they don't make decisions about which
parameters to use (that's the planner's job).

Separation of Concerns:
========================

    Fitting Layer (this module):
    - calculate_ws_shear(): Fits shear from any set of heights
    - calculate_wd_deg_diff(): Fits deg_diff from any set of heights
    - get_top_heights(): Gets top N heights from sensors

    Planning Layer (planner.py):
    - Decides which heights to use (top3, neighbors, etc.)
    - Builds configurations using fitted parameters
    - Manages dual-config generation

Why This Separation?
====================

1. Testability: Fitting functions can be tested in isolation
2. Reusability: Same fitting functions used for different strategies
3. Clarity: Each layer has a single responsibility
4. Flexibility: Easy to add new strategies without changing fitting logic

Wind Speed Fitting (Log-Log Regression):
=========================================

The power law for wind speed is:
    V2 = V1 * (H2 / H1)^α

Taking natural logs:
    ln(V2) = ln(V1) + α * ln(H2 / H1)
    ln(V2) = ln(V1) + α * (ln(H2) - ln(H1))

This is linear in α! So we can fit using simple linear regression:
    ln(V) = intercept + α * ln(H)

The slope (α) is the shear exponent.

Why Log-Log?
=============

1. Power law becomes linear in log-log space
2. Simple least squares gives optimal fit in log space
3. Standard approach in wind energy (IEC 61400 standards)
4. Geometric mean interpretation (appropriate for multiplicative processes)

Wind Direction Fitting (Vector-Based):
======================================

Direct degree arithmetic fails for circular quantities.
Instead, we:

1. Convert mean directions at each height to (u, v) vectors
2. Calculate the angular change between lowest and highest vectors
3. Divide by height difference to get deg_diff_per_m

This handles wraparound (0°/360°) automatically through vector math.

Implementation:
    cross = u1*v2 - v1*u2  (2D cross product)
    dot = u1*u2 + v1*v2     (dot product)
    angle_diff = atan2(cross, dot)  # Signed angle between vectors

The sign tells us:
    - Positive = clockwise rotation (veering) with height
    - Negative = counter-clockwise (backing) with height
"""

import logging

import numpy as np
import polars as pl
from typing import Literal, cast

from ...models.sensor import SensorColumn
from ...models.timeseries import TimeSeriesData

logger = logging.getLogger(__name__)


# Default limits for deg_diff_per_m (degrees per meter)
# Default: ±22.5° over 20m = ±1.125 deg/m
DEFAULT_DEG_DIFF_PER_M_LIMIT: float = 22.5 / 20  # 1.125 deg/m


def snap_to_limits(value: float, limit: float) -> float:
    """Snap a value to be within [-limit, limit].

    Args:
        value: The value to snap
        limit: The absolute limit (must be positive)

    Returns:
        Value snapped to [-limit, limit]

    Example:
        snap_to_limits(2.0, 1.125) -> 1.125
        snap_to_limits(-2.0, 1.125) -> -1.125
        snap_to_limits(0.5, 1.125) -> 0.5
    """
    return max(-limit, min(limit, value))


def _get_avg_sensors(
    timeseries: TimeSeriesData, sensor_type: str
) -> list[SensorColumn]:
    """Filter sensors by type and avg stat_type.

    Internal helper that extracts SensorColumn objects for sensors
    matching the criteria. Used by fitting functions to get the
    data they need.

    CRITICAL: Only uses avg sensors, not min/max/sd.
    Average sensors represent typical conditions and are appropriate
    for fitting shear and direction change parameters.

    Args:
        timeseries: Time series data with attached sensor definitions
        sensor_type: Type of sensor to filter ('WindSpeed' or 'WindDirection')

    Returns:
        List of SensorColumn objects, sorted by height ascending

    Example:
        _get_avg_sensors(ts, 'WindSpeed')
        -> [SensorColumn(height=40.0, column_name='WS_40m_avg', ...), ...]
    """
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
    """Find WS sensor closest to target height within max_height_diff.

    Args:
        timeseries: Time series data with sensor definitions
        target_height: Target height to find nearby sensor
        max_height_diff: Maximum allowed height difference (default: 20.0m)

    Returns:
        Closest WindSpeed sensor if found within range, None otherwise

    Example:
        _find_nearby_ws_sensor(ts, 80.0)
        -> SensorColumn(height=80.0, sensor_type="WindSpeed", ...)
    """
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
    """Get top N sensors for a sensor type (avg only), sorted by height descending.

    Returns the N highest sensors, sorted descending by height.
    Used by strategies that fit from the top layers.

    Args:
        timeseries: Time series data with sensor definitions
        sensor_type: Type of sensor ('WindSpeed' or 'WindDirection')
        n: Number of top sensors to return (default 3)

    Returns:
        List of top N SensorColumn objects (sorted descending by height)

    Example:
        sensors at [40, 60, 80, 100, 120]m
        get_top_sensors(ts, 'WindSpeed', n=3)
        -> [SensorColumn(height=120.0, ...), SensorColumn(height=100.0, ...), ...]
    """
    avg_sensors = _get_avg_sensors(timeseries, sensor_type)
    # Sort by height descending and take top n
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

    Args:
        timeseries: Time series data with wind speed columns
        source_sensors: List of SensorColumn objects to use for fitting

    Returns:
        Shear exponent α

    Raises:
        ValueError: If fewer than 2 valid sensors available
        ValueError: If unable to extract sufficient data

    Physical Interpretation:
        α < 0.1: Very stable conditions (temperature inversion)
        α = 0.1-0.2: Neutral stability (typical)
        α > 0.2: Unstable conditions (daytime/convective)

    Example:
        sensors = [SensorColumn(height=80.0, ...), SensorColumn(height=100.0, ...)]
        calculate_ws_shear(ts, sensors)
        -> 0.147  (typical neutral stability shear)
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

    # Linear regression: ln_speeds = intercept + shear * ln_heights
    coeffs = np.polyfit(ln_heights, ln_speeds, 1)
    shear = coeffs[0]  # Slope is the shear exponent

    return float(shear)


def _degrees_to_vector(degrees: float) -> tuple[float, float]:
    """Convert wind direction in degrees to (u, v) unit vector components.

    Wind direction is the direction the wind is coming FROM.
    Convention: 0° = North (wind from North), 90° = East (wind from East)

    Vector components follow standard Cartesian convention:
    - u: East-West axis (positive = East)
    - v: North-South axis (positive = North)

    The negative signs in formulas account for meteorological convention
    (direction FROM) vs mathematical convention (direction TO).

    Args:
        degrees: Wind direction in degrees (0-360)

    Returns:
        Tuple of (u, v) components as floats in range [-1, 1]

    Example:
        _degrees_to_vector(0)   -> (0.0, -1.0)   # From North
        _degrees_to_vector(90)  -> (1.0, 0.0)    # From East
        _degrees_to_vector(180) -> (0.0, 1.0)    # From South
        _degrees_to_vector(270) -> (-1.0, 0.0)   # From West
    """
    # Convert to radians and calculate vector
    # u = -sin(θ), v = -cos(θ) for wind FROM direction
    rad = np.radians(degrees)
    u = -np.sin(rad)
    v = -np.cos(rad)
    return float(u), float(v)


def _vector_to_degrees(u: float, v: float) -> float:
    """Convert (u, v) vector to wind direction in degrees.

    Wind direction is the direction the wind is coming FROM.

    Uses arctan2 to compute the angle from the positive v-axis
    (North), going clockwise (meteorological convention).

    Args:
        u: East-West component (positive = East)
        v: North-South component (positive = North)

    Returns:
        Wind direction in degrees (0, 360)

    Example:
        _vector_to_degrees(0.0, -1.0) -> 0.0     # From North
        _vector_to_degrees(1.0, 0.0)  -> 90.0    # From East
        _vector_to_degrees(0.0, 1.0)  -> 180.0    # From South
        _vector_to_degrees(-1.0, 0.0) -> 270.0    # From West
    """
    # atan2(u, v) gives angle from North, clockwise
    degrees = np.degrees(np.arctan2(u, v))
    # Normalize to [0, 360)
    return float(degrees % 360)


def _calculate_mean_vector_direction(
    timeseries: TimeSeriesData, col: str
) -> float | None:
    """Calculate mean wind direction using vector averaging.

    Vector averaging properly handles the circular nature of wind direction.
    This avoids the problem where simple averaging of 350° and 10° gives 180°
    instead of the correct ~0°.

    Algorithm:
    1. Convert each direction to (u, v) vector
    2. Sum all vectors component-wise
    3. Convert mean vector back to degrees

    Args:
        timeseries: Time series data containing the wind direction column
        col: Column name with wind direction data (degrees)

    Returns:
        Mean wind direction in degrees, or None if no valid data

    Example:
        # Mean of 350° and 10° should be ~0° (or 360°)
        _calculate_mean_vector_direction(ts, 'WD_80m_avg')
        -> 0.0  # Correct!
    """
    if col not in timeseries.df.columns:
        return None

    values = timeseries.df[col].drop_nulls()
    if len(values) == 0:
        return None

    # Convert all directions to vectors and sum
    sum_u = 0.0
    sum_v = 0.0

    for wd in values:
        u, v = _degrees_to_vector(float(wd))
        sum_u += u
        sum_v += v

    # Mean direction from mean vector
    return _vector_to_degrees(sum_u, sum_v)


def calculate_wd_deg_diff(
    timeseries: TimeSeriesData,
    source_sensors: list[SensorColumn],
    limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
    ws_threshold: float = 2.5,
) -> float:
    """Calculate deg_diff_per_m from any set of sensors using scattered data fit.

    Uses all data points (all heights x all timestamps) for robust linear regression.
    This is more statistically sound than averaging per-timestamp diffs.

    Algorithm:
    1. Find nearby WS sensor for wind speed filtering
    2. Filter data to periods with WS > ws_threshold (reliable WD readings)
    3. Use lowest sensor as base reference
    4. For each other sensor: calculate (h_diff, deg_diff) for all timestamps
    5. Handle wraparound using ((diff + 540) % 360) - 180 -> [-180, 180]
    6. Add base height constraint (0 h_diff = 0 deg_diff)
    7. Linear regression on all scattered points: deg_diff = intercept + slope * h_diff
    8. Return slope as deg_diff_per_m (snapped to [-limit, limit])

    Args:
        timeseries: Time series data with wind direction columns
        source_sensors: List of SensorColumn objects to use for fitting
        limit: Maximum absolute value for deg_diff_per_m (default: 1.125 deg/m)
        ws_threshold: Minimum wind speed for reliable WD readings (default: 2.5 m/s)

    Returns:
        Direction change per meter (degrees/meter), snapped to limits

    Raises:
        ValueError: If fewer than 2 sensors provided or insufficient data
    """
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
        # Filter to periods with reliable wind direction (WS > threshold)
        base_df = timeseries.df.filter(pl.col(ws_sensor.column_name) > ws_threshold)
        logger.debug(
            f"Filtered {len(timeseries.df)} rows to {len(base_df)} rows "
            f"using WS > {ws_threshold} from {ws_sensor.column_name}"
        )

    data_frames: list[pl.DataFrame] = []

    for sensor in sorted_sensors[1:]:
        col = sensor.column_name
        height_diff = sensor.height - base_height

        # Calculate degree difference with wraparound handling in Polars
        # Wraparound formula: ((diff + 540) % 360) - 180 gives [-180, 180]
        deg_diff_expr = (
            ((pl.col(col) - pl.col(base_col) + 540) % 360) - 180
        )

        # Create DataFrame with height diff and degree diff for valid pairs
        pair_df = base_df.select([
            pl.lit(height_diff).alias("h_diff"),
            deg_diff_expr.alias("deg_diff"),
        ]).drop_nulls()

        if len(pair_df) > 0:
            data_frames.append(pair_df)

    if not data_frames:
        raise ValueError("Insufficient valid data points for deg_diff fitting")

    # Concatenate all scatter points
    scatter_df = pl.concat(data_frames)

    # Add base height constraint: enforce that 0 height diff = 0 degree diff
    # This ensures regression passes through origin
    valid_count = len(scatter_df)
    constraint_df = pl.DataFrame({
        "h_diff": [0.0] * valid_count,
        "deg_diff": [0.0] * valid_count,
    })
    scatter_df = pl.concat([scatter_df, constraint_df])

    if len(scatter_df) < 2:
        raise ValueError("Insufficient valid data points for deg_diff fitting")

    # Linear regression: deg_diff = intercept + slope * h_diff
    # Slope is deg_diff_per_m (relative to base height)
    coeffs = np.polyfit(
        scatter_df["h_diff"].to_numpy(),
        scatter_df["deg_diff"].to_numpy(),
        1
    )
    deg_diff_per_m = float(coeffs[0])

    # Snap to limits
    return snap_to_limits(deg_diff_per_m, limit)


def fit_shear_top3(
    timeseries: TimeSeriesData,
) -> float:
    """Fit shear from top 3 existing layers.

    Wrapper function that gets top 3 sensors and fits shear from them.
    Uses the highest layers because:
    1. They're most relevant for extrapolation to higher targets
    2. Less affected by ground effects (roughness)
    3. More representative of free-stream conditions

    Args:
        timeseries: Time series data with wind speed columns

    Returns:
        Shear exponent fitted from top 3 layers

    Example:
        fit_shear_top3(ts)
        -> 0.142  # Shear from top 3 heights
    """
    sensors = get_top_sensors(timeseries, "WindSpeed", n=3)
    return calculate_ws_shear(timeseries, sensors)


def fit_shear_neighbors(
    timeseries: TimeSeriesData,
    lower: SensorColumn,
    higher: SensorColumn,
) -> float:
    """Fit shear from two neighboring layers.

    Wrapper function that fits shear from exactly two sensors.
    Used for interpolation between those same heights.

    Args:
        timeseries: Time series data with wind speed columns
        lower: Lower reference sensor
        higher: Higher reference sensor

    Returns:
        Shear exponent fitted from the two neighbor sensors

    Example:
        fit_shear_neighbors(ts, SensorColumn(height=80.0, ...), SensorColumn(height=100.0, ...))
        -> 0.135  # Local shear between 80m and 100m
    """
    return calculate_ws_shear(timeseries, [lower, higher])


def fit_deg_diff_top3(
    timeseries: TimeSeriesData,
    limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
    ws_threshold: float = 2.5,
) -> float:
    """Fit deg_diff_per_m from top 3 WD layers.

    Wrapper function that gets top 3 wind direction sensors and fits
    the direction change per meter. Uses top layers for same reasons
    as shear fitting.

    Args:
        timeseries: Time series data with wind direction columns
        limit: Maximum absolute value for deg_diff_per_m (default: 1.125 deg/m)
        ws_threshold: Minimum wind speed for reliable WD readings (default: 2.5 m/s)

    Returns:
        Direction change per meter fitted from top 3 layers

    Example:
        fit_deg_diff_top3(ts)
        -> 0.12  # 0.12°/m veering from top 3 WD sensors
    """
    sensors = get_top_sensors(timeseries, "WindDirection", n=3)
    return calculate_wd_deg_diff(timeseries, sensors, limit, ws_threshold)


def fit_deg_diff_neighbors(
    timeseries: TimeSeriesData,
    lower: SensorColumn,
    higher: SensorColumn,
    limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
    ws_threshold: float = 2.5,
) -> float:
    """Fit deg_diff_per_m from two neighboring WD layers.

    Wrapper function that fits direction change from exactly two sensors.
    Used for interpolation between those same heights.

    Args:
        timeseries: Time series data with wind direction columns
        lower: Lower reference sensor
        higher: Higher reference sensor
        limit: Maximum absolute value for deg_diff_per_m (default: 1.125 deg/m)
        ws_threshold: Minimum wind speed for reliable WD readings (default: 2.5 m/s)

    Returns:
        Direction change per meter fitted from the two neighbor sensors

    Example:
        fit_deg_diff_neighbors(ts, SensorColumn(height=80.0, ...), SensorColumn(height=100.0, ...))
        -> 0.10  # Local direction change between 80m and 100m
    """
    return calculate_wd_deg_diff(timeseries, [lower, higher], limit, ws_threshold)
