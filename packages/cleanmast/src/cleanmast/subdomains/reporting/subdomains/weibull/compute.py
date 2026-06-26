"""Weibull distribution fitting for the reporting domain.

# LOGIC-PRESERVATION: Ported from assessment weibull/services/_calculator.py.
All formulas, constants, and algorithms preserved exactly.
Pure functions only — no IO, no side effects.
Stateless: module-level functions, no class with __init__.
"""

from dataclasses import dataclass
from math import gamma, log

import numpy as np
from scipy.optimize import minimize

# Minimum number of samples required for fitting
MIN_SAMPLES = 10

# Reasonable parameter bounds for wind speed Weibull distribution
_BOUND_K = (0.01, 10.0)
_BOUND_C = (0.01, 50.0)


@dataclass(frozen=True)
class WeibullFitResult:
    """Container for Weibull fitting result at a single height.

    Includes fitted parameters, mean speed, and histogram curves.
    """

    height: float
    interpolation_marker: str | None
    shape_k: float
    scale_c: float
    mean_speed: float
    bin_centers: list[float]
    observed_density: list[float]
    fitted_density: list[float]


def weibull_pdf(x: np.ndarray, k: float, c: float) -> np.ndarray:
    """Calculate Weibull probability density function.

    LOGIC-PRESERVATION: identical to _weibull_pdf from assessment.

    Formula: f(x) = (k/c) * (x/c)^(k-1) * exp(-(x/c)^k)
    """
    result = np.zeros_like(x, dtype=float)
    mask = x > 0
    x_pos = x[mask]

    term1 = k / c
    term2 = (x_pos / c) ** (k - 1)
    term3 = np.exp(-((x_pos / c) ** k))
    result[mask] = term1 * term2 * term3

    return result


def _method_of_moments(wind_speeds: list[float]) -> tuple[float, float]:
    """Fit Weibull parameters using Method of Moments.

    LOGIC-PRESERVATION: identical to assessment _method_of_moments.

    Uses empirical approximation:
        k = (std / mean)^(-1.086)
        c = mean / Gamma(1 + 1/k)
    """
    x = np.array(wind_speeds)
    mean_val = float(np.mean(x))
    std_val = float(np.std(x, ddof=1))

    if mean_val <= 0 or std_val <= 0:
        return 2.0, mean_val

    cv = std_val / mean_val
    shape_k = cv ** (-1.086)
    scale_c = mean_val / gamma(1 + 1 / shape_k)

    return shape_k, scale_c


def _mle_fit(wind_speeds: list[float]) -> tuple[float, float]:
    """Fit Weibull parameters using Maximum Likelihood Estimation.

    LOGIC-PRESERVATION: identical to assessment _mle_fit.

    Maximizes log-likelihood:
        LL = n*ln(k) - n*k*ln(c) + (k-1)*sum(ln(x)) - sum((x/c)^k)
    """
    x = np.array(wind_speeds)
    n = len(x)
    log_x = np.log(x)
    sum_log_x = np.sum(log_x)

    def negative_log_likelihood(params: np.ndarray) -> float:
        k, c = params
        if k <= 0 or c <= 0:
            return 1e10

        term1 = n * log(k)
        term2 = -n * k * log(c)
        term3 = (k - 1) * sum_log_x
        term4 = -np.sum((x / c) ** k)

        ll_val = term1 + term2 + term3 + term4
        return -ll_val

    initial_k, initial_c = _method_of_moments(wind_speeds)
    initial_params = np.array([initial_k, initial_c])

    result = minimize(
        negative_log_likelihood,
        initial_params,
        method="L-BFGS-B",
        bounds=[_BOUND_K, _BOUND_C],
    )

    if not result.success:
        raise RuntimeError(f"MLE optimization failed: {result.message}")

    shape_k, scale_c = result.x
    return float(shape_k), float(scale_c)


def _fit_parameters(wind_speeds: list[float]) -> tuple[float, float]:
    """Fit Weibull parameters using MLE with MoM fallback.

    LOGIC-PRESERVATION: identical logic to assessment _fit_parameters.
    Improved: replaces bare except Exception with specific exception types.
    """
    try:
        return _mle_fit(wind_speeds)
    except (RuntimeError, ValueError):
        return _method_of_moments(wind_speeds)


def _calculate_histogram(
    wind_speeds: list[float],
    shape_k: float,
    scale_c: float,
) -> tuple[list[float], list[float], list[float]]:
    """Calculate histogram bins and densities.

    LOGIC-PRESERVATION: identical to assessment _calculate_histogram.

    Creates 1 m/s bins from 0 to max(wind_speeds) + 1.
    """
    x = np.array(wind_speeds)
    max_speed = float(np.max(x))

    bin_edges = np.arange(0, int(max_speed) + 2, 1.0)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    observed_counts, _ = np.histogram(x, bins=bin_edges)
    observed_density = observed_counts / (len(x) * 1.0)

    fitted_density_arr = weibull_pdf(bin_centers, shape_k, scale_c)

    return (
        bin_centers.tolist(),
        observed_density.tolist(),
        fitted_density_arr.tolist(),
    )


def fit_weibull(
    wind_speeds: list[float],
    height: float,
    interpolation_marker: str | None = None,
) -> WeibullFitResult | None:
    """Fit Weibull distribution to wind speed data.

    LOGIC-PRESERVATION: identical to assessment WeibullFitter.fit().

    Returns None if insufficient data (< MIN_SAMPLES valid samples).
    """
    if len(wind_speeds) < MIN_SAMPLES:
        return None

    valid_speeds = [ws for ws in wind_speeds if ws > 0]
    if len(valid_speeds) < MIN_SAMPLES:
        return None

    shape_k, scale_c = _fit_parameters(valid_speeds)

    bin_centers, observed_density, fitted_density = _calculate_histogram(
        valid_speeds, shape_k, scale_c
    )

    mean_speed = scale_c * gamma(1 + 1 / shape_k)

    return WeibullFitResult(
        height=height,
        interpolation_marker=interpolation_marker,
        shape_k=shape_k,
        scale_c=scale_c,
        mean_speed=mean_speed,
        bin_centers=bin_centers,
        observed_density=observed_density,
        fitted_density=fitted_density,
    )
