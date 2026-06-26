"""Tests for wind rose section builder — reporting domain.

Ported from tests/assessment/wind_rose/test_wind_rose_section_builder.py.
Uses pure function `build_wind_rose_atoms()` instead of WindRoseSectionBuilder class.
Test logic preserved exactly.
"""

import polars as pl
import pytest
from cleanmast.subdomains.reporting.subdomains.wind_rose.assemble import (
    build_wind_rose_atoms,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_atom import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_grid_atom import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_power_grid_atom import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)


@pytest.fixture
def sample_wind_rose_df() -> pl.DataFrame:
    """Create sample wind rose DataFrame with WindRoseSchema columns."""
    return pl.DataFrame({
        "month": [1, 1, 2, 2],
        "month_name": ["1月", "1月", "2月", "2月"],
        "sector": [0, 1, 0, 1],
        "sector_name": ["N", "NNE", "N", "NNE"],
        "height": [100.0, 100.0, 100.0, 100.0],
        "interpolation_marker": [None, None, None, None],
        "frequency": [0.5, 0.3, 0.6, 0.2],
        "wind_power_density": [300.0, 150.0, 350.0, 120.0],
        "energy_frequency": [0.5, 0.3, 0.6, 0.2],
    })


class TestWindRoseSectionBuilder:
    """Tests for build_wind_rose_atoms()."""

    def test_build_returns_four_atoms(
        self,
        sample_wind_rose_df: pl.DataFrame,
    ) -> None:
        """Builder must return exactly 4 atoms."""
        atoms = build_wind_rose_atoms(mast_name="M01", df=sample_wind_rose_df)
        assert len(atoms) == 4

    def test_build_returns_correct_atom_types_in_order(
        self,
        sample_wind_rose_df: pl.DataFrame,
    ) -> None:
        """Builder must return 4 atoms in the prescribed order."""
        atoms = build_wind_rose_atoms(mast_name="M01", df=sample_wind_rose_df)

        expected_types = [
            SingleMastMonthlyWindFrequencyRoseAtom,
            SingleMastWindPowerRoseAtom,
            SingleMastMonthlyWindRoseGridAtom,
            SingleMastMonthlyWindPowerRoseGridAtom,
        ]

        for i, expected_type in enumerate(expected_types):
            assert isinstance(atoms[i], expected_type), (
                f"Atom at index {i} expected {expected_type.__name__}, "
                f"got {type(atoms[i]).__name__}"
            )

    def test_build_grid_atoms_receive_data(
        self,
        sample_wind_rose_df: pl.DataFrame,
    ) -> None:
        """Both grid atoms should receive the same DataFrame."""
        atoms = build_wind_rose_atoms(mast_name="M01", df=sample_wind_rose_df)

        freq_grid_atom = atoms[2]
        power_grid_atom = atoms[3]

        assert isinstance(freq_grid_atom, SingleMastMonthlyWindRoseGridAtom)
        assert isinstance(power_grid_atom, SingleMastMonthlyWindPowerRoseGridAtom)

        assert freq_grid_atom.df.equals(sample_wind_rose_df)
        assert power_grid_atom.df.equals(sample_wind_rose_df)

    def test_build_preserves_mast_name_in_meta(
        self,
        sample_wind_rose_df: pl.DataFrame,
    ) -> None:
        """Each atom's meta should contain the provided mast name."""
        atoms = build_wind_rose_atoms(mast_name="CustomMast", df=sample_wind_rose_df)

        for atom in atoms:
            assert atom.meta.mast_name == "CustomMast"
