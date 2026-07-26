"""Extreme wind computation — pure functions only.

LOGIC-PRESERVATION: Ported from assessment extreme_wind services/calculators.
All algorithms, constants, and formulas preserved exactly.
"""

import math
from typing import NotRequired, TypedDict

import numpy as np
import polars as pl
from scipy.optimize import minimize

EULER_MASCHERONI = 0.5772156649
STANDARD_AIR_DENSITY = 1.225
GAS_CONSTANT_DRY_AIR = 287.05
KELVIN_OFFSET = 273.15
GRAVITY = 9.81
STD_TEMP_SEA_LEVEL = 288.15
LAPSE_RATE = 0.0065


# ── TypedDicts for accumulator row shapes ──

class Method2Result(TypedDict):
    """Return shape of :func:`calculate_method2`.

    Mirrors :class:`FiftyYearMaxWindResultSchema` + Gumbel fit fields.
    Gumbel fields are ``NotRequired`` — callers guard with ``"mu" in result``.
    """

    height: float
    interpolation_marker: str | None
    wind_speed_type: str
    method: str
    max_wind_speed: float
    standard_density_wind_speed: float
    observed_max: float | None
    mu: NotRequired[float]
    beta: NotRequired[float]
    sample_count: NotRequired[int]
    sample_mean: NotRequired[float]
    sample_std: NotRequired[float]
    sample_data: NotRequired[list[float]]


class Method3Result(TypedDict):
    """Return shape of :func:`calculate_method3`.

    Mirrors :class:`FiftyYearMaxWindResultSchema` (observed_max is required).
    """

    height: float
    interpolation_marker: str | None
    wind_speed_type: str
    method: str
    max_wind_speed: float
    standard_density_wind_speed: float
    observed_max: float


class Method2WindRow(TypedDict):
    """Row shape for Method 2 wind result tables — mirrors
    :class:`FiftyYearMaxWindResultSchema`.
    """

    height: float
    interpolation_marker: str | None
    wind_speed_type: str
    method: str
    max_wind_speed: float
    standard_density_wind_speed: float
    observed_max: float | None


class Method1Row(TypedDict):
    """Row shape for Method 1 detail tables — mirrors
    :class:`FiftyYearMaxWindMethod1DetailSchema`.
    """

    height: float
    interpolation_marker: str | None
    wind_speed_type: str
    method: str
    max_wind_speed: float
    standard_density_wind_speed: float
    average_wind_speed: float
    air_density: float


class GumbelParamRow(TypedDict):
    """Row shape for Gumbel parameter tables — mirrors
    :class:`GumbelParameterSchema`.
    """

    height: float
    wind_speed_type: str
    mu: float
    beta: float
    sample_count: int
    sample_mean: float
    sample_std: float
    sample_data: list[float] | None


class SummaryComparisonRow(TypedDict):
    """Row shape for multi-method comparison tables — mirrors
    :class:`FiftyYearMaxWindComparisonSchema` + ``interpolation_marker``.
    """

    height: float
    method1: float
    method2: float
    method3: float
    conservative_max: float
    wind_speed_type: str
    interpolation_marker: str


class IECClassRow(TypedDict):
    """Row shape for IEC wind-class reference tables — mirrors
    :class:`IECWindClassSchema`.
    """

    wind_class: str
    height: float | None
    sustained_threshold: float
    extreme_threshold: float
    conservative_sustained: float | None
    conservative_extreme: float | None

# ---- Method 2: 五日最大法 ----


def extract_five_day_maxima(
    wind_speeds: pl.Series,
    timestamps: pl.Series,
) -> pl.Series:
    """Extract 5-day maxima from wind speed time series."""
    df = pl.DataFrame({"timestamp": timestamps, "wind_speed": wind_speeds})
    df = df.filter(pl.col("wind_speed").is_not_null() & pl.col("wind_speed").is_finite())
    df = df.sort("timestamp")

    if df.is_empty():
        return pl.Series("max_wind_speed", [], dtype=pl.Float64)

    first_ts = df["timestamp"][0]
    df = df.with_columns(
        ((pl.col("timestamp") - first_ts).dt.total_days() / 5).floor()
        .cast(pl.Int64)
        .alias("period")
    )
    maxima = df.group_by("period").agg(pl.col("wind_speed").max().alias("max_wind"))
    maxima = maxima.sort("period")
    return maxima["max_wind"]


