"""Gumbel Q-Q plot rendering — pure render-logic module.

Lives in model/ (pipeline bottom layer). Generates Gumbel Q-Q plots
with Monte Carlo confidence bands as PNG images via Altair + vl-convert.
Renders subgrid visualizations consumed by Method 2 atoms.

LOGIC-PRESERVATION: Ported from assessment entities/_gumbel_qq.py.
Resolves anti-pattern V6: IO-in-compute (gumbel_qq writes PNGs).
"""

import hashlib
import math
from pathlib import Path
from typing import TypedDict

import altair as alt
import numpy as np
import polars as pl
import scipy.stats
import vl_convert as vlc


class QQPoint(TypedDict):
    """A single Q-Q plot data point — consumed by Gumbel Q-Q subgrid rendering.

    Built from :class:`GumbelParameterSchema` rows in :class:`Method2QQSustainedAtom`
    / :class:`Method2QQExtremeAtom`.
    """

    height: float
    wind_data: list[float]
    mu: float
    beta: float


def generate_qq_monte_carlo_bands(
    empirical_probs: list[float],
    mu: float,
    beta: float,
    n: int,
    n_monte_carlo: int = 1000,
) -> pl.DataFrame:
    """Generate 95% confidence bands for Q-Q plot via Monte Carlo simulation.

    Returns Polars DataFrame with columns: probs, quantiles, lower, upper.
    """
    dist = scipy.stats.gumbel_r(loc=mu, scale=beta)
    probs_array = np.asarray(empirical_probs, dtype=float)
    n_probs = len(empirical_probs)

    simulated_quantiles = np.empty((n_probs, n_monte_carlo), dtype=float)

    for i in range(n_monte_carlo):
        sample = dist.rvs(size=n, random_state=None)
        sample.sort()

        indices = probs_array * (n - 1)
        lower_idx = np.floor(indices).astype(int)
        upper_idx = np.ceil(indices).astype(int)

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
) -> alt.LayerChart:
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
    """Generate a single Gumbel Q-Q plot with Monte Carlo confidence bands."""
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


def _arrange_charts_in_subgrid(
    charts: list[alt.LayerChart],
) -> alt.LayerChart | alt.HConcatChart | alt.VConcatChart:
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
    rows: list[alt.HConcatChart] = []
    for i in range(0, n, 3):
        rows.append(alt.hconcat(*charts[i : i + 3]))
    return alt.vconcat(*rows)


def generate_gumbel_qq_subgrid(
    data_list: list[QQPoint],
    mast_name: str,
    output_dir: Path,
    wind_speed_type: str,
) -> Path:
    """Generate a dynamic subgrid of Gumbel Q-Q plots."""
    charts: list[alt.LayerChart] = []
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
