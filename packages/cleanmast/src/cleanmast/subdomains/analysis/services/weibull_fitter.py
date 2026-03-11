"""Weibull fitter service (placeholder).

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓

Analysis not yet migrated from Julia. Use Julia implementation.
"""

from pathlib import Path
from typing import Any

import polars as pl


class WeibullFitter:
    """Fit Weibull distribution to wind speed data.

    Analysis not yet migrated from Julia. Use Julia implementation.
    """

    def fit(
        self,
        df: pl.DataFrame,
        ws_column: str,
    ) -> dict[str, float]:
        """Fit Weibull distribution to wind speed data.

        Fits the Weibull probability density function:
        f(v) = (k/c) * (v/c)^(k-1) * exp(-(v/c)^k)

        where:
        - k: Shape parameter (dimensionless)
        - c: Scale parameter (m/s)

        Args:
            df: Input DataFrame with wind speed data
            ws_column: Column name for wind speed

        Returns:
            Dictionary with fitted parameters (k, c)

        Raises:
            NotImplementedError: This analysis is not yet implemented in Python
        """
        raise NotImplementedError(
            "Weibull fitting is not yet implemented in Python. "
            "Use: julia bin/CleanMast.jl analyze weibull"
        )

    def fit_by_sector(
        self,
        df: pl.DataFrame,
        ws_column: str,
        wd_column: str,
        n_sectors: int = 12,
    ) -> dict[str, dict[str, float]]:
        """Fit Weibull distribution by wind direction sector.

        Args:
            df: Input DataFrame with wind data
            ws_column: Column name for wind speed
            wd_column: Column name for wind direction
            n_sectors: Number of direction sectors (default: 12)

        Returns:
            Dictionary with fitted parameters for each sector

        Raises:
            NotImplementedError: This analysis is not yet implemented in Python
        """
        raise NotImplementedError(
            "Sector-wise Weibull fitting is not yet implemented in Python. "
            "Use: julia bin/CleanMast.jl analyze weibull --by-sector"
        )

    def calculate_aep(
        self,
        weibull_params: dict[str, float],
        turbine_curve: dict[str, Any],
    ) -> float:
        """Calculate Annual Energy Production (AEP) from Weibull parameters.

        Args:
            weibull_params: Dictionary with k and c parameters
            turbine_curve: Turbine power curve data

        Returns:
            Estimated AEP in MWh

        Raises:
            NotImplementedError: This analysis is not yet implemented in Python
        """
        raise NotImplementedError(
            "AEP calculation from Weibull is not yet implemented in Python. "
            "Use: julia bin/CleanMast.jl analyze aep"
        )

    def save_to_file(
        self,
        weibull_data: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Save Weibull fit results to file.

        Args:
            weibull_data: Weibull fit data dictionary
            output_path: Output file path

        Raises:
            NotImplementedError: This analysis is not yet implemented in Python
        """
        raise NotImplementedError(
            "Weibull result saving is not yet implemented in Python. "
            "Use: julia bin/CleanMast.jl analyze weibull"
        )