def fit_gumbel_distribution(data: list[float]) -> tuple[float, float] | None:
    """Fit Gumbel distribution using MLE with MoM fallback."""
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
    """Calculate return period wind speed from Gumbel parameters."""
    t = return_period_years * 365.0 / sampling_period_days
    p = 1.0 - 1.0 / t
    return mu - beta * math.log(-math.log(p))


def calculate_method2(
    five_day_maxima: list[float],
    height: float,
    air_density: float,
    reference_height: float,
    wind_speed_type: str,
    interpolation_marker: str = "",
) -> Method2Result | None:
    """Calculate Method 2 (Gumbel fit to 5-day maxima) for one height."""
    fit = fit_gumbel_distribution(five_day_maxima)
    if fit is None:
        return None

    mu, beta = fit
    max_wind = calculate_gumbel_return_period(mu, beta)

    rho_h = _compute_density_at_height(height, air_density, reference_height)
    max_wind_std = _convert_to_standard(max_wind, rho_h)

    observed_max = max(five_day_maxima) if five_day_maxima else None
    sample_mean = float(np.mean(five_day_maxima))
    sample_std = float(np.std(five_day_maxima, ddof=1))

    return {
        "height": height,
        "interpolation_marker": interpolation_marker or None,
        "wind_speed_type": wind_speed_type,
        "method": "method2",
        "max_wind_speed": max_wind,
        "standard_density_wind_speed": max_wind_std,
        "observed_max": observed_max,
        "mu": mu,
        "beta": beta,
        "sample_count": len(five_day_maxima),
        "sample_mean": sample_mean,
        "sample_std": sample_std,
        "sample_data": five_day_maxima,
    }


# ---- Method 3: 极端风速模型法 ----

def calculate_method3(
    observed_max: float,
    height: float,
    air_density: float,
    reference_height: float,
    wind_speed_type: str,
    interpolation_marker: str = "",
) -> Method3Result:
    """Calculate Method 3 (EWM: 1.25 * observed_max) for one height."""
    v50 = 1.25 * observed_max
    rho_h = _compute_density_at_height(height, air_density, reference_height)
    v50_std = _convert_to_standard(v50, rho_h)

    return {
        "height": height,
        "interpolation_marker": interpolation_marker or None,
        "wind_speed_type": wind_speed_type,
        "method": "method3",
        "max_wind_speed": v50,
        "standard_density_wind_speed": v50_std,
        "observed_max": observed_max,
    }


# ---- Summary ----

def build_summary_comparison(
    method1_data: pl.DataFrame,
    method2_data: pl.DataFrame,
    method3_data: pl.DataFrame,
    wind_speed_type: str,
) -> pl.DataFrame:
    """Build comparison DataFrame across all three methods."""
    m1_map = _extract_values(method1_data, wind_speed_type)
    m2_map = _extract_values(method2_data, wind_speed_type)
    m3_map = _extract_values(method3_data, wind_speed_type)

    all_heights = set(m1_map.keys()) | set(m2_map.keys()) | set(m3_map.keys())

    rows: list[SummaryComparisonRow] = []
    for height in sorted(all_heights):
        m1_value, m1_marker = m1_map.get(height, (0.0, ""))
        m2_value, m2_marker = m2_map.get(height, (0.0, ""))
        m3_value, m3_marker = m3_map.get(height, (0.0, ""))
        marker = m1_marker or m2_marker or m3_marker
        conservative_max = max(m1_value, m2_value, m3_value)

        rows.append({
            "height": height,
            "method1": m1_value,
            "method2": m2_value,
            "method3": m3_value,
            "conservative_max": conservative_max,
            "wind_speed_type": wind_speed_type,
            "interpolation_marker": marker,
        })

    return pl.DataFrame(rows) if rows else pl.DataFrame({
        "height": pl.Series([], dtype=pl.Float64),
        "method1": pl.Series([], dtype=pl.Float64),
        "method2": pl.Series([], dtype=pl.Float64),
        "method3": pl.Series([], dtype=pl.Float64),
        "conservative_max": pl.Series([], dtype=pl.Float64),
        "wind_speed_type": pl.Series([], dtype=pl.String),
        "interpolation_marker": pl.Series([], dtype=pl.String),
    })


