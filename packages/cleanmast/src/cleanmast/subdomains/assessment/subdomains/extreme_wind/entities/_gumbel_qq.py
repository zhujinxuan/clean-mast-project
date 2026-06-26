"""Gumbel Q-Q plot service for fifty-year max wind analysis.

Provides Monte Carlo confidence bands and Q-Q plot generation for
assessing Gumbel distribution fit to extreme wind speed data.
"""

import hashlib
import math
from pathlib import Path
from typing import Any

import altair as alt
import numpy as np
import polars as pl
import scipy.stats
import vl_convert as vlc


def generate_qq_monte_carlo_bands(
    empirical_probs: list[float],
    mu: float,
    beta: float,
    n: int,
    n_monte_carlo: int = 1000,
) -> pl.DataFrame:
    """Generate 95% confidence bands for Q-Q plot via Monte Carlo simulation.

    For each simulation, ``n`` samples are drawn from a Gumbel distribution with
    parameters ``mu`` and ``beta``, sorted, and quantiles are linearly interpolated
    at the requested empirical probabilities. The 2.5% and 97.5% quantiles across
    all simulations form the lower and upper confidence bounds.

    Args:
        empirical_probs: List of empirical probabilities (plotting positions).
        mu: Gumbel location parameter.
        beta: Gumbel scale parameter.
        n: Original sample size (number of observations per simulation).
        n_monte_carlo: Number of Monte Carlo simulations to run.

    Returns:
        Polars DataFrame with columns:
        - ``probs`` (Float64): Empirical probabilities.
        - ``quantiles`` (Float64): Theoretical Gumbel quantiles.
        - ``lower`` (Float64): 2.5% quantile across simulations.
        - ``upper`` (Float64): 97.5% quantile across simulations.
    """
    dist = scipy.stats.gumbel_r(loc=mu, scale=beta)
    probs_array = np.asarray(empirical_probs, dtype=float)
    n_probs = len(empirical_probs)

    simulated_quantiles = np.empty((n_probs, n_monte_carlo), dtype=float)

    for i in range(n_monte_carlo):
        sample = dist.rvs(size=n, random_state=None)
        sample.sort()

        # Fractional index using 0-based indexing: i = p * (n - 1)
        indices = probs_array * (n - 1)
        lower_idx = np.floor(indices).astype(int)
        upper_idx = np.ceil(indices).astype(int)

        # Clip to valid array bounds
        lower_idx = np.clip(lower_idx, 0, n - 1)
        upper_idx = np.clip(upper_idx, 0, n - 1)

        weights = indices - lower_idx
        interpolated = (1.0 - weights) * sample[lower_idx] + weights * sample[upper_idx]
        simulated_quantiles[:, i] = interpolated

    lower_ci = np.quantile(simulated_quantiles, 0.025, axis=1).tolist()
    upper_ci = np.quantile(simulated_quantiles, 0.975, axis=1).tolist()

    theoretical_quantiles = [
        mu - beta * math.log(-math.log(p)) for p in empirical_probs
    ]

    return pl.DataFrame(
        {
            "probs": empirical_probs,
            "quantiles": theoretical_quantiles,
            "lower": lower_ci,
            "upper": upper_ci,
        },
        schema={
            "probs": pl.Float64,
            "quantiles": pl.Float64,
            "lower": pl.Float64,
            "upper": pl.Float64,
        },
    )


def _build_single_qq_chart(
    wind_data: list[float],
    mu: float,
    beta: float,
    height: float,
    width: int = 250,
    height_px: int = 250,
) -> alt.Chart:
    """Build an Altair Q-Q chart for a single height (internal helper)."""
    sorted_data = sorted([x for x in wind_data if x > 0 and math.isfinite(x)])
    n = len(sorted_data)

    if n == 0:
        raise ValueError("No valid wind data after filtering.")

    empirical_probs = [i / (n + 1) for i in range(1, n + 1)]
    bands_df = generate_qq_monte_carlo_bands(empirical_probs, mu, beta, n)

    theoretical_quantiles = bands_df["quantiles"].to_list()

    qq_df = pl.DataFrame(
        {
            "theoretical": theoretical_quantiles,
            "empirical": sorted_data,
        }
    )

    min_val = min(min(theoretical_quantiles), min(sorted_data))
    max_val = max(max(theoretical_quantiles), max(sorted_data))
    diagonal_df = pl.DataFrame({"x": [min_val, max_val], "y": [min_val, max_val]})

    band = (
        alt.Chart(bands_df)
        .mark_area(opacity=0.3, color="lightgray")
        .encode(
            x=alt.X("quantiles:Q", title="Theoretical"),
            y=alt.Y("lower:Q", title="Empirical"),
            y2="upper:Q",
        )
    )

    line = (
        alt.Chart(diagonal_df)
        .mark_line(color="red", strokeDash=[5, 5])
        .encode(x="x:Q", y="y:Q")
    )

    points = (
        alt.Chart(qq_df)
        .mark_point(color="blue")
        .encode(x="theoretical:Q", y="empirical:Q")
    )

    return (band + line + points).properties(
        title=f"{height}m",
        width=width,
        height=height_px,
    )


