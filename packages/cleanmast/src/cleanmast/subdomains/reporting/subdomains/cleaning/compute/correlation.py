"""Pearson correlation matrix over selected time-series columns."""

import math

import numpy as np
import polars as pl

_KEY_COLUMN = "column"


def correlation_matrix(
    df: pl.DataFrame,
    columns: list[str],
) -> pl.DataFrame:
    """Pairwise Pearson correlation over the given columns.

    Each pair is correlated over the rows where BOTH columns are non-null
    (pairwise-complete). The result is a square frame keyed by ``column``
    with one additional column per entry; the diagonal is 1.0. Pairs with
    fewer than two complete rows or zero variance yield NaN.

    Args:
        df: DataFrame holding the columns.
        columns: Columns to correlate (e.g. one WS avg column per selected
            height); duplicates and unknown columns raise.

    Returns:
        DataFrame of shape (len(columns), len(columns) + 1).

    Raises:
        KeyError: If any column is missing from ``df``.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"columns not in DataFrame: {missing}")
    if len(set(columns)) != len(columns):
        raise ValueError(f"duplicate columns: {columns}")

    size = len(columns)
    values: list[list[float]] = []
    for row_col in columns:
        row: list[float] = []
        for col_col in columns:
            if row_col == col_col:
                row.append(1.0)
                continue
            pairs = df.select(row_col, col_col).drop_nulls()
            x = pairs.get_column(row_col).cast(pl.Float64).to_numpy()
            y = pairs.get_column(col_col).cast(pl.Float64).to_numpy()
            if len(x) < 2 or float(np.ptp(x)) == 0.0 or float(np.ptp(y)) == 0.0:
                row.append(math.nan)
                continue
            row.append(float(np.corrcoef(x, y)[0, 1]))
        values.append(row)

    series: list[pl.Series] = [
        pl.Series(_KEY_COLUMN, list(columns), dtype=pl.String),
    ]
    for j, col_name in enumerate(columns):
        series.append(
            pl.Series(
                col_name,
                [values[i][j] for i in range(size)],
                dtype=pl.Float64,
            )
        )
    return pl.DataFrame(series)
