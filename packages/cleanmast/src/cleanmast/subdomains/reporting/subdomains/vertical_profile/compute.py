# LOGIC-PRESERVATION: ported from assessment/subdomains/vertical_profile/services/_calculator.py.
# Verified: same formulas, same constants, same library calls, same edge case handling.
# Changes: extracted stateful VerticalProfileAnalyzer into module-level pure functions
# and a frozen constants dataclass for backward-compatible test access.

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

import numpy as np
import polars as pl
from scipy.stats import linregress

from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.model.analysis_metadata import AnalysisMetadata
from cleanmast.subdomains.reporting.model.analysis_result import AnalysisResult
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.schemas import (
    VerticalProfileSchema,
    WindShearAggregateProfileSchema,
)

if TYPE_CHECKING:
    from cleanmast.shared.timeseries import SensorColumn

MIN_HEIGHTS_FOR_FIT = 2
MIN_SAMPLES = 10
MIN_R_SQUARED = 0.5
DEFAULT_REF_HEIGHT = 10.0


@dataclass(frozen=True)
class VerticalProfileConstants:
    MIN_HEIGHTS_FOR_FIT: int = 2
    MIN_SAMPLES: int = 10
    MIN_R_SQUARED: float = 0.5
    DEFAULT_REF_HEIGHT: float = 10.0


def get_time_range(df: pl.DataFrame) -> str:
    if "timestamp" not in df.columns or df.is_empty():
        return "Unknown"

    timestamps = df["timestamp"]
    start = timestamps.min()
    end = timestamps.max()

    if start is None or end is None:
        return "Unknown"

    start_str = f"{start}"[:10]
    end_str = f"{end}"[:10]

    return f"{start_str} to {end_str}"


def fit_power_law(
    heights: list[float],
    wind_speeds: list[float],
) -> tuple[float | None, float | None]:
    if len(heights) < MIN_HEIGHTS_FOR_FIT:
        return None, None

    if len(heights) != len(wind_speeds):
        return None, None

    valid_pairs = [
        (h, v) for h, v in zip(heights, wind_speeds) if h > 0 and v > 0
    ]

    if len(valid_pairs) < MIN_HEIGHTS_FOR_FIT:
        return None, None

    valid_heights = [p[0] for p in valid_pairs]
    valid_speeds = [p[1] for p in valid_pairs]

    log_h = np.log(valid_heights)
    log_v = np.log(valid_speeds)

    result = cast(tuple[float, float, float, float, float], linregress(log_h, log_v))

    alpha = result[0]
    r_squared = result[2] ** 2

    if not np.isfinite(alpha) or not np.isfinite(r_squared):
        return None, None

    return float(alpha), float(r_squared)


def calculate_wind_shear(
    height1: float,
    speed1: float,
    height2: float,
    speed2: float,
) -> float | None:
    if height1 <= 0 or height2 <= 0:
        return None

    if speed1 <= 0 or speed2 <= 0:
        return None

    if height1 == height2:
        return None

    try:
        alpha = np.log(speed2 / speed1) / np.log(height2 / height1)

        if not np.isfinite(alpha):
            return None

        return float(alpha)
    except (ValueError, ZeroDivisionError):
        return None


def _create_empty_profile_dataframe() -> pl.DataFrame:
    return pl.DataFrame({
        "height": pl.Series([], dtype=pl.Float64),
        "interpolation_marker": pl.Series([], dtype=pl.String),
        "wind_speed_mean": pl.Series([], dtype=pl.Float64),
        "wind_speed_std": pl.Series([], dtype=pl.Float64),
        "alpha": pl.Series([], dtype=pl.Float64),
        "r_squared": pl.Series([], dtype=pl.Float64),
    })


def _create_empty_shear_dataframe() -> pl.DataFrame:
    return pl.DataFrame({
        "from_height": pl.Series([], dtype=pl.Float64),
        "to_height": pl.Series([], dtype=pl.Float64),
        "from_v": pl.Series([], dtype=pl.Float64),
        "to_v": pl.Series([], dtype=pl.Float64),
        "alpha": pl.Series([], dtype=pl.Float64),
    })


def _process_vertical_profile(
    df: pl.DataFrame,
    sensors: list["SensorColumn"],
) -> pl.DataFrame:
    height_stats: list[tuple[float, float, float, str]] = []

    for sensor in sensors:
        height = sensor.height
        ws_col = sensor.column_name

        if ws_col not in df.columns:
            continue

        interpolation_marker = sensor.detect_interpolation_marker()

        ws_series = df.filter(
            (pl.col(ws_col).is_not_null()) & (pl.col(ws_col) > 0)
        )[ws_col]
        wind_speeds = ws_series.to_list()

        if len(wind_speeds) < MIN_SAMPLES:
            continue

        mean_speed = float(np.mean(wind_speeds))
        std_speed = float(np.std(wind_speeds))

        height_stats.append((height, mean_speed, std_speed, interpolation_marker))

    height_stats.sort(key=lambda x: x[0])

    alpha_fit: float | None = None
    r_squared_fit: float | None = None

    if len(height_stats) >= MIN_HEIGHTS_FOR_FIT:
        heights_for_fit = [h for h, _, _, _ in height_stats]
        speeds_for_fit = [s for _, s, _, _ in height_stats]
        alpha_fit, r_squared_fit = fit_power_law(
            heights_for_fit, speeds_for_fit
        )

    rows: list[dict[str, object]] = []
    for height, mean_speed, std_speed, marker in height_stats:
        rows.append({
            "height": height,
            "interpolation_marker": marker,
            "wind_speed_mean": mean_speed,
            "wind_speed_std": std_speed,
            "alpha": alpha_fit,
            "r_squared": r_squared_fit,
        })

    return pl.DataFrame(rows) if rows else _create_empty_profile_dataframe()