def generate_gumbel_qq_plot(
    wind_data: list[float],
    mu: float,
    beta: float,
    height: float,
    mast_name: str,
    output_dir: Path,
    wind_speed_type: str,
) -> Path:
    """Generate a single Gumbel Q-Q plot with Monte Carlo confidence bands.

    Args:
        wind_data: List of wind speed observations.
        mu: Gumbel location parameter.
        beta: Gumbel scale parameter.
        height: Sensor height in metres.
        mast_name: Mast identifier for the filename.
        output_dir: Directory where the PNG will be saved.
        wind_speed_type: Type of wind speed (e.g. "sustained" or "extreme").

    Returns:
        Path to the saved PNG file.
    """
    chart = _build_single_qq_chart(
        wind_data=wind_data,
        mu=mu,
        beta=beta,
        height=height,
        width=400,
        height_px=400,
    ).properties(title=f"{height}m ({wind_speed_type})")

    content_hash = hashlib.md5(str(sorted(wind_data)).encode()).hexdigest()[:8]
    filename = f"gumbel_qq_{mast_name}_{int(height)}m_{wind_speed_type}_{content_hash}.png"

    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / filename

    png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
    image_path.write_bytes(png_bytes)

    return image_path


def _arrange_charts_in_subgrid(charts: list[alt.Chart]) -> Any:
    """Arrange charts dynamically according to the required subgrid rules."""
    n = len(charts)
    if n == 1:
        return charts[0]
    if n == 2:
        return alt.hconcat(*charts)
    if n == 3:
        return alt.hconcat(*charts)
    if n == 4:
        return alt.vconcat(
            alt.hconcat(charts[0], charts[1]),
            alt.hconcat(charts[2], charts[3]),
        )
    if n <= 6:
        return alt.vconcat(
            alt.hconcat(*charts[:3]),
            alt.hconcat(*charts[3:]),
        )
    if n <= 9:
        return alt.vconcat(
            alt.hconcat(*charts[:3]),
            alt.hconcat(*charts[3:6]),
            alt.hconcat(*charts[6:]),
        )
    # More than 9: 3 columns max
    rows: list[Any] = []
    for i in range(0, n, 3):
        rows.append(alt.hconcat(*charts[i : i + 3]))
    return alt.vconcat(*rows)


def generate_gumbel_qq_subgrid(
    data_list: list[dict],
    mast_name: str,
    output_dir: Path,
    wind_speed_type: str,
) -> Path:
    """Generate a dynamic subgrid of Gumbel Q-Q plots.

    Args:
        data_list: List of dicts, each with keys ``height``, ``wind_data``,
            ``mu``, and ``beta``.
        mast_name: Mast identifier for the filename.
        output_dir: Directory where the PNG will be saved.
        wind_speed_type: Type of wind speed (e.g. "sustained" or "extreme").

    Returns:
        Path to the saved PNG file.
    """
    charts: list[alt.Chart] = []
    for item in data_list:
        chart = _build_single_qq_chart(
            wind_data=item["wind_data"],
            mu=item["mu"],
            beta=item["beta"],
            height=item["height"],
            width=250,
            height_px=250,
        )
        charts.append(chart)

    grid = _arrange_charts_in_subgrid(charts).properties(
        title=f"{mast_name} Gumbel Q-Q {wind_speed_type}"
    )

    content_hash = hashlib.md5(str(data_list).encode()).hexdigest()[:8]
    filename = (
        f"gumbel_qq_grid_{mast_name}_{wind_speed_type}_{content_hash}.png"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / filename

    png_bytes = vlc.vegalite_to_png(grid.to_dict(), scale=2.0)
    image_path.write_bytes(png_bytes)

    return image_path
