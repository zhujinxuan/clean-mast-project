"""Pure helper functions for fill-heights operations.

This module contains stateless utility functions used throughout the fill-heights
system. All functions are pure (no side effects, no external dependencies) making
them easy to test and reason about.

Categories of Functions:
========================

1. Sensor Queries (NEW - SensorColumn based):
   - get_existing_sensors(): Get all sensors of a type sorted by height
   - get_top_sensors(): Get top N sensors sorted by height descending
   - find_neighbor_sensors(): Find lower and higher neighbor sensors
   - get_sensor_for_height(): Find sensor at specific height
   - create_fill_target_sensor(): Create SensorColumn for fill target

2. Column Name Generation (DEPRECATED):
   - generate_target_column(): Create standardized column names (deprecated)

3. Neighbor/Weight Calculations:
   - calculate_interpolation_weights(): Compute 1/distance weights

4. Data Validation:
   - check_min_overlap(): Verify sufficient concurrent data between columns

5. Vector Math (CRITICAL FOR WIND DIRECTION):
   - degrees_to_vector(): Convert wind direction to (u, v) components
   - vector_to_degrees(): Convert (u, v) back to degrees

Vector Math Explanation:
========================

Wind direction is a CIRCULAR quantity (0° ≡ 360°). Direct arithmetic fails:

    WRONG: (350° + 10°) / 2 = 180°  (should be 0° or 360°!)
    RIGHT: Use vector components

The vector approach:
1. Convert each direction to unit vector (u, v)
2. Average the vectors component-wise
3. Convert back to degrees

This handles wraparound automatically because:
- 0° = (0, -1)  [wind from north]
- 90° = (1, 0)   [wind from east]
- 180° = (0, 1)  [wind from south]
- 270° = (-1, 0) [wind from west]
- 350° ≈ (0, -0.985) [close to north]
- 10° ≈ (0.174, -0.985) [close to north]

Averaging vectors from 350° and 10° gives a vector pointing north,
correctly yielding ~0° (or 360°).
"""

from typing import Literal

import numpy as np

from ...models.sensor import SensorColumn
from ...models.timeseries import TimeSeriesData


def get_existing_sensors(
    sensors: list[SensorColumn],
    sensor_type: Literal["WindSpeed", "WindDirection"]
) -> list[SensorColumn]:
    """Get sorted list of existing average sensors.

    Filters sensors by type and stat_type='avg', then returns them
    sorted by height in ascending order.

    Args:
        sensors: List of SensorColumn definitions from the timeseries
        sensor_type: Type of sensor to filter ('WindSpeed' or 'WindDirection')

    Returns:
        Sorted list of SensorColumn objects with stat_type='avg'

    Example:
        sensors = [WS_80m_avg, WS_100m_avg, WD_80m_avg]
        get_existing_sensors(sensors, "WindSpeed") -> [WS_80m_avg, WS_100m_avg]
        get_existing_sensors(sensors, "WindDirection") -> [WD_80m_avg]
    """
    matching = [
        s for s in sensors
        if s.sensor_type == sensor_type and s.stat_type == "avg"
    ]
    return sorted(matching, key=lambda s: s.height)


def get_top_sensors(
    timeseries: TimeSeriesData,
    sensor_type: Literal["WindSpeed", "WindDirection"],
    n: int = 3
) -> list[SensorColumn]:
    """Get top N sensors sorted by height descending.

    Returns the highest N sensors of the specified type, sorted
    from highest to lowest height.

    Args:
        timeseries: TimeSeriesData containing sensors
        sensor_type: Type of sensor to filter ('WindSpeed' or 'WindDirection')
        n: Number of top sensors to return (default 3)

    Returns:
        List of top N SensorColumn objects sorted by height descending

    Example:
        sensors = [WS_50m_avg, WS_80m_avg, WS_100m_avg, WS_120m_avg]
        get_top_sensors(timeseries, "WindSpeed", 2) -> [WS_120m_avg, WS_100m_avg]
    """
    sensors = get_existing_sensors(timeseries.sensors, sensor_type)
    return sorted(sensors, key=lambda s: s.height, reverse=True)[:n]


