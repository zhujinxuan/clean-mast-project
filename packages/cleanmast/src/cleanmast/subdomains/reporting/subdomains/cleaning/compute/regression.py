"""Ordinary least squares regression over paired time-series columns."""

from dataclasses import dataclass

import numpy as np
import polars as pl


@dataclass(frozen=True)
class RegressionResult:
    """OLS fit of y on x.

    Attributes:
        slope: Fitted slope.
        intercept: Fitted intercept.
        r: Pearson correlation coefficient (sign matches the slope);
            0.0 when y has zero variance (r undefined).
        rmse: Root mean squared error of the fit.
        n: Number of complete (non-null) pairs used.
    """

    slope: float
    intercept: float
    r: float
    rmse: float
    n: int


def linear_regression(
    df: pl.DataFrame,
    x_column: str,
    y_column: str,
) -> RegressionResult:
    """Fit y = slope * x + intercept over rows where both columns are non-null.

    Args:
        df: DataFrame holding both columns.
        x_column: Predictor column (e.g. reference sensor).
        y_column: Response column (e.g. target sensor).

    Returns:
        RegressionResult with slope, intercept, r, rmse, and pair count.

    Raises:
        ValueError: If fewer than two complete pairs exist or x has zero
            variance (the fit is undefined).
    """
    pairs = (
        df.select(
            pl.col(x_column).cast(pl.Float64).alias("x"),
            pl.col(y_column).cast(pl.Float64).alias("y"),
        )
        .drop_nulls()
    )
    x = pairs.get_column("x").to_numpy()
    y = pairs.get_column("y").to_numpy()
    if len(x) < 2:
        raise ValueError(
            f"linear_regression requires at least 2 complete pairs, got {len(x)} "
            f"(x='{x_column}', y='{y_column}')"
        )
    if float(np.ptp(x)) == 0.0:
        raise ValueError(
            f"linear_regression x column '{x_column}' has zero variance"
        )

    slope, intercept = np.polyfit(x, y, 1)
    residuals = y - (float(slope) * x + float(intercept))
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r = float(np.sqrt(1.0 - ss_res / ss_tot)) if ss_tot > 0 else 0.0
    if slope < 0:
        r = -r
    rmse = float(np.sqrt(ss_res / len(x)))
    return RegressionResult(
        slope=float(slope),
        intercept=float(intercept),
        r=r,
        rmse=rmse,
        n=len(x),
    )
