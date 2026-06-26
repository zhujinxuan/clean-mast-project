"""Wind rose computation for the reporting domain.

LOGIC-PRESERVATION: Ported from assessment/subdomains/wind_rose/services/_calculator.py.
All formulas, constants, and algorithms preserved exactly.
Pure functions only — no IO, no side effects.

Key improvement: eliminates `rows: list[dict]` pattern by building Polars
DataFrames per sensor and concatenating, instead of accumulating untyped dicts.
"""

import polars as pl

from cleanmast.shared.timeseries import TimeSeriesData

# Sector constants (named, not hardcoded 22.5/16)
SECTOR_COUNT = 16
SECTOR_WIDTH = 360.0 / SECTOR_COUNT  # degrees per sector

SECTOR_NAMES = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]

# Interpolation marker regex pattern (matches *_fill:type suffix)
_FILL_TYPE_PATTERN = r"_fill:(\w+)$"

_FILL_TYPE_LABELS: dict[str, str] = {
    "extrapolated": "外推",
    "interpolated": "内插",
}


def _detect_interpolation_marker(column_name: str) -> str:
    """Detect fill type marker from column name.

    Returns Chinese label ("外推"/"内插") or empty string if no marker.
    """
    import re
    if match := re.search(_FILL_TYPE_PATTERN, column_name, re.IGNORECASE):
        fill_type = match.group(1).lower()
        return _FILL_TYPE_LABELS.get(fill_type, "")
    return ""


def _process_sensor_data(
    df: pl.DataFrame,
    ws_col: str,
    wd_col: str,
    height: float,
    marker: str,
    air_density: float,
) -> pl.DataFrame:
    """Process a single sensor's data into wind rose statistics.

    Eliminates the `rows: list[dict]` pattern by building a Polars DataFrame
    directly from grouped statistics.

    Args:
        df: Full time series DataFrame with timestamp, WS, WD columns
        ws_col: Wind speed column name
        wd_col: Wind direction column name
        height: Sensor height in meters
        marker: Interpolation marker string
        air_density: Air density in kg/m³

    Returns:
        Polars DataFrame with columns: month, month_name, sector, sector_name,
        height, interpolation_marker, frequency, wind_power_density, total_power
    """
    # Filter out null wind direction values
    valid_df = df.filter(pl.col(wd_col).is_not_null())

    # Calculate sector (0-15) from wind direction and extract month
    df_with_sector_month = valid_df.with_columns(
        ((pl.col(wd_col) / SECTOR_WIDTH).round().cast(pl.Int64) % SECTOR_COUNT).alias("sector"),
        pl.col("timestamp").dt.month().alias("month"),
    )

    # Group by month and sector, calculate statistics
    month_sector_stats = df_with_sector_month.group_by(["month", "sector"]).agg([
        pl.len().alias("count"),
        (0.5 * air_density * pl.col(ws_col).pow(3)).mean().alias("wind_power_density"),
        (0.5 * air_density * pl.col(ws_col).pow(3)).sum().alias("total_power"),
    ]).sort(["month", "sector"])

    # Calculate frequency per month based on valid rows
    month_counts = df_with_sector_month.group_by("month").agg(
        pl.len().alias("month_total")
    )
    month_sector_stats = month_sector_stats.join(month_counts, on="month")

    # Build the result DataFrame directly from Polars operations
    result = month_sector_stats.with_columns([
        pl.lit(height).alias("height"),
        pl.lit(marker).alias("interpolation_marker"),
        (pl.col("count") / pl.col("month_total")).alias("frequency"),
        (pl.col("month").cast(pl.Utf8) + pl.lit("月")).alias("month_name"),
        pl.col("sector").map_elements(
            lambda s: SECTOR_NAMES[int(s)], return_dtype=pl.Utf8
        ).alias("sector_name"),
    ]).select([
        "month", "month_name", "sector", "sector_name",
        "height", "interpolation_marker", "frequency",
        "wind_power_density", "total_power",
    ])

    return result


def _compute_energy_frequency(df: pl.DataFrame) -> pl.DataFrame:
    """Compute energy_frequency from total_power grouped by month and height.

    energy_frequency = sector_total_power / month_height_total_power
    Zero-division guard: returns 0.0 when denominator is 0 or null.
    """
    total_power = pl.col("total_power").sum().over(["month", "height"])
    return df.with_columns(
        pl.when(total_power.is_null() | (total_power == 0))
        .then(0.0)
        .otherwise(pl.col("total_power") / total_power)
        .alias("energy_frequency")
    ).drop("total_power")


def calculate_wind_rose(
    time_series: TimeSeriesData,
    air_density: float,
) -> pl.DataFrame:
    """Calculate wind rose statistics from time series data.

    Pure function — no IO, no side effects. Replaces the stateful
    WindRoseCalculator class from assessment.

    Args:
        time_series: TimeSeriesData containing DataFrame and sensor metadata
        air_density: Air density in kg/m³ for power density calculation

    Returns:
        Polars DataFrame with WindRoseSchema columns: month, month_name,
        sector, sector_name, height, interpolation_marker, frequency,
        wind_power_density, energy_frequency
    """
    df = time_series.df
    sensors = time_series.sensors

    # Filter sensors by type and stat_type
    ws_avg_sensors = [
        s for s in sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]
    wd_avg_sensors = [
        s for s in sensors
        if s.sensor_type == "WindDirection" and s.stat_type == "avg"
    ]

    # Build height -> WD column lookup
    wd_col_map: dict[float, str] = {
        s.height: s.column_name for s in wd_avg_sensors
    }

    # Process each wind speed sensor — collect Polars DataFrames, not list[dict]
    sensor_dfs: list[pl.DataFrame] = []
    for sensor in ws_avg_sensors:
        height = sensor.height
        ws_col = sensor.column_name

        wd_col = wd_col_map.get(height)
        if wd_col is None:
            continue

        marker = sensor.detect_interpolation_marker()

        sensor_df = _process_sensor_data(
            df, ws_col, wd_col, height, marker, air_density
        )
        sensor_dfs.append(sensor_df)

    # Return empty result if no sensor data was processed
    if not sensor_dfs:
        return pl.DataFrame(
            schema={
                "month": pl.Int64, "month_name": pl.Utf8,
                "sector": pl.Int64, "sector_name": pl.Utf8,
                "height": pl.Float64, "interpolation_marker": pl.Utf8,
                "frequency": pl.Float64, "wind_power_density": pl.Float64,
                "energy_frequency": pl.Float64,
            }
        )

    # Concatenate all sensor DataFrames (typed, not untyped list[dict])
    result_df = pl.concat(sensor_dfs)

    # Compute energy_frequency from total_power
    result_df = _compute_energy_frequency(result_df)

    return result_df
