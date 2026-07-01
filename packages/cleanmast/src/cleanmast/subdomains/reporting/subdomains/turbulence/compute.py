"""Turbulence intensity computation for the reporting domain.

LOGIC-PRESERVATION: Ported from assessment/services/_calculator.py.
All formulas, constants, and algorithms preserved exactly.
Key change: stateful TurbulenceCalculator class → pure functions.
No IO, no side effects, no mutable global state.
"""

import numpy as np
import polars as pl

from cleanmast.shared.timeseries import SensorColumn

# ── Constants ────────────────────────────────────────────────────────────────

# Minimum number of samples required for analysis
MIN_SAMPLES: int = 10

# Z-score for P90 representative TI (90th percentile)
TI_REP_Z: float = 1.28

# Minimum wind speed for TI calculation (avoid division by small numbers)
MIN_WIND_SPEED: float = 1.0

# Number of direction sectors (16: N, NNE, NE, ..., NNW)
NUM_SECTORS: int = 16

# Sector width in degrees
SECTOR_WIDTH: float = 22.5

# IEC reference turbulence intensity categories
IEC_CATEGORIES: dict[str, float] = {
    "A+": 0.18,
    "A": 0.16,
    "B": 0.14,
    "C": 0.12,
}

# Sector names for 16-sector wind rose
SECTOR_NAMES: list[str] = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


# ── Height Filter Utility ────────────────────────────────────────────────────


def _select_interested_heights(
    heights: list[float],
    min_height: float = 120.0,
    max_height: float = 160.0,
    min_count: int = 2,
) -> list[float]:
    """Select heights within the target range, falling back to top heights.

    Returns all heights where ``min_height <= h <= max_height``, sorted
    ascending. If fewer than ``min_count`` heights fall within the range,
    returns the ``min_count`` highest heights from the full set.
    """
    filtered = [h for h in heights if min_height <= h <= max_height]
    filtered.sort()

    if len(filtered) >= min_count:
        return filtered

    sorted_heights = sorted(heights, reverse=True)
    fallback = sorted_heights[:min_count]
    fallback.sort()
    return fallback


# ── Core TI Calculation ──────────────────────────────────────────────────────


def calculate_ti_series(
    wind_speeds: list[float],
    rolling_window: int = 600,
) -> list[float | None]:
    """Calculate turbulence intensity time series using rolling window.

    TI = σ / max(μ, MIN_WIND_SPEED) over a rolling window.
    Edge values where the window is incomplete are set to None.
    Returns all None if input is shorter than rolling_window.
    """
    if len(wind_speeds) < rolling_window:
        return [None] * len(wind_speeds)

    ws_array = np.array(wind_speeds)
    kernel = np.ones(rolling_window) / rolling_window
    mean_values = np.convolve(ws_array, kernel, mode="same")

    mean_sq_values = np.convolve(ws_array**2, kernel, mode="same")
    variance = mean_sq_values - mean_values**2
    variance = np.maximum(variance, 0)
    std_values = np.sqrt(variance)

    ti_values = std_values / np.maximum(mean_values, MIN_WIND_SPEED)

    half_window = rolling_window // 2
    ti_list: list[float | None] = ti_values.tolist()
    for i in range(half_window):
        ti_list[i] = None
        ti_list[-(i + 1)] = None

    return ti_list


def calculate_representative_ti(
    ti_values: list[float | None],
) -> float | None:
    """Calculate representative turbulence intensity (P90).

    TI_rep = mean(TI) + TI_REP_Z * std(TI)
    Returns None if fewer than MIN_SAMPLES valid values.
    """
    valid_ti = [ti for ti in ti_values if ti is not None]

    if len(valid_ti) < MIN_SAMPLES:
        return None

    return float(np.mean(valid_ti) + TI_REP_Z * np.std(valid_ti, ddof=1))


def compute_iec_ti(wind_speed: float, i_ref: float) -> float | None:
    """Compute IEC reference turbulence intensity.

    TI_IEC = I_ref * (0.75 + 5.6/V)
    Returns None for wind_speed ≤ 0.
    """
    if wind_speed <= 0:
        return None

    return i_ref * (0.75 + 5.6 / wind_speed)


def classify_iec_category(
    representative_ti: float | None,
    wind_speed: float,
) -> str:
    """Classify IEC turbulence category using strict > thresholds.

    Compares representative TI against IEC reference TI for categories
    A, B, C at the given wind speed. Defaults to "C" for None or zero wind.
    """
    if representative_ti is None or wind_speed <= 0:
        return "C"

    ti_a = compute_iec_ti(wind_speed, IEC_CATEGORIES["A"])
    ti_b = compute_iec_ti(wind_speed, IEC_CATEGORIES["B"])
    ti_c = compute_iec_ti(wind_speed, IEC_CATEGORIES["C"])

    if ti_a is not None and representative_ti > ti_a:
        return "A+"
    if ti_b is not None and representative_ti > ti_b:
        return "A"
    if ti_c is not None and representative_ti > ti_c:
        return "B"
    return "C"