def generate_target_column(
    sensor_type: Literal["WindSpeed", "WindDirection"],
    height: float,
    method: Literal["interpolated", "extrapolated"]
) -> str:
    """Generate standardized target column name (DEPRECATED).

    .. deprecated::
        Use create_fill_target_sensor() instead to get full SensorColumn
        with properly inherited metadata. This function may be removed
        in a future cleanup.

    Creates a column name following the convention:
    - WindSpeed: WS_{height}m_fill:{method}
    - WindDirection: WD_{height}m_fill:{method}

    Args:
        sensor_type: 'WindSpeed' or 'WindDirection'
        height: Target height in meters (will be converted to integer)
        method: 'interpolated' or 'extrapolated'

    Returns:
        Standardized column name string

    Example:
        generate_target_column("WindSpeed", 120.0, "extrapolated")
        -> "WS_120m_fill:extrapolated"
    """
    prefix = "WS" if sensor_type == "WindSpeed" else "WD"
    return f"{prefix}_{int(height)}m_fill:{method}"


def find_neighbor_sensors(
    target: float,
    sensors: list[SensorColumn]
) -> tuple[SensorColumn, SensorColumn]:
    """Find lower and higher neighbor sensors.

    Given a list of sensors sorted by height, finds the closest sensors
    that bracket the target height (one below, one above).

    Args:
        target: Target height to find neighbors for
        sensors: List of SensorColumn objects (should be sorted by height)

    Returns:
        Tuple of (lower_sensor, higher_sensor)

    Raises:
        ValueError: If cannot find valid neighbors for the target height

    Example:
        sensors = [WS_40m, WS_60m, WS_80m, WS_120m, WS_140m]
        find_neighbor_sensors(100.0, sensors) -> (WS_80m, WS_120m)
    """
    lower = max(
        [s for s in sensors if s.height < target],
        key=lambda s: s.height,
        default=None
    )
    higher = min(
        [s for s in sensors if s.height > target],
        key=lambda s: s.height,
        default=None
    )

    if lower is None or higher is None:
        raise ValueError(f"Cannot find neighbors for {target}m")

    return lower, higher


def create_fill_target_sensor(
    timeseries: TimeSeriesData,
    target_height: float,
    sensor_type: Literal["WindSpeed", "WindDirection"],
    method: Literal["interpolated", "extrapolated"]
) -> SensorColumn:
    """Create a SensorColumn for the fill target.

    Inherits metadata from nearest reference sensor:
    - sensor_direction: From nearest reference
    - unit: From nearest reference

    Generates column name: WS_{height}m_fill:{method} or WD_{height}m_fill:{method}

    Args:
        timeseries: TimeSeriesData containing reference sensors
        target_height: Target height in meters for the fill sensor
        sensor_type: 'WindSpeed' or 'WindDirection'
        method: 'interpolated' or 'extrapolated'

    Returns:
        New SensorColumn configured for the fill target

    Raises:
        ValueError: If no reference sensors exist for the sensor_type

    Example:
        create_fill_target_sensor(ts, 115.0, "WindSpeed", "interpolated")
        -> SensorColumn(column_name="WS_115m_fill:interpolated", ...)
    """
    refs = get_existing_sensors(timeseries.sensors, sensor_type)
    if not refs:
        raise ValueError(f"No reference sensors for {sensor_type}")

    nearest = min(refs, key=lambda s: abs(s.height - target_height))

    prefix = "WS" if sensor_type == "WindSpeed" else "WD"
    column_name = f"{prefix}_{int(target_height)}m_fill:{method}"

    return SensorColumn(
        column_name=column_name,
        sensor_type=sensor_type,
        sensor_direction=nearest.sensor_direction,
        height=target_height,
        stat_type="avg",
        unit=nearest.unit,
    )


def calculate_interpolation_weights(
    target: float,
    lower: float,
    higher: float
) -> tuple[float, float]:
    """Calculate 1/distance weights for linear interpolation.

    Uses inverse-distance weighting, where closer reference points
    get higher weights. This is a standard approach in spatial
    interpolation.

    Weight formula:
        weight_lower = (1/dist_lower) / (1/dist_lower + 1/dist_higher)
        weight_higher = (1/dist_higher) / (1/dist_lower + 1/dist_higher)

    Where:
        dist_lower = target - lower
        dist_higher = higher - target

    Args:
        target: Target height in meters
        lower: Lower reference height (must be < target)
        higher: Higher reference height (must be > target)

    Returns:
        Tuple of (weight_lower, weight_higher) that sum to 1.0

    Example:
        calculate_interpolation_weights(100.0, 80.0, 120.0)
        -> (0.5, 0.5)  # Equal distance from both

        calculate_interpolation_weights(90.0, 80.0, 120.0)
        -> (0.75, 0.25)  # Much closer to lower (10m away vs 30m)
    """
    dist_low = target - lower
    dist_high = higher - target
    total = (1 / dist_low) + (1 / dist_high)

    weight_low = (1 / dist_low) / total
    weight_high = (1 / dist_high) / total

    return weight_low, weight_high


