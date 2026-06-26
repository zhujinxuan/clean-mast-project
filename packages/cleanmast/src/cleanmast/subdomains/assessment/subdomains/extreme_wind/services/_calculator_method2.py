"""Fifty-year max wind Method 2 (五日最大法) calculator.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating 50-year max wind using Gumbel
distribution fitted to 5-day maxima.
"""

import math
from datetime import datetime
from typing import cast

import numpy as np
import polars as pl
from scipy.optimize import minimize

from cleanmast.subdomains.assessment.shared.utils.air_density import (
    calculate_air_density_for_height,
    convert_to_standard_air_density,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindResultSchema,
    GumbelParameterSchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

EULER_MASCHERONI = 0.5772156649


def extract_five_day_maxima(wind_speeds: pl.Series, timestamps: pl.Series) -> pl.Series:
    """Extract 5-day maxima from wind speed time series.

    Args:
        wind_speeds: Series of wind speed values
        timestamps: Series of timestamps

    Returns:
        Series of 5-day maximum wind speeds
    """
    df = pl.DataFrame({"timestamp": timestamps, "wind_speed": wind_speeds})
    df = df.filter(pl.col("wind_speed").is_not_null() & pl.col("wind_speed").is_finite())
    df = df.sort("timestamp")

    if df.is_empty():
        return pl.Series("max_wind_speed", [], dtype=pl.Float64)

    first_ts = df["timestamp"][0]
    df = df.with_columns(
        ((pl.col("timestamp") - first_ts).dt.total_days() / 5).floor().cast(pl.Int64).alias("period")
    )
    maxima = df.group_by("period").agg(pl.col("wind_speed").max().alias("max_wind"))
    maxima = maxima.sort("period")
    return maxima["max_wind"]


def fit_gumbel_distribution(data: list[float]) -> tuple[float, float] | None:
    """Fit Gumbel distribution to data using MLE with MoM fallback.

    Args:
        data: List of wind speed observations

    Returns:
        (mu, beta) tuple or None if insufficient data
    """
    valid = [x for x in data if x > 0 and math.isfinite(x)]
    if len(valid) < 5:
        return None

    arr = np.asarray(valid, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1))

    beta_init = std * math.sqrt(6.0) / math.pi
    mu_init = mean - beta_init * EULER_MASCHERONI

    if beta_init < 0.001:
        return mu_init, beta_init

    def neg_log_likelihood(params: np.ndarray) -> float:
        mu, beta = params
        if beta <= 0:
            return 1e12
        n = len(arr)
        z = (arr - mu) / beta
        return float(n * math.log(beta) + np.sum(z) + np.sum(np.exp(-z)))

    bounds = [
        (mu_init - 5.0 * beta_init, mu_init + 5.0 * beta_init),
        (0.01, 10.0 * beta_init),
    ]

    result = minimize(
        neg_log_likelihood,
        x0=np.array([mu_init, beta_init]),
        method="L-BFGS-B",
        bounds=bounds,
    )

    if result.success:
        mu_fit, beta_fit = result.x
        return float(mu_fit), float(beta_fit)

    return mu_init, beta_init


def calculate_gumbel_return_period(
    mu: float,
    beta: float,
    return_period_years: float = 50.0,
    sampling_period_days: float = 5.0,
) -> float:
    """Calculate return period wind speed from Gumbel parameters.

    Args:
        mu: Gumbel location parameter
        beta: Gumbel scale parameter
        return_period_years: Return period in years
        sampling_period_days: Sampling period in days

    Returns:
        Return period wind speed
    """
    t = return_period_years * 365.0 / sampling_period_days
    p = 1.0 - 1.0 / t
    return mu - beta * math.log(-math.log(p))


