"""16-sector binning for tower-shading statistics."""

import polars as pl

from cleanmast.subdomains.reporting.model.sectors import find_sector

SECTOR_COLUMN = "sector"


def assign_sector(df: pl.DataFrame, wd_column: str) -> pl.DataFrame:
    """Add a 1-indexed 16-sector column derived from a wind direction column.

    Sector semantics come from the shared helper
    (``reporting/model/sectors.py``): 16 sectors clockwise from N, 22.5°
    wide. Null directions yield a null sector.
    """
    return df.with_columns(
        pl.col(wd_column)
        .map_elements(find_sector, return_dtype=pl.Int64, skip_nulls=True)
        .alias(SECTOR_COLUMN)
    )


def sector_ws_stats(
    df: pl.DataFrame,
    wd_column: str,
    ws_column: str,
) -> pl.DataFrame:
    """Per-sector wind speed statistics for tower-shading analysis.

    Rows where either the direction or the speed is null are excluded.
    Sectors without any observation are omitted (not zero-filled).

    Args:
        df: Time-series frame with direction and speed columns.
        wd_column: Wind direction column (degrees).
        ws_column: Wind speed column.

    Returns:
        DataFrame with columns ``sector`` (1–16), ``data_points``, and
        ``mean_ws``, sorted by sector.
    """
    return (
        assign_sector(df, wd_column)
        .drop_nulls(subset=[wd_column, ws_column])
        .group_by(SECTOR_COLUMN)
        .agg(
            pl.len().alias("data_points"),
            pl.col(ws_column).mean().alias("mean_ws"),
        )
        .sort(SECTOR_COLUMN)
    )
