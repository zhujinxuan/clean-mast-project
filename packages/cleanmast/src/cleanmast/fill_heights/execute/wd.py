"""Wind direction filling execution functions.

This module implements the execution layer for wind direction height filling.
It applies the fill configurations to actual data.

Critical: Vector-Based Processing
==============================

Wind direction is a CIRCULAR quantity (0° ≡ 360°). Direct arithmetic fails!

BAD: (350° + 10°) / 2 = 180°  (WRONG!)
GOOD: Use vector components → ~0° (CORRECT!)

Vector Math for Wind Direction:
=============================

1. Convert degrees to (u, v) components:
    u = -sin(θ), v = -cos(θ) where θ is in radians
    This uses meteorological convention (direction FROM which wind blows)

2. Process vectors (linear operations work correctly):
    - Extrapolation: Add deg_diff * ΔH to each component
    - Interpolation: Weighted average of vectors (component-wise)

3. Convert back to degrees using atan2:
    θ = atan2(-u, -v) normalized to [0, 360)

This handles wraparound automatically because:
- Vectors don't wrap: (0, -1) for 0°, (0, -0.985) for 10°, etc.
- Adding/subtracting works correctly on components
- atan2 always returns correct angle in [0, 360)

Extrapolation:
=============

    WD_target = WD_ref + deg_diff_per_m * (H_target - H_ref)
    Result wrapped to [0, 360)

Interpolation:
============

1. Extrapolate all references to target height
2. Convert all to (u, v) vectors
3. Weight-average the vectors component-wise
4. Convert back to degrees

Null Handling:
===========

Null values are PRESERVED, not filled. Polars arithmetic operations
naturally propagate nulls - if any reference column has a null value
at a given row, the result is null at that row.
"""

import polars as pl

from ..config import HeightReference
from ...models.sensor import SensorColumn


def apply_wd_fill(
    df: pl.DataFrame,
    target: SensorColumn,
    references: list[HeightReference],
    deg_diff_per_m: float,
) -> pl.Series:
    """Apply wind direction fill (extrapolation or interpolation).

    CRITICAL: Uses VECTOR COMPONENTS to handle 0°/360° wraparound!

    Algorithm:
        1. For each reference: extrapolate to target height
           WD_target = WD_ref + deg_diff_per_m * (H_target - H_ref)
        2. Convert each extrapolated value to (u, v) vector components
        3. Weight each vector by reference weight
        4. Sum all weighted vectors and normalize by total weight
        5. Convert back to degrees

    This handles any number of references (N >= 1):
        - N=1: Simple extrapolation (weight should be 1.0)
        - N=2: Standard interpolation between two references
        - N>2: Multi-reference weighted interpolation

    Why Vector Components?
    ======================

    Direct degree arithmetic fails for circular quantities:

        WRONG:  Average of 350° and 10° = 180°
        CORRECT: Vector average = ~0°

    Vector approach:
    1. 350° → (u≈0.017, v≈-0.985)
    2. 10°  → (u≈0.174, v≈-0.985)
    3. Average: (u≈0.096, v≈-0.985)
    4. atan2(-0.096, -0.985) ≈ ~355° (close to 0°, correct!)

    Null values are preserved (not filled). Polars arithmetic operations
    naturally propagate nulls - if any reference column has a null value
    at a given row, the result is null at that row.

    Args:
        df: Input DataFrame with reference columns
        target: SensorColumn for the target height (column_name and height)
        references: List of HeightReference with at least 1 element
        deg_diff_per_m: Direction change per meter (degrees/meter)
            Positive = veering (clockwise), Negative = backing (counter-clockwise)

    Returns:
        Series with filled wind direction values at target height

    Raises:
        ValueError: If references list is empty

    Example:
        # Single reference: extrapolation
        apply_wd_fill(
            df,
            SensorColumn(column_name="WD_120m_fill:extrapolated", sensor_type="WindDirection", height=120.0, ...),
            [HeightReference(sensor=SensorColumn(..., column_name="WD_80m_avg", height=80.0), weight=1.0)],
            0.1
        )

        # Two references: interpolation
        apply_wd_fill(
            df,
            SensorColumn(column_name="WD_100m_fill:interpolated", sensor_type="WindDirection", height=100.0, ...),
            [
                HeightReference(sensor=SensorColumn(..., column_name="WD_80m_avg", height=80.0), weight=0.5),
                HeightReference(sensor=SensorColumn(..., column_name="WD_120m_avg", height=120.0), weight=0.5)
            ],
            0.1
        )
    """
    if len(references) == 0:
        raise ValueError("references list must contain at least 1 HeightReference")

    total_weight = sum(ref.weight for ref in references)

    # Build u expression: sum of -sin(radians(wd_at_target)) * weight
    u_expr = pl.sum_horizontal(
        [
            -(
                (pl.col(ref.sensor.column_name) + deg_diff_per_m * (target.height - ref.sensor.height)) % 360
            ).radians().sin() * (ref.weight / total_weight)
            for ref in references
        ],
        ignore_nulls=False
    )

    # Build v expression: sum of -cos(radians(wd_at_target)) * weight
    v_expr = pl.sum_horizontal(
        [
            -(
                (pl.col(ref.sensor.column_name) + deg_diff_per_m * (target.height - ref.sensor.height)) % 360
            ).radians().cos() * (ref.weight / total_weight)
            for ref in references
        ],
        ignore_nulls=False
    )

    # Convert back to degrees using arctan2 (returns radians) then convert to degrees
    result_expr = pl.arctan2(-u_expr, -v_expr).degrees() % 360

    return df.with_columns(result_expr.alias(target.column_name))[target.column_name]
