"""Wind shear calculation functions.

Functions for extrapolating wind speed and direction using power law
and linear models.
"""

from typing import Union

import numpy as np
from numpy.typing import ArrayLike, NDArray


def extrapolate_wind_speed(
    wind_speed: Union[float, ArrayLike],
    reference_height: float,
    target_height: float,
    shear: float,
) -> Union[float, NDArray[np.floating]]:
    """Extrapolate wind speed using power law.

    Formula: V2 = V1 * (H2/H1)^α

    Where:
        V1 = wind speed at reference height
        V2 = wind speed at target height
        H1 = reference height
        H2 = target height
        α = shear exponent

    Args:
        wind_speed: Wind speed at reference height (m/s)
        reference_height: Reference measurement height (m)
        target_height: Target extrapolation height (m)
        shear: Power law shear exponent (α)

    Returns:
        Extrapolated wind speed at target height (m/s)
    """
    return wind_speed * (target_height / reference_height) ** shear


def calculate_shear_exponent(
    v1: float,
    h1: float,
    v2: float,
    h2: float,
) -> float:
    """Calculate shear exponent from two height measurements.

    From the power law: V2/V1 = (H2/H1)^α
    Solving for α: α = ln(V2/V1) / ln(H2/H1)

    Args:
        v1: Wind speed at height h1 (m/s)
        h1: Lower measurement height (m)
        v2: Wind speed at height h2 (m/s)
        h2: Upper measurement height (m)

    Returns:
        Shear exponent (α)

    Raises:
        ValueError: If heights are equal
    """
    if h1 == h2:
        raise ValueError("Heights must be different to calculate shear")

    return np.log(v2 / v1) / np.log(h2 / h1)


def fit_shear_from_heights(
    heights: ArrayLike,
    speeds: ArrayLike,
) -> float:
    """Fit shear exponent from multiple height measurements using linear regression.

    Uses the linearized power law:
        ln(V) = ln(V_ref) + α * ln(H/H_ref)

    This is equivalent to fitting: y = a + α*x
    where y = ln(V), x = ln(H), a = ln(V_ref) - α*ln(H_ref)

    Args:
        heights: Array of measurement heights (m)
        speeds: Array of wind speeds at corresponding heights (m/s)

    Returns:
        Fitted shear exponent (α)

    Raises:
        ValueError: If fewer than 2 heights provided
    """
    heights = np.asarray(heights)
    speeds = np.asarray(speeds)

    if len(heights) < 2:
        raise ValueError("At least 2 height measurements required to fit shear")

    # Linearize: ln(V) = ln(V_ref) + α * ln(H/H_ref)
    # Using H_ref = 1 for simplicity: ln(V) = a + α * ln(H)
    ln_heights = np.log(heights)
    ln_speeds = np.log(speeds)

    # Linear regression: ln_speeds = intercept + shear * ln_heights
    # Using numpy's polyfit (degree 1)
    coeffs = np.polyfit(ln_heights, ln_speeds, 1)
    shear = coeffs[0]  # Slope is the shear exponent

    return float(shear)


def extrapolate_wind_direction(
    wind_direction: Union[float, ArrayLike],
    reference_height: float,
    target_height: float,
    deg_diff_per_m: float,
) -> Union[float, NDArray[np.floating]]:
    """Extrapolate wind direction using linear model.

    Formula: WD2 = WD1 + deg_diff_per_m * (H2 - H1)

    The result is wrapped to [0, 360) degrees.

    Args:
        wind_direction: Wind direction at reference height (degrees, 0-360)
        reference_height: Reference measurement height (m)
        target_height: Target extrapolation height (m)
        deg_diff_per_m: Direction change per meter height difference (degrees/m)

    Returns:
        Extrapolated wind direction at target height (degrees, 0-360)
    """
    height_diff = target_height - reference_height
    direction_change = deg_diff_per_m * height_diff

    # Convert to numpy array for consistent operations
    wd = np.asarray(wind_direction)
    result = wd + direction_change

    # Wrap to [0, 360)
    wrapped = result % 360

    # Return scalar if input was scalar
    if np.isscalar(wind_direction):
        return float(wrapped)
    return wrapped