class Method2Calculator:
    """Calculate fifty-year maximum wind speed using Method 2 (五日最大法)."""

    def calculate_sustained(
        self,
        input: SingleMastAnalysisInput,
    ) -> tuple[AnalysisResult[FiftyYearMaxWindResultSchema], AnalysisResult[GumbelParameterSchema]]:
        """Calculate sustained 50-year max wind for all heights."""
        wind_rows, param_rows = self._calculate_for_wind_speed_type(input, "sustained")
        return self._build_results(wind_rows, param_rows, input)

    def calculate_extreme(
        self,
        input: SingleMastAnalysisInput,
        sustained_result: AnalysisResult[FiftyYearMaxWindResultSchema] | None = None,
    ) -> tuple[AnalysisResult[FiftyYearMaxWindResultSchema], AnalysisResult[GumbelParameterSchema]]:
        """Calculate extreme 50-year max wind for all heights."""
        wind_rows, param_rows = self._calculate_for_wind_speed_type(
            input, "extreme", sustained_result
        )
        return self._build_results(wind_rows, param_rows, input)

    def _calculate_for_wind_speed_type(
        self,
        input: SingleMastAnalysisInput,
        wind_speed_type: str,
        sustained_result: AnalysisResult[FiftyYearMaxWindResultSchema] | None = None,
    ) -> tuple[list[dict], list[dict]]:
        df = input.time_series.df
        sensors = input.time_series.sensors
        heights = input.parameters.heights

        air_density = input.parameters.air_density
        reference_height = self._get_reference_height_from_sensors(sensors, default=10.0)

        sustained_lookup: dict[float, tuple[float, str | None]] = {}
        if sustained_result is not None and wind_speed_type == "extreme":
            for row in sustained_result.data.filter(
                pl.col("wind_speed_type") == "sustained"
            ).iter_rows(named=True):
                sustained_lookup[row["height"]] = (row["max_wind_speed"], row.get("interpolation_marker"))

        wind_rows: list[dict] = []
        param_rows: list[dict] = []

        for height in heights:
            if wind_speed_type == "sustained":
                sensor = self._find_avg_wind_speed_sensor(sensors, height)
            else:
                sensor = self._find_max_wind_speed_sensor(sensors, height)

            if sensor is None:
                if wind_speed_type == "extreme" and height in sustained_lookup:
                    self._add_extreme_fallback(height, sustained_lookup, air_density, reference_height, wind_rows)
                continue

            ws_col = sensor.column_name
            if ws_col not in df.columns:
                if wind_speed_type == "extreme" and height in sustained_lookup:
                    self._add_extreme_fallback(height, sustained_lookup, air_density, reference_height, wind_rows)
                continue

            valid_df = df.filter(
                pl.col(ws_col).is_not_null() & (pl.col(ws_col) > 0) & pl.col(ws_col).is_finite()
            )
            if valid_df.is_empty():
                if wind_speed_type == "extreme" and height in sustained_lookup:
                    self._add_extreme_fallback(height, sustained_lookup, air_density, reference_height, wind_rows)
                continue

            timestamps = valid_df["timestamp"]
            wind_speeds = valid_df[ws_col]
            maxima = extract_five_day_maxima(wind_speeds, timestamps)
            maxima_list = maxima.to_list()

            if len(maxima_list) < 5:
                if wind_speed_type == "extreme" and height in sustained_lookup:
                    self._add_extreme_fallback(height, sustained_lookup, air_density, reference_height, wind_rows)
                continue

            fit = fit_gumbel_distribution(maxima_list)
            if fit is None:
                if wind_speed_type == "extreme" and height in sustained_lookup:
                    self._add_extreme_fallback(height, sustained_lookup, air_density, reference_height, wind_rows)
                continue

            mu, beta = fit
            max_wind = calculate_gumbel_return_period(mu, beta)

            interpolation_marker = sensor.detect_interpolation_marker()
            air_density_at_height = calculate_air_density_for_height(
                height=height,
                reference_density=air_density,
                reference_height=reference_height,
            )
            max_wind_std = convert_to_standard_air_density(max_wind, air_density_at_height)

            observed_max = max(maxima_list) if maxima_list else None
            wind_rows.append({
                "height": height,
                "interpolation_marker": interpolation_marker or None,
                "wind_speed_type": wind_speed_type,
                "method": "method2",
                "max_wind_speed": max_wind,
                "standard_density_wind_speed": max_wind_std,
                "observed_max": observed_max,
            })

            sample_mean = cast(float, maxima.mean())
            sample_std = cast(float, maxima.std())
            param_rows.append({
                "height": height,
                "wind_speed_type": wind_speed_type,
                "mu": mu,
                "beta": beta,
                "sample_count": len(maxima_list),
                "sample_mean": sample_mean,
                "sample_std": sample_std,
                "sample_data": maxima_list,
            })

        return wind_rows, param_rows

    def _build_results(
        self,
        wind_rows: list[dict],
        param_rows: list[dict],
        input: SingleMastAnalysisInput,
    ) -> tuple[AnalysisResult[FiftyYearMaxWindResultSchema], AnalysisResult[GumbelParameterSchema]]:
        df = input.time_series.df
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        wind_df = pl.DataFrame(wind_rows) if wind_rows else self._create_empty_wind_dataframe()
        param_df = pl.DataFrame(param_rows) if param_rows else self._create_empty_param_dataframe()

        wind_result = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=wind_df,
            metadata=metadata,
        )
        param_result = AnalysisResult.create(
            schema=GumbelParameterSchema,
            data=param_df,
            metadata=metadata,
        )
        return wind_result, param_result

    def _add_extreme_fallback(
        self,
        height: float,
        sustained_lookup: dict[float, tuple[float, str | None]],
        air_density: float,
        reference_height: float,
        wind_rows: list[dict],
    ) -> None:
        sustained_ws, interp_marker = sustained_lookup[height]
        extreme_ws = sustained_ws * 1.4
        air_density_at_height = calculate_air_density_for_height(
            height=height,
            reference_density=air_density,
            reference_height=reference_height,
        )
        extreme_std = convert_to_standard_air_density(extreme_ws, air_density_at_height)
        wind_rows.append({
            "height": height,
            "interpolation_marker": interp_marker,
            "wind_speed_type": "extreme",
            "method": "method2",
            "max_wind_speed": extreme_ws,
            "standard_density_wind_speed": extreme_std,
            "observed_max": None,
        })

    def _find_avg_wind_speed_sensor(
        self,
        sensors: list[SensorColumn],
        height: float,
    ) -> SensorColumn | None:
        return next(
            (
                s
                for s in sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg" and s.height == height
            ),
            None,
        )

    def _find_max_wind_speed_sensor(
        self,
        sensors: list[SensorColumn],
        height: float,
    ) -> SensorColumn | None:
        return next(
            (
                s
                for s in sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "max" and s.height == height
            ),
            None,
        )

    def _get_reference_height_from_sensors(
        self,
        sensors: list[SensorColumn],
        default: float = 10.0,
    ) -> float:
        temp_sensor = next(
            (s for s in sensors if s.sensor_type == "Temperature" and s.stat_type == "avg"),
            None,
        )
        if temp_sensor is not None:
            return temp_sensor.height

        pressure_sensor = next(
            (s for s in sensors if s.sensor_type == "Pressure" and s.stat_type == "avg"),
            None,
        )
        if pressure_sensor is not None:
            return pressure_sensor.height

        return default

    def _create_empty_wind_dataframe(self) -> pl.DataFrame:
        return pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "method": pl.Series([], dtype=pl.String),
            "max_wind_speed": pl.Series([], dtype=pl.Float64),
            "standard_density_wind_speed": pl.Series([], dtype=pl.Float64),
            "observed_max": pl.Series([], dtype=pl.Float64),
        })

    def _create_empty_param_dataframe(self) -> pl.DataFrame:
        return pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "mu": pl.Series([], dtype=pl.Float64),
            "beta": pl.Series([], dtype=pl.Float64),
            "sample_count": pl.Series([], dtype=pl.Int64),
            "sample_mean": pl.Series([], dtype=pl.Float64),
            "sample_std": pl.Series([], dtype=pl.Float64),
            "sample_data": pl.Series([], dtype=pl.List(pl.Float64)),
        })

    def _get_time_range(self, df: pl.DataFrame) -> str:
        if "timestamp" not in df.columns or df.is_empty():
            return "Unknown"

        timestamps = df["timestamp"]
        start = timestamps.min()
        end = timestamps.max()

        if start is None or end is None:
            return "Unknown"

        start_str = str(start)[:10]
        end_str = str(end)[:10]

        return f"{start_str} to {end_str}"