# ── Sensor Matching ──────────────────────────────────────────────────────────


def _find_matching_sd_sensor(
    avg_sensor: SensorColumn,
    all_sensors: list[SensorColumn],
) -> SensorColumn | None:
    """Find the SD sensor at the same height as the avg sensor."""
    height = avg_sensor.height
    sd_sensors = [
        s for s in all_sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "sd"
    ]

    if not sd_sensors:
        return None

    closest = min(sd_sensors, key=lambda s: abs(s.height - height))
    if abs(closest.height - height) <= 5.0:
        return closest
    return None


def _find_matching_direction_sensor(
    height: float,
    wd_sensors: list[SensorColumn],
) -> SensorColumn | None:
    """Find the direction sensor closest to the given height."""
    if not wd_sensors:
        return None

    closest = min(wd_sensors, key=lambda s: abs(s.height - height))
    if abs(closest.height - height) <= 20.0:
        return closest
    return None


# ── Wind Speed Bin Analysis ──────────────────────────────────────────────────


def _create_empty_turbulence_dataframe() -> pl.DataFrame:
    """Create an empty DataFrame with TurbulenceSchema columns."""
    return pl.DataFrame({
        "wind_speed_bin": pl.Series([], dtype=pl.Int64),
        "height": pl.Series([], dtype=pl.Float64),
        "interpolation_marker": pl.Series([], dtype=pl.String),
        "mean_ti": pl.Series([], dtype=pl.Float64),
        "std_ti": pl.Series([], dtype=pl.Float64),
        "representative_ti": pl.Series([], dtype=pl.Float64),
        "iec_category": pl.Series([], dtype=pl.String),
        "count": pl.Series([], dtype=pl.Int64),
    })


def _create_empty_sector_dataframe() -> pl.DataFrame:
    """Create an empty DataFrame with TurbulenceSectorSchema columns."""
    return pl.DataFrame({
        "sector": pl.Series([], dtype=pl.Int64),
        "sector_name": pl.Series([], dtype=pl.String),
        "height": pl.Series([], dtype=pl.Float64),
        "interpolation_marker": pl.Series([], dtype=pl.String),
        "mean_ti": pl.Series([], dtype=pl.Float64),
        "representative_ti": pl.Series([], dtype=pl.Float64),
        "iec_category": pl.Series([], dtype=pl.String),
    })


def analyze_by_wind_speed(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
) -> pl.DataFrame:
    """Analyze turbulence intensity by wind speed bins (long format).

    For each height, calculate mean TI, std TI, representative TI (P90),
    and IEC category for wind speed bins using paired avg and sd sensors.

    Args:
        df: DataFrame with timestamp and sensor columns.
        sensors: List of SensorColumn objects.

    Returns:
        DataFrame with columns: wind_speed_bin, height, interpolation_marker,
        mean_ti, std_ti, representative_ti, iec_category, count.
    """
    ws_avg_sensors = [
        s for s in sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]

    if not ws_avg_sensors:
        return _create_empty_turbulence_dataframe()

    return _process_wind_speed_analysis(df, ws_avg_sensors, sensors)


def _process_wind_speed_analysis(
    df: pl.DataFrame,
    avg_sensors: list[SensorColumn],
    all_sensors: list[SensorColumn],
) -> pl.DataFrame:
    """Process data into TI by wind speed bins (long format)."""
    rows: list[dict] = []

    for sensor in avg_sensors:
        height = sensor.height
        avg_col = sensor.column_name

        sd_sensor = _find_matching_sd_sensor(sensor, all_sensors)
        if sd_sensor is None:
            continue
        sd_col = sd_sensor.column_name

        if avg_col not in df.columns or sd_col not in df.columns:
            continue

        interpolation_marker = sensor.detect_interpolation_marker()

        valid_df = df.filter(
            (pl.col(avg_col).is_not_null())
            & (pl.col(avg_col) > 0)
            & (pl.col(sd_col).is_not_null())
            & (pl.col(sd_col) > 0)
        )

        if valid_df.is_empty():
            continue

        # TI for each row: TI = sd / max(avg, 1.0), capped at 1.0
        ti_expr = (
            pl.col(sd_col)
            / pl.max_horizontal(pl.col(avg_col), pl.lit(1.0))
        ).clip(upper_bound=1.0)

        df_with_ti = valid_df.with_columns([
            ti_expr.alias("ti"),
            pl.col(avg_col).floor().cast(pl.Int64).alias("ws_bin"),
        ])

        bin_stats = (
            df_with_ti.group_by("ws_bin")
            .agg([
                pl.col("ti").mean().alias("mean_ti"),
                pl.col("ti").std().alias("std_ti"),
                pl.col("ti").count().alias("count"),
            ])
            .sort("ws_bin")
        )

        for row in bin_stats.iter_rows(named=True):
            ws_bin = row["ws_bin"]
            mean_ti = row["mean_ti"]
            std_ti = row["std_ti"] if row["std_ti"] is not None else 0.0
            count = row["count"]

            if count < MIN_SAMPLES:
                continue

            rep_ti = mean_ti + TI_REP_Z * std_ti
            iec_category = classify_iec_category(rep_ti, float(ws_bin) + 0.5)

            rows.append({
                "wind_speed_bin": ws_bin,
                "height": height,
                "interpolation_marker": interpolation_marker,
                "mean_ti": mean_ti,
                "std_ti": std_ti,
                "representative_ti": rep_ti,
                "iec_category": iec_category,
                "count": count,
            })

    return pl.DataFrame(rows) if rows else _create_empty_turbulence_dataframe()