def analyze_vertical_profile(
    input: SingleMastAnalysisInput,
) -> AnalysisResult[VerticalProfileSchema]:
    df = input.time_series.df
    sensors = input.time_series.sensors

    ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

    if not ws_sensors:
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=get_time_range(df),
            created_at=datetime.now(),
        )
        return AnalysisResult.create(
            schema=VerticalProfileSchema,
            data=_create_empty_profile_dataframe(),
            metadata=metadata,
        )

    result_df = _process_vertical_profile(df, ws_sensors)

    metadata = AnalysisMetadata(
        mast_name=input.mast_name,
        time_range=get_time_range(df),
        created_at=datetime.now(),
    )

    return AnalysisResult.create(
        schema=VerticalProfileSchema,
        data=result_df,
        metadata=metadata,
    )


def _process_shear_profile(
    df: pl.DataFrame,
    sensors: list["SensorColumn"],
) -> pl.DataFrame:
    # 1. Compute mean wind speed at each valid height
    valid_sensors: list[tuple[float, str, float]] = []  # (height, col, mean_speed)
    for sensor in sensors:
        ws_col = sensor.column_name
        if ws_col not in df.columns:
            continue
        valid_count = df.filter(
            (pl.col(ws_col).is_not_null()) & (pl.col(ws_col) > 0)
        ).height
        if valid_count is not None and valid_count >= MIN_SAMPLES:
            ws_series = df.filter(
                (pl.col(ws_col).is_not_null()) & (pl.col(ws_col) > 0)
            )[ws_col]
            mean_speed = float(np.mean(ws_series.to_numpy()))
            valid_sensors.append((sensor.height, ws_col, mean_speed))

    valid_sensors.sort(key=lambda x: x[0])

    # 2. For each height pair, compute alpha from mean speeds
    rows: list[dict[str, object]] = []
    for i in range(len(valid_sensors)):
        for j in range(i + 1, len(valid_sensors)):
            h1, col1, v1 = valid_sensors[i]
            h2, col2, v2 = valid_sensors[j]

            if v1 > 0 and v2 > 0 and h1 > 0 and h2 > 0:
                alpha = float(np.log(v2 / v1) / np.log(h2 / h1))
                rows.append({
                    "from_height": h1,
                    "to_height": h2,
                    "from_v": v1,
                    "to_v": v2,
                    "alpha": alpha,
                })

    return pl.DataFrame(rows) if rows else _create_empty_shear_dataframe()


def calculate_wind_shear_profile(
    input: SingleMastAnalysisInput,
) -> AnalysisResult[WindShearAggregateProfileSchema]:
    df = input.time_series.df
    sensors = input.time_series.sensors

    ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

    if len(ws_sensors) < 2:
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=get_time_range(df),
            created_at=datetime.now(),
        )
        return AnalysisResult.create(
            schema=WindShearAggregateProfileSchema,
            data=_create_empty_shear_dataframe(),
            metadata=metadata,
        )

    result_df = _process_shear_profile(df, ws_sensors)

    metadata = AnalysisMetadata(
        mast_name=input.mast_name,
        time_range=get_time_range(df),
        created_at=datetime.now(),
    )

    return AnalysisResult.create(
        schema=WindShearAggregateProfileSchema,
        data=result_df,
        metadata=metadata,
    )


class VerticalProfileAnalyzer:
    """Backward-compatible frozen wrapper around pure compute functions."""

    constants: VerticalProfileConstants = VerticalProfileConstants()

    def fit_power_law(
        self,
        heights: list[float],
        wind_speeds: list[float],
    ) -> tuple[float | None, float | None]:
        return fit_power_law(heights, wind_speeds)

    def calculate_wind_shear(
        self,
        height1: float,
        speed1: float,
        height2: float,
        speed2: float,
    ) -> float | None:
        return calculate_wind_shear(height1, speed1, height2, speed2)

    def analyze_vertical_profile(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[VerticalProfileSchema]:
        return analyze_vertical_profile(input)

    def calculate_wind_shear_profile(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[WindShearAggregateProfileSchema]:
        return calculate_wind_shear_profile(input)

    def _get_time_range(self, df: pl.DataFrame) -> str:
        return get_time_range(df)


__all__ = [
    "VerticalProfileAnalyzer",
    "VerticalProfileConstants",
    "analyze_vertical_profile",
    "calculate_wind_shear_profile",
    "calculate_wind_shear",
    "fit_power_law",
    "get_time_range",
]