def get_sensor_for_height(
    sensors: list[SensorColumn],
    sensor_type: Literal["WindSpeed", "WindDirection"],
    height: float
) -> SensorColumn | None:
    """Find sensor for given type and height.

    Searches through sensors to find one matching the specified
    type and height with stat_type='avg'.

    Args:
        sensors: List of SensorColumn definitions
        sensor_type: 'WindSpeed' or 'WindDirection'
        height: Exact height to find (floating point comparison)

    Returns:
        Matching SensorColumn or None if not found

    Example:
        get_sensor_for_height(sensors, "WindSpeed", 80.0) -> WS_80m_avg SensorColumn
        get_sensor_for_height(sensors, "WindSpeed", 999.0) -> None
    """
    for s in sensors:
        if (s.sensor_type == sensor_type and
            s.height == height and
            s.stat_type == "avg"):
            return s
    return None


def check_min_overlap(
    timeseries: TimeSeriesData,
    ref1_col: str,
    ref2_col: str,
    min_points: int = 1000
) -> bool:
    """Check if two columns have sufficient concurrent valid data.

    For fitting operations (shear, deg_diff), we need sufficient
    concurrent observations at both reference heights. This function
    checks if both columns have enough non-null values at the same
    timestamps.

    Args:
        timeseries: TimeSeriesData containing the dataframe
        ref1_col: Name of first reference column
        ref2_col: Name of second reference column
        min_points: Minimum concurrent valid observations required (default 1000)

    Returns:
        True if sufficient overlap exists, False otherwise

    Note:
        Default of 1000 points provides statistical significance for
        regression while remaining computationally efficient.
    """
    df = timeseries.df
    # Count rows where both columns have non-null values
    valid_count = df.filter(
        df[ref1_col].is_not_null() & df[ref2_col].is_not_null()
    ).height
    return valid_count >= min_points


def degrees_to_vector(
    degrees: float | np.ndarray,
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Convert wind direction degrees to (u, v) vector components.

    Uses meteorological convention: direction FROM which wind blows.

    Vector components:
        u = East-West component (positive = East)
        v = North-South component (positive = North)

    Formulas:
        u = -sin(θ) where θ is in radians
        v = -cos(θ) where θ is in radians

    The negative signs account for meteorological convention:
    - 0° = North (wind from north) → u=0, v=-1 (pointing south)
    - 90° = East (wind from east) → u=-1, v=0 (pointing west)

    Args:
        degrees: Wind direction in degrees (0-360), either a scalar or array
            0° = North, 90° = East, 180° = South, 270° = West

    Returns:
        Tuple of (u, v) unit vector components (scalars or arrays matching input)

    Example:
        degrees_to_vector(0)   -> (0.0, -1.0)  [from north]
        degrees_to_vector(90)  -> (1.0, 0.0)   [from east]
        degrees_to_vector(180) -> (0.0, 1.0)   [from south]
        degrees_to_vector(270) -> (-1.0, 0.0)  [from west]
    """
    theta_rad = np.radians(degrees)
    u = -np.sin(theta_rad)
    v = -np.cos(theta_rad)
    return u, v


def vector_to_degrees(
    u: float | np.ndarray,
    v: float | np.ndarray,
) -> float | np.ndarray:
    """Convert (u, v) vector components back to wind direction degrees.

    Uses atan2 to compute the angle from the vector, then converts
    to degrees and normalizes to [0, 360).

    The result represents the direction the wind is coming FROM.

    Args:
        u: East-West component (positive = East), scalar or array
        v: North-South component (positive = North), scalar or array

    Returns:
        Wind direction in degrees [0, 360), scalar or array matching inputs

    Example:
        vector_to_degrees(0.0, -1.0) -> 0.0     [from north]
        vector_to_degrees(1.0, 0.0)  -> 90.0    [from east]
        vector_to_degrees(0.0, 1.0)  -> 180.0   [from south]
        vector_to_degrees(-1.0, 0.0) -> 270.0   [from west]

    Note:
        The arctan2(y, x) function gives angle from positive x-axis.
        We use atan2(-u, -v) to get meteorological direction convention.
    """
    theta_rad = np.arctan2(-u, -v)
    degrees = np.degrees(theta_rad)
    return degrees % 360