# ── Sector Analysis ──────────────────────────────────────────────────────────


def analyze_by_sector(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
) -> pl.DataFrame:
    """Analyze turbulence intensity by 16 direction sectors (long format).

    For each height, calculate mean TI and representative TI grouped by
    16 direction sectors using paired avg, sd, and direction sensors.

    Args:
        df: DataFrame with timestamp and sensor columns.
        sensors: List of SensorColumn objects.

    Returns:
        DataFrame with columns: sector, sector_name, height,
        interpolation_marker, mean_ti, representative_ti, iec_category.
    """
    ws_avg_sensors = [
        s for s in sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]
    wd_avg_sensors = [
        s for s in sensors
        if s.sensor_type == "WindDirection" and s.stat_type == "avg"
    ]

    if not ws_avg_sensors or not wd_avg_sensors:
        return _create_empty_sector_dataframe()

    return _process_sector_analysis(df, ws_avg_sensors, wd_avg_sensors, sensors)


def _process_sector_analysis(
    df: pl.DataFrame,
    ws_sensors: list[SensorColumn],
    wd_sensors: list[SensorColumn],
    all_sensors: list[SensorColumn],
) -> pl.DataFrame:
    """Process data into TI by direction sectors (long format)."""
    rows: list[dict] = []

    for ws_sensor in ws_sensors:
        height = ws_sensor.height
        avg_col = ws_sensor.column_name

        sd_sensor = _find_matching_sd_sensor(ws_sensor, all_sensors)
        if sd_sensor is None:
            continue
        sd_col = sd_sensor.column_name

        wd_sensor = _find_matching_direction_sensor(height, wd_sensors)
        if wd_sensor is None:
            continue
        wd_col = wd_sensor.column_name

        if (
            avg_col not in df.columns
            or sd_col not in df.columns
            or wd_col not in df.columns
        ):
            continue

        interpolation_marker = ws_sensor.detect_interpolation_marker()

        valid_df = df.filter(
            (pl.col(avg_col).is_not_null())
            & (pl.col(avg_col) > 0)
            & (pl.col(sd_col).is_not_null())
            & (pl.col(sd_col) > 0)
            & (pl.col(wd_col).is_not_null())
        )

        if valid_df.is_empty():
            continue

        ti_expr = (
            pl.col(sd_col)
            / pl.max_horizontal(pl.col(avg_col), pl.lit(1.0))
        ).clip(upper_bound=1.0)

        sector_expr = (
            (pl.col(wd_col) / SECTOR_WIDTH).floor() % NUM_SECTORS
        ).cast(pl.Int64)

        df_with_ti = valid_df.with_columns([
            ti_expr.alias("ti"),
            sector_expr.alias("sector"),
        ])

        sector_stats = (
            df_with_ti.group_by("sector")
            .agg([
                pl.col("ti").mean().alias("mean_ti"),
                pl.col("ti").std().alias("std_ti"),
                pl.col("ti").count().alias("count"),
                pl.col(avg_col).mean().alias("mean_ws"),
            ])
            .sort("sector")
        )

        for row in sector_stats.iter_rows(named=True):
            sector = int(row["sector"])
            mean_ti = row["mean_ti"]
            std_ti = row["std_ti"] if row["std_ti"] is not None else 0.0
            count = row["count"]

            if count < MIN_SAMPLES:
                continue

            rep_ti = mean_ti + TI_REP_Z * std_ti
            iec_category = classify_iec_category(rep_ti, row["mean_ws"])

            rows.append({
                "sector": sector,
                "sector_name": SECTOR_NAMES[sector],
                "height": height,
                "interpolation_marker": interpolation_marker,
                "mean_ti": mean_ti,
                "representative_ti": rep_ti,
                "iec_category": iec_category,
            })

    return pl.DataFrame(rows) if rows else _create_empty_sector_dataframe()
