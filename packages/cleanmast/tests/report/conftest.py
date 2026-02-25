"""Fixtures for report module tests."""

from pathlib import Path
from typing import Any

import polars as pl
import pytest

from cleanmast.report.atom import ReportAtom
from cleanmast.report.atoms.single_mast.monthly_wind import SingleMastMonthlyWindAtom
from cleanmast.report.atoms.single_mast.monthly_wind_power import (
    SingleMastMonthlyWindPowerAtom,
)
from cleanmast.report.atoms.single_mast.schemas import (
    MonthlyWindPowerSchema,
    MonthlyWindSchema,
    WindRoseSchema,
)
from cleanmast.report.atoms.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.report.meta import SingleMastMeta


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for testing."""
    return tmp_path / "output"


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(
        mast_name="M01",
        air_density=1.225,
        caption="Test Caption",
        width="80%",
    )


@pytest.fixture
def sample_monthly_wind_df() -> pl.DataFrame:
    """Create sample monthly wind DataFrame for testing."""
    return pl.DataFrame({
        "month": [1, 1, 2, 2, 3, 3],
        "height": [80.0, 120.0, 80.0, 120.0, 80.0, 120.0],
        "interpolation_marker": [None, "外推", None, "外推", None, "外推"],
        "wind_speed_mean": [5.2, 5.8, 5.5, 6.1, 6.0, 6.8],
        "wind_speed_max": [8.1, 9.2, 8.5, 9.8, 9.0, 10.5],
        "wind_speed_min": [2.3, 2.8, 2.5, 3.1, 3.0, 3.5],
    })


@pytest.fixture
def sample_monthly_wind_power_df() -> pl.DataFrame:
    """Create sample monthly wind power DataFrame for testing."""
    return pl.DataFrame({
        "month": [1, 1, 2, 2, 3, 3],
        "height": [80.0, 120.0, 80.0, 120.0, 80.0, 120.0],
        "interpolation_marker": [None, "外推", None, "外推", None, "外推"],
        "wind_power_density": [150.5, 220.3, 180.2, 260.8, 200.5, 300.2],
        "air_density_used": [1.225, 1.225, 1.225, 1.225, 1.225, 1.225],
    })


@pytest.fixture
def sample_wind_rose_df() -> pl.DataFrame:
    """Create sample wind rose DataFrame for testing."""
    # Create data for 3 heights and 16 sectors
    sectors = list(range(16))
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    data: dict[str, list[Any]] = {
        "sector": [],
        "sector_name": [],
        "height": [],
        "interpolation_marker": [],
        "frequency": [],
        "wind_power_density": [],
    }
    
    # Generate data for heights 80m and 120m
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else ""
        for i, (sector, name) in enumerate(zip(sectors, sector_names)):
            # Create a distribution with peak at N (sector 0)
            freq = 0.2 if i == 0 else 0.05
            power = 300.0 if i == 0 else 100.0
            
            data["sector"].append(sector)
            data["sector_name"].append(name)
            data["height"].append(height)
            data["interpolation_marker"].append(marker if marker else None)
            data["frequency"].append(freq)
            data["wind_power_density"].append(power)
    
    return pl.DataFrame(data)


@pytest.fixture
def sample_wind_rose_with_null_power_df() -> pl.DataFrame:
    """Create wind rose DataFrame with null power density for testing."""
    sectors = list(range(16))
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    data: dict[str, list[Any]] = {
        "sector": [],
        "sector_name": [],
        "height": [],
        "interpolation_marker": [],
        "frequency": [],
        "wind_power_density": [],
    }
    
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else ""
        for i, (sector, name) in enumerate(zip(sectors, sector_names)):
            freq = 0.2 if i == 0 else 0.05
            # Make some power densities null for testing
            power = None if i > 8 else (300.0 if i == 0 else 100.0)
            
            data["sector"].append(sector)
            data["sector_name"].append(name)
            data["height"].append(height)
            data["interpolation_marker"].append(marker if marker else None)
            data["frequency"].append(freq)
            data["wind_power_density"].append(power)
    
    return pl.DataFrame(data)


@pytest.fixture
def monthly_wind_atom(
    sample_monthly_wind_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyWindAtom for testing."""
    return SingleMastMonthlyWindAtom.create(
        schema=MonthlyWindSchema,
        df=sample_monthly_wind_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_wind_power_atom(
    sample_monthly_wind_power_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyWindPowerAtom for testing."""
    return SingleMastMonthlyWindPowerAtom.create(
        schema=MonthlyWindPowerSchema,
        df=sample_monthly_wind_power_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_frequency_rose_atom(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyWindFrequencyRoseAtom for testing."""
    return SingleMastMonthlyWindFrequencyRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_atom(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindPowerRoseAtom for testing."""
    return SingleMastWindPowerRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_atom_null_power(
    sample_wind_rose_with_null_power_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindPowerRoseAtom with null power for testing."""
    return SingleMastWindPowerRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_with_null_power_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def all_atoms(
    monthly_wind_atom: Any,
    monthly_wind_power_atom: Any,
    wind_frequency_rose_atom: Any,
    wind_power_rose_atom: Any,
) -> list[ReportAtom[Any, Any]]:
    """Return a list of all atom types for testing."""
    return [
        monthly_wind_atom,
        monthly_wind_power_atom,
        wind_frequency_rose_atom,
        wind_power_rose_atom,
    ]
