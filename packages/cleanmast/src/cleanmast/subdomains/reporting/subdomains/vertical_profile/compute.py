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
    WindShearSchema,
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


def calculate_shear_matrix(
    heights: list[float],
    wind_speeds: list[float],
) -> list[list[float | None]]:
    n = len(heights)

    if n == 0 or len(wind_speeds) != n:
        return []

    matrix: list[list[float | None]] = [[None] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = None
            else:
                alpha = calculate_wind_shear(
                    heights[i], wind_speeds[i],
                    heights[j], wind_speeds[j]
                )
                matrix[i][j] = alpha

    return matrix


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
        "alpha_mean": pl.Series([], dtype=pl.Float64),
        "alpha_std": pl.Series([], dtype=pl.Float64),
        "alpha_min": pl.Series([], dtype=pl.Float64),
        "alpha_max": pl.Series([], dtype=pl.Float64),
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


def _calculate_shear_series(
    df: pl.DataFrame,
    col1: str,
    col2: str,
    h1: float,
    h2: float,
) -> list[float]:
    shear_values: list[float] = []

    filtered = df.filter(
        (pl.col(col1).is_not_null()) & (pl.col(col1) > 0) &
        (pl.col(col2).is_not_null()) & (pl.col(col2) > 0)
    )

    if filtered.is_empty():
        return shear_values

    s1 = filtered[col1].to_numpy()
    s2 = filtered[col2].to_numpy()

    for v1, v2 in zip(s1, s2):
        alpha = calculate_wind_shear(h1, float(v1), h2, float(v2))
        if alpha is not None:
            shear_values.append(alpha)

    return shear_values


def _process_shear_analysis(
    df: pl.DataFrame,
    sensors: list["SensorColumn"],
) -> pl.DataFrame:
    valid_sensors: list[tuple[float, str]] = []
    for sensor in sensors:
        ws_col = sensor.column_name
        if ws_col not in df.columns:
            continue

        valid_count = df.filter(
            (pl.col(ws_col).is_not_null()) & (pl.col(ws_col) > 0)
        ).height

        if valid_count is not None and valid_count >= MIN_SAMPLES:
            valid_sensors.append((sensor.height, ws_col))

    valid_sensors.sort(key=lambda x: x[0])

    rows: list[dict[str, object]] = []
    for i in range(len(valid_sensors)):
        for j in range(i + 1, len(valid_sensors)):
            h1, col1 = valid_sensors[i]
            h2, col2 = valid_sensors[j]

            shear_values = _calculate_shear_series(df, col1, col2, h1, h2)

            if shear_values:
                rows.append({
                    "from_height": h1,
                    "to_height": h2,
                    "alpha_mean": float(np.mean(shear_values)),
                    "alpha_std": float(np.std(shear_values)),
                    "alpha_min": float(np.min(shear_values)),
                    "alpha_max": float(np.max(shear_values)),
                })

    return pl.DataFrame(rows) if rows else _create_empty_shear_dataframe()


def calculate_wind_shear_analysis(
    input: SingleMastAnalysisInput,
) -> AnalysisResult[WindShearSchema]:
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
            schema=WindShearSchema,
            data=_create_empty_shear_dataframe(),
            metadata=metadata,
        )

    result_df = _process_shear_analysis(df, ws_sensors)

    metadata = AnalysisMetadata(
        mast_name=input.mast_name,
        time_range=get_time_range(df),
        created_at=datetime.now(),
    )

    return AnalysisResult.create(
        schema=WindShearSchema,
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

    def calculate_shear_matrix(
        self,
        heights: list[float],
        wind_speeds: list[float],
    ) -> list[list[float | None]]:
        return calculate_shear_matrix(heights, wind_speeds)

    def analyze_vertical_profile(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[VerticalProfileSchema]:
        return analyze_vertical_profile(input)

    def calculate_wind_shear_analysis(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[WindShearSchema]:
        return calculate_wind_shear_analysis(input)

    def _get_time_range(self, df: pl.DataFrame) -> str:
        return get_time_range(df)


__all__ = [
    "VerticalProfileAnalyzer",
    "VerticalProfileConstants",
    "analyze_vertical_profile",
    "calculate_wind_shear_analysis",
    "calculate_wind_shear",
    "calculate_shear_matrix",
    "fit_power_law",
    "get_time_range",
]
