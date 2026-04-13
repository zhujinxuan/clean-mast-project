"""Tests for Gumbel Q-Q plot service.

Tests cover Monte Carlo confidence band correctness, empirical coverage,
and dynamic subgrid PNG generation.
"""

from pathlib import Path

import numpy as np
import pytest
import scipy.stats
from cleanmast.subdomains.assessment.domain.services.calculators.gumbel_qq_plot_service import (
    generate_gumbel_qq_subgrid,
    generate_qq_monte_carlo_bands,
)

# =============================================================================
# Monte Carlo bands
# =============================================================================


def test_monte_carlo_band_correctness() -> None:
    """Bands should bracket theoretical quantiles and be monotonic."""
    mu = 10.0
    beta = 2.0
    n = 50
    empirical_probs = [i / (n + 1) for i in range(1, n + 1)]

    df = generate_qq_monte_carlo_bands(
        empirical_probs=empirical_probs,
        mu=mu,
        beta=beta,
        n=n,
        n_monte_carlo=500,
    )

    lower = df["lower"].to_list()
    quantiles = df["quantiles"].to_list()
    upper = df["upper"].to_list()

    assert len(lower) == n
    assert len(quantiles) == n
    assert len(upper) == n

    for lo, q, u in zip(lower, quantiles, upper):
        assert lo <= q
        assert q <= u
        assert lo <= u

    # Monotonicity
    assert all(lower[i] <= lower[i + 1] for i in range(n - 1))
    assert all(upper[i] <= upper[i + 1] for i in range(n - 1))
    assert all(quantiles[i] <= quantiles[i + 1] for i in range(n - 1))


def test_monte_carlo_coverage() -> None:
    """~95%% of empirical points from the true distribution should lie within bands."""
    rng = np.random.default_rng(42)
    mu = 10.0
    beta = 2.0
    n = 300

    sample = scipy.stats.gumbel_r(loc=mu, scale=beta).rvs(size=n, random_state=rng)
    sample.sort()

    empirical_probs = [i / (n + 1) for i in range(1, n + 1)]
    df = generate_qq_monte_carlo_bands(
        empirical_probs=empirical_probs,
        mu=mu,
        beta=beta,
        n=n,
        n_monte_carlo=800,
    )

    lower = np.array(df["lower"].to_list())
    upper = np.array(df["upper"].to_list())

    within_band = ((sample >= lower) & (sample <= upper)).sum()
    coverage = within_band / n

    assert 0.90 <= coverage <= 1.0


# =============================================================================
# Subgrid generation
# =============================================================================


def _make_data_list(n_heights: int, n_samples: int = 30) -> list[dict]:
    rng = np.random.default_rng(42 + n_heights)
    data_list: list[dict] = []
    for idx in range(n_heights):
        mu = 8.0 + idx * 0.5
        beta = 1.5
        wind_data = scipy.stats.gumbel_r(loc=mu, scale=beta).rvs(
            size=n_samples, random_state=rng
        ).tolist()
        data_list.append(
            {
                "height": 50.0 + idx * 20.0,
                "wind_data": wind_data,
                "mu": mu,
                "beta": beta,
            }
        )
    return data_list


@pytest.mark.parametrize("n_heights", [1, 2, 3, 4, 6])
def test_generate_gumbel_qq_subgrid(tmp_path: Path, n_heights: int) -> None:
    """Subgrid PNG should be created and non-empty for various height counts."""
    data_list = _make_data_list(n_heights)
    output_path = generate_gumbel_qq_subgrid(
        data_list=data_list,
        mast_name="M01",
        output_dir=tmp_path,
        wind_speed_type="sustained",
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert output_path.suffix == ".png"
