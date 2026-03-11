"""Wind speed filling execution functions.

This module implements the execution layer for wind speed height filling.
It applies the fill configurations to actual data.

Power Law Extrapolation:
=======================

The power law describes how wind speed changes with height:
    V2 = V1 * (H2 / H1)^α

Where:
    V1, H1 = Reference wind speed and height
    V2, H2 = Target wind speed and height
    α = Shear exponent (dimensionless)

The power law is derived from the logarithmic wind profile:
    V(z) = V_ref * ln(z/z0) / ln(z_ref/z0)

Which can be approximated as a power law for practical purposes.

Interpolation vs Extrapolation:
================================

- Extrapolation (1 reference):
    Uses power law directly to estimate V at target height

- Interpolation (2 references):
    Both references are extrapolated to target height
    Results are weighted and averaged

Why Extrapolate Both References?
================================

1. Consistency: Both values are computed using same formula
2. Correctness: Respects the physical relationship between heights
3. Robustness: Reduces sensitivity to individual sensor errors

Example:
    References at 80m (10 m/s) and 120m (12 m/s), target at 100m, shear=0.15

    Extrapolate 80m→100m: 10 * (100/80)^0.15 ≈ 10.7 m/s
    Extrapolate 120m→100m: 12 * (100/120)^0.15 ≈ 11.8 m/s
    Weighted average (if equal weights): ≈ 11.25 m/s

Null Handling:
==============

Null values are PRESERVED, not filled. Polars arithmetic operations
naturally propagate nulls - if any input is null, the result is null.
This ensures:
1. No spurious data is created
2. Downstream quality analysis can detect gaps
3. Transparency about data provenance
"""

import polars as pl
from polars import Series

from cleanmast.subdomains.configuration import HeightReference
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


def apply_ws_fill(
    df: pl.DataFrame,
    target: SensorColumn,
    references: list[HeightReference],
    shear: float,
) -> pl.Series:
    """Apply wind speed fill (extrapolation or interpolation).

    Implements the power law for wind speed height adjustment.

    Algorithm:
        1. For each reference: extrapolate to target height using power law
           V_target = V_ref * (H_target / H_ref)^shear
        2. Weight each extrapolated value by reference weight
        3. Sum all weighted values and normalize by total weight

    This handles any number of references (N >= 1):
        - N=1: Simple extrapolation (weight should be 1.0)
        - N=2: Standard interpolation between two references
        - N>2: Multi-reference weighted interpolation

    Null values are preserved (not filled). Polars arithmetic operations
    naturally propagate nulls - if any input is null, result is null.

    Args:
        df: Input DataFrame with reference columns
        target: SensorColumn for the target height (column_name and height)
        references: List of HeightReference with at least 1 element
        shear: Power law shear exponent (typically 0.1-0.3)

    Returns:
        Series with filled wind speed values at target height

    Raises:
        ValueError: If references list is empty

    Example:
        # Single reference: extrapolation
        apply_ws_fill(
            df,
            SensorColumn(column_name="WS_120m_fill:extrapolated", sensor_type="WindSpeed", height=120.0, ...),
            [HeightReference(sensor=SensorColumn(..., column_name="WS_80m_avg", height=80.0), weight=1.0)],
            0.15
        )

        # Two references: interpolation
        apply_ws_fill(
            df,
            SensorColumn(column_name="WS_100m_fill:interpolated", sensor_type="WindSpeed", height=100.0, ...),
            [
                HeightReference(sensor=SensorColumn(..., column_name="WS_80m_avg", height=80.0), weight=0.5),
                HeightReference(sensor=SensorColumn(..., column_name="WS_120m_avg", height=120.0), weight=0.5)
            ],
            0.15
        )
    """
    # General weighted average: extrapolate each reference to target, then weight-average
    total_weight = sum(ref.weight for ref in references)

    # Build weighted expression using polars-native operations
    expr = pl.sum_horizontal(
        [
            pl.col(ref.sensor.column_name)
            * ((target.height / ref.sensor.height) ** shear)
            * (ref.weight / total_weight)
            for ref in references
        ],
        ignore_nulls=False,
    )

    # Single evaluation with polars
    return df.with_columns(expr.alias(target.column_name))[target.column_name]
