"""Wind temporal computation for the reporting domain.

LOGIC-PRESERVATION: Ported from assessment/subdomains/wind_temporal/services/_calculator.py.
All formulas and aggregation logic preserved exactly.
Pure functions only — no IO, no side effects.
"""

import polars as pl

from cleanmast.shared.timeseries import SensorColumn


def analyze_daily_pattern(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    air_density: float = 1.225,
) -> pl.DataFrame:
    """Analyze daily 24-hour wind pattern.

    Aggregates data by hour (0-23) to show typical daily wind patterns.

    Args:
        df: DataFrame with timestamp and wind speed columns.
        sensors: List of SensorColumn objects.
        air_density: Air density in kg/m³ for power calculations.

    Returns:
        DataFrame matching TemporalPatternSchema with 24 hourly data points
        per height.
    """
    ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]
    if not ws_sensors:
        return _create_empty_dataframe()

    return _process_daily_pattern(df, ws_sensors, air_density)


def analyze_monthly_pattern(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    air_density: float = 1.225,
) -> pl.DataFrame:
    """Analyze monthly wind pattern.

    Aggregates data by month (1-12) to show seasonal wind patterns.

    Args:
        df: DataFrame with timestamp and wind speed columns.
        sensors: List of SensorColumn objects.
        air_density: Air density in kg/m³ for power calculations.

    Returns:
        DataFrame matching TemporalPatternSchema with 12 monthly data points
        per height.
    """
    ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]
    if not ws_sensors:
        return _create_empty_dataframe()

    return _process_monthly_pattern(df, ws_sensors, air_density)


def analyze_monthly_daily_pattern(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    air_density: float = 1.225,
) -> pl.DataFrame:
    """Analyze combined monthly-daily wind pattern.

    Aggregates data by hour x month (24 hours x 12 months) for faceted grid
    visualizations showing how daily patterns vary by season.

    Args:
        df: DataFrame with timestamp and wind speed columns.
        sensors: List of SensorColumn objects.
        air_density: Air density in kg/m³ for power calculations.

    Returns:
        DataFrame matching TemporalPatternSchema with hourly x monthly data
        per height.
    """
    ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]
    if not ws_sensors:
        return _create_empty_dataframe()

    return _process_monthly_daily_pattern(df, ws_sensors, air_density)


def _process_daily_pattern(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    air_density: float,
) -> pl.DataFrame:
    """Process data into daily 24-hour pattern (long format)."""
    df_with_hour = df.with_columns(pl.col("timestamp").dt.hour().alias("hour"))

    rows: list[dict] = []

    for sensor in sensors:
        height = sensor.height
        ws_col = sensor.column_name

        if ws_col not in df.columns:
            continue

        hourly_stats = (
            df_with_hour.group_by("hour")
            .agg([
                pl.col(ws_col).mean().alias("mean_speed"),
                (0.5 * air_density * pl.col(ws_col).pow(3)).mean().alias("mean_power"),
            ])
            .sort("hour")
        )

        hour_timestamps = (
            df_with_hour.group_by("hour")
            .agg([pl.col("timestamp").first().alias("timestamp")])
            .sort("hour")
        )

        hourly_stats = hourly_stats.join(hour_timestamps, on="hour")

        for row in hourly_stats.iter_rows(named=True):
            rows.append({
                "timestamp": row["timestamp"],
                "hour": row["hour"],
                "month": row["timestamp"].month if hasattr(row["timestamp"], "month") else 1,
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": row["mean_speed"],
                "mean_power": row["mean_power"],
                "interpolation_marker": sensor.detect_interpolation_marker(),
            })

    return pl.DataFrame(rows) if rows else _create_empty_dataframe()


def _process_monthly_pattern(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    air_density: float,
) -> pl.DataFrame:
    """Process data into monthly pattern (long format)."""
    df_with_month = df.with_columns(pl.col("timestamp").dt.month().alias("month"))

    rows: list[dict] = []

    for sensor in sensors:
        height = sensor.height
        ws_col = sensor.column_name

        if ws_col not in df.columns:
            continue

        monthly_stats = (
            df_with_month.group_by("month")
            .agg([
                pl.col(ws_col).mean().alias("mean_speed"),
                (0.5 * air_density * pl.col(ws_col).pow(3)).mean().alias("mean_power"),
            ])
            .sort("month")
        )

        month_timestamps = (
            df_with_month.group_by("month")
            .agg([pl.col("timestamp").first().alias("timestamp")])
            .sort("month")
        )

        monthly_stats = monthly_stats.join(month_timestamps, on="month")

        for row in monthly_stats.iter_rows(named=True):
            rows.append({
                "timestamp": row["timestamp"],
                "hour": row["timestamp"].hour if hasattr(row["timestamp"], "hour") else 0,
                "month": row["month"],
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": row["mean_speed"],
                "mean_power": row["mean_power"],
                "interpolation_marker": sensor.detect_interpolation_marker(),
            })

    return pl.DataFrame(rows) if rows else _create_empty_dataframe()


def _process_monthly_daily_pattern(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    air_density: float,
) -> pl.DataFrame:
    """Process data into monthly-daily combined pattern (long format)."""
    df_with_time = df.with_columns([
        pl.col("timestamp").dt.hour().alias("hour"),
        pl.col("timestamp").dt.month().alias("month"),
    ])

    rows: list[dict] = []

    for sensor in sensors:
        height = sensor.height
        ws_col = sensor.column_name

        if ws_col not in df.columns:
            continue

        combined_stats = (
            df_with_time.group_by(["hour", "month"])
            .agg([
                pl.col(ws_col).mean().alias("mean_speed"),
                (0.5 * air_density * pl.col(ws_col).pow(3)).mean().alias("mean_power"),
                pl.col("timestamp").first().alias("timestamp"),
            ])
            .sort(["month", "hour"])
        )

        for row in combined_stats.iter_rows(named=True):
            rows.append({
                "timestamp": row["timestamp"],
                "hour": row["hour"],
                "month": row["month"],
                "wind_speed": None,
                "wind_power": None,
                "height": height,
                "mean_speed": row["mean_speed"],
                "mean_power": row["mean_power"],
                "interpolation_marker": sensor.detect_interpolation_marker(),
            })

    return pl.DataFrame(rows) if rows else _create_empty_dataframe()


def _create_empty_dataframe() -> pl.DataFrame:
    """Create an empty DataFrame with TemporalPatternSchema columns."""
    return pl.DataFrame({
        "timestamp": [],
        "hour": [],
        "month": [],
        "wind_speed": [],
        "wind_power": [],
        "height": [],
        "mean_speed": [],
        "mean_power": [],
        "interpolation_marker": [],
    })


__all__ = [
    "analyze_daily_pattern",
    "analyze_monthly_pattern",
    "analyze_monthly_daily_pattern",
]