def build_iec_class_table(
    sustained_comp: pl.DataFrame,
    extreme_comp: pl.DataFrame,
) -> pl.DataFrame:
    """Build IEC wind class reference table."""
    rows: list[IECClassRow] = [
        {"wind_class": "I", "height": None, "sustained_threshold": 50.0,
         "extreme_threshold": 70.0, "conservative_sustained": None, "conservative_extreme": None},
        {"wind_class": "II", "height": None, "sustained_threshold": 42.5,
         "extreme_threshold": 59.5, "conservative_sustained": None, "conservative_extreme": None},
        {"wind_class": "III", "height": None, "sustained_threshold": 37.5,
         "extreme_threshold": 52.5, "conservative_sustained": None, "conservative_extreme": None},
        {"wind_class": "S", "height": None, "sustained_threshold": 0.0,
         "extreme_threshold": 0.0, "conservative_sustained": None, "conservative_extreme": None},
    ]

    extreme_lookup: dict[float, float] = {}
    for row in extreme_comp.iter_rows(named=True):
        extreme_lookup[float(row["height"])] = float(row["conservative_max"])

    for row in sustained_comp.sort("height").iter_rows(named=True):
        height = float(row["height"])
        sustained = float(row["conservative_max"])
        extreme = extreme_lookup.get(height, 0.0)
        wind_class = _classify_wind_class(sustained, extreme)

        rows.append({
            "wind_class": wind_class,
            "height": height,
            "sustained_threshold": 0.0,
            "extreme_threshold": 0.0,
            "conservative_sustained": sustained,
            "conservative_extreme": extreme,
        })

    return pl.DataFrame(rows)


# ---- Internal helpers ----

def _compute_density_at_height(
    height: float,
    reference_density: float,
    reference_height: float,
) -> float:
    """Extrapolate air density from reference height to target height."""
    return reference_density * math.exp(
        -GRAVITY * (height - reference_height)
        / (GAS_CONSTANT_DRY_AIR * (STD_TEMP_SEA_LEVEL - LAPSE_RATE * reference_height))
    )


def _compute_air_density_at_heights(
    heights: list[float],
    air_density: float,
    reference_height: float,
) -> list[float]:
    """Compute air density at each analysis height."""
    return [
        _compute_density_at_height(h, air_density, reference_height)
        for h in heights
    ]


def _convert_to_standard(wind_speed: float, actual_density: float) -> float:
    """Convert wind speed to standard air density equivalent."""
    return wind_speed * math.sqrt(actual_density / STANDARD_AIR_DENSITY)


def _extract_values(
    data: pl.DataFrame,
    wind_speed_type: str,
) -> dict[float, tuple[float, str]]:
    """Extract (standard_density_wind_speed, interpolation_marker) per height."""
    if "wind_speed_type" not in data.columns:
        return {}
    filtered = data.filter(pl.col("wind_speed_type") == wind_speed_type)
    values: dict[float, tuple[float, str]] = {}
    for row in filtered.iter_rows(named=True):
        marker = str(row.get("interpolation_marker") or "")
        values[float(row["height"])] = (
            float(row["standard_density_wind_speed"]),
            marker,
        )
    return values


def _classify_wind_class(sustained: float, extreme: float) -> str:
    """Classify IEC wind class based on conservative sustained and extreme."""
    if sustained <= 37.5 and extreme <= 52.5:
        return "III"
    elif sustained <= 42.5 and extreme <= 59.5:
        return "II"
    elif sustained <= 50.0 and extreme <= 70.0:
        return "I"
    else:
        return "S"


def compute_method2_extreme_fallback(
    sustained_wind_speed: float,
    height: float,
    air_density: float,
    reference_height: float,
    gust_factor: float,
    interpolation_marker: str = "",
) -> Method2WindRow:
    """Compute extreme wind from sustained using a per-height gust factor.

    Args:
        sustained_wind_speed: Sustained (10min-avg) wind speed at the height.
        height: Measurement height in meters.
        air_density: Reference air density in kg/m³.
        reference_height: Reference height for air density extrapolation.
        gust_factor: Gust factor for 10min→3s conversion.
        interpolation_marker: Interpolation label if filled height.

    Returns:
        Dict with extreme wind computation result.
    """
    extreme_ws = sustained_wind_speed * gust_factor
    rho_h = _compute_density_at_height(height, air_density, reference_height)
    extreme_std = _convert_to_standard(extreme_ws, rho_h)
    return {
        "height": height,
        "interpolation_marker": interpolation_marker or None,
        "wind_speed_type": "extreme",
        "method": "method2",
        "max_wind_speed": extreme_ws,
        "standard_density_wind_speed": extreme_std,
        "observed_max": None,
    }
