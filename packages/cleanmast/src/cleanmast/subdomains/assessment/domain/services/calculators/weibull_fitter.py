"""Weibull fitter service for wind speed distribution analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for fitting Weibull distributions to wind speed data
"""

from dataclasses import dataclass
from datetime import datetime
from math import gamma, log
from typing import TYPE_CHECKING

import numpy as np
import polars as pl
from scipy.optimize import minimize

from cleanmast.subdomains.assessment.domain.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WeibullSchema,
)

if TYPE_CHECKING:
    from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
        SingleMastAnalysisInput,
    )


@dataclass(frozen=True)
class WeibullParameters:
    """Container for fitted Weibull parameters."""

    shape_k: float
    scale_c: float


class WeibullFitter:
    """Fit Weibull distribution to wind speed data.

    This is a domain service that encapsulates the calculation logic for
    fitting Weibull distributions using Maximum Likelihood Estimation (MLE)
    with Method of Moments fallback.

    The Weibull probability density function is:
        f(x) = (k/c) * (x/c)^(k-1) * exp(-(x/c)^k)

    where:
        - k: Shape parameter (dimensionless)
        - c: Scale parameter (m/s)
    """

    # Minimum number of samples required for fitting
    MIN_SAMPLES: int = 10

    def fit(
        self,
        wind_speeds: list[float],
        height: float,
        interpolation_marker: str | None,
    ) -> AnalysisResult[WeibullSchema] | None:
        """Fit Weibull distribution to wind speed data.

        Args:
            wind_speeds: List of wind speed measurements in m/s
            height: Measurement height in meters
            interpolation_marker: Optional marker for interpolation status

        Returns:
            AnalysisResult with WeibullSchema containing fitted parameters
            and density curves, or None if insufficient data (< 10 samples)
        """
        # Return None for insufficient data
        if len(wind_speeds) < self.MIN_SAMPLES:
            return None

        # Filter out non-positive values (Weibull requires x > 0)
        valid_speeds = [ws for ws in wind_speeds if ws > 0]
        if len(valid_speeds) < self.MIN_SAMPLES:
            return None

        # Fit parameters using MLE with MoM fallback
        params = self._fit_parameters(valid_speeds)

        # Calculate histogram data
        bin_centers, observed_density, fitted_density = self._calculate_histogram(
            valid_speeds, params
        )

        # Calculate mean speed from fitted parameters
        # Mean = c * Gamma(1 + 1/k)
        mean_speed = params.scale_c * gamma(1 + 1 / params.shape_k)

        # Create DataFrame matching WeibullSchema
        data = pl.DataFrame({
            "height": [height],
            "interpolation_marker": [interpolation_marker],
            "shape_k": [params.shape_k],
            "scale_c": [params.scale_c],
            "mean_speed": [mean_speed],
            "bin_centers": [bin_centers],
            "observed_density": [observed_density],
            "fitted_density": [fitted_density],
        })

        # Create metadata (using generic info since we don't have full input context)
        metadata = AnalysisMetadata(
            mast_name="unknown",  # Will be set by caller
            time_range=f"n={len(valid_speeds)} samples",
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=WeibullSchema,
            data=data,
            metadata=metadata,
        )

    def fit_from_input(
        self,
        input_data: "SingleMastAnalysisInput",
        ws_column: str,
    ) -> AnalysisResult[WeibullSchema] | None:
        """Fit Weibull distribution from SingleMastAnalysisInput.

        Args:
            input_data: SingleMastAnalysisInput containing time series data
            ws_column: Column name for wind speed data

        Returns:
            AnalysisResult with WeibullSchema, or None if insufficient data
        """
        df = input_data.time_series.df

        if ws_column not in df.columns:
            return None

        # Extract wind speeds
        wind_speeds = df[ws_column].drop_nulls().to_list()

        # Find sensor for this column to get height
        height = 0.0
        interpolation_marker = None
        for sensor in input_data.time_series.sensors:
            if sensor.column_name == ws_column:
                height = sensor.height
                interpolation_marker = None  # Could be derived from sensor metadata
                break

        result = self.fit(wind_speeds, height, interpolation_marker)

        if result is None:
            return None

        metadata = AnalysisMetadata(
            mast_name=input_data.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=WeibullSchema,
            data=result.data,
            metadata=metadata,
        )

    def _fit_parameters(self, wind_speeds: list[float]) -> WeibullParameters:
        """Fit Weibull parameters using MLE with MoM fallback.

        Args:
            wind_speeds: List of valid wind speed measurements

        Returns:
            WeibullParameters with shape_k and scale_c
        """
        try:
            # Try MLE first
            shape_k, scale_c = self._mle_fit(wind_speeds)
        except Exception:
            # Fall back to Method of Moments
            shape_k, scale_c = self._method_of_moments(wind_speeds)

        return WeibullParameters(shape_k=shape_k, scale_c=scale_c)

    def _mle_fit(self, wind_speeds: list[float]) -> tuple[float, float]:
        """Fit Weibull parameters using Maximum Likelihood Estimation.

        Maximizes the log-likelihood:
            LL = n*ln(k) - n*k*ln(c) + (k-1)*sum(ln(x)) - sum((x/c)^k)

        Args:
            wind_speeds: List of valid wind speed measurements

        Returns:
            Tuple of (shape_k, scale_c)

        Raises:
            Exception: If optimization fails
        """
        x = np.array(wind_speeds)
        n = len(x)
        log_x = np.log(x)
        sum_log_x = np.sum(log_x)

        def negative_log_likelihood(params: np.ndarray) -> float:
            """Calculate negative log-likelihood for minimization."""
            k, c = params
            if k <= 0 or c <= 0:
                return 1e10  # Large penalty for invalid parameters

            # LL = n*ln(k) - n*k*ln(c) + (k-1)*sum(ln(x)) - sum((x/c)^k)
            term1 = n * log(k)
            term2 = -n * k * log(c)
            term3 = (k - 1) * sum_log_x
            term4 = -np.sum((x / c) ** k)

            ll = term1 + term2 + term3 + term4
            return -ll  # Return negative for minimization

        # Initial guess using Method of Moments
        initial_k, initial_c = self._method_of_moments(wind_speeds)
        initial_params = np.array([initial_k, initial_c])

        # Optimize with bounds k > 0, c > 0
        result = minimize(
            negative_log_likelihood,
            initial_params,
            method="L-BFGS-B",
            bounds=[(0.01, 10.0), (0.01, 50.0)],  # Reasonable bounds for wind
        )

        if not result.success:
            raise RuntimeError(f"MLE optimization failed: {result.message}")

        shape_k, scale_c = result.x
        return float(shape_k), float(scale_c)

    def _method_of_moments(self, wind_speeds: list[float]) -> tuple[float, float]:
        """Fit Weibull parameters using Method of Moments.

        Uses empirical approximation:
            k = (std / mean)^(-1.086)
            c = mean / Gamma(1 + 1/k)

        Args:
            wind_speeds: List of valid wind speed measurements

        Returns:
            Tuple of (shape_k, scale_c)
        """
        x = np.array(wind_speeds)
        mean = float(np.mean(x))
        std = float(np.std(x, ddof=1))  # Sample standard deviation

        if mean <= 0 or std <= 0:
            # Fallback to reasonable defaults
            return 2.0, mean

        # Empirical approximation for shape parameter
        cv = std / mean  # Coefficient of variation
        shape_k = cv ** (-1.086)

        # Calculate scale parameter
        scale_c = mean / gamma(1 + 1 / shape_k)

        return shape_k, scale_c

    def _calculate_histogram(
        self,
        wind_speeds: list[float],
        params: WeibullParameters,
    ) -> tuple[list[float], list[float], list[float]]:
        """Calculate histogram bins and densities.

        Creates 1 m/s bins from 0 to max(wind_speeds) + 1.

        Args:
            wind_speeds: List of valid wind speed measurements
            params: Fitted Weibull parameters

        Returns:
            Tuple of (bin_centers, observed_density, fitted_density)
        """
        x = np.array(wind_speeds)
        max_speed = float(np.max(x))

        # Create 1 m/s bins from 0 to max+1
        bin_edges = np.arange(0, int(max_speed) + 2, 1.0)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Calculate observed density (normalized histogram)
        observed_counts, _ = np.histogram(x, bins=bin_edges)
        observed_density = observed_counts / (len(x) * 1.0)  # Normalize by bin width

        # Calculate fitted density using Weibull PDF
        fitted_density = self._weibull_pdf(bin_centers, params.shape_k, params.scale_c)

        return (
            bin_centers.tolist(),
            observed_density.tolist(),
            fitted_density.tolist(),
        )

    def _weibull_pdf(self, x: np.ndarray, k: float, c: float) -> np.ndarray:
        """Calculate Weibull probability density function.

        Formula: f(x) = (k/c) * (x/c)^(k-1) * exp(-(x/c)^k)

        Args:
            x: Array of wind speed values
            k: Shape parameter
            c: Scale parameter

        Returns:
            Array of PDF values
        """
        # Handle x <= 0 (PDF is 0 for non-positive values)
        result = np.zeros_like(x, dtype=float)

        # Only calculate for positive values
        mask = x > 0
        x_pos = x[mask]

        # f(x) = (k/c) * (x/c)^(k-1) * exp(-(x/c)^k)
        term1 = k / c
        term2 = (x_pos / c) ** (k - 1)
        term3 = np.exp(-((x_pos / c) ** k))

        result[mask] = term1 * term2 * term3

        return result

    def _get_time_range(self, df: pl.DataFrame) -> str:
        """Get time range string from DataFrame.

        Args:
            df: DataFrame with timestamp column

        Returns:
            String representation of time range
        """
        if "timestamp" not in df.columns:
            return "unknown"

        min_ts = df["timestamp"].min()
        max_ts = df["timestamp"].max()
        return f"{min_ts} to {max_ts}"

    def calculate_weibull_pdf(
        self,
        wind_speeds: np.ndarray,
        shape_k: float,
        scale_c: float,
    ) -> np.ndarray:
        """Public method to calculate Weibull PDF for given wind speeds.

        Args:
            wind_speeds: Array of wind speed values
            shape_k: Shape parameter (k)
            scale_c: Scale parameter (c)

        Returns:
            Array of PDF values
        """
        return self._weibull_pdf(wind_speeds, shape_k, scale_c)
