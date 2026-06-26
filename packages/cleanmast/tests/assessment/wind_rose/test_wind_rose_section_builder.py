"""Tests for WindRoseSectionBuilder.

RED phase tests: Verify that WindRoseSectionBuilder returns exactly 4 atoms
of the correct types in the correct order.
"""

from datetime import datetime

import polars as pl
import pytest
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_atom import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_grid_atom import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_power_grid_atom import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.services._builder import (
    WindRoseSectionBuilder,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.value_objects.schemas import (
    WindRoseSchema,
)


@pytest.fixture
def sample_wind_rose_analysis_result() -> AnalysisResult[WindRoseSchema]:
    """Create a single AnalysisResult with WindRoseSchema data."""
    df = pl.DataFrame({
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
    metadata = AnalysisMetadata(
        mast_name="TestMast",
        time_range="2024-01-01 to 2024-02-01",
        created_at=datetime.now(),
    )
    return AnalysisResult.create(
        schema=WindRoseSchema,
        data=df,
        metadata=metadata,
    )


class TestWindRoseSectionBuilder:
    """Tests for WindRoseSectionBuilder.build()."""

    def test_build_returns_four_atoms(
        self,
        sample_wind_rose_analysis_result: AnalysisResult[WindRoseSchema],
    ) -> None:
        """Builder must return exactly 4 atoms."""
        builder = WindRoseSectionBuilder()
        atoms = builder.build(
            mast_name="M01",
            results=[sample_wind_rose_analysis_result],
        )
        assert len(atoms) == 4

    def test_build_returns_correct_atom_types_in_order(
        self,
        sample_wind_rose_analysis_result: AnalysisResult[WindRoseSchema],
    ) -> None:
        """Builder must return 4 atoms in the prescribed order."""
        builder = WindRoseSectionBuilder()
        atoms = builder.build(
            mast_name="M01",
            results=[sample_wind_rose_analysis_result],
        )

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

    def test_build_grid_atoms_receive_concatenated_data(
        self,
        sample_wind_rose_analysis_result: AnalysisResult[WindRoseSchema],
    ) -> None:
        """Both grid atoms should receive the same concatenated DataFrame."""
        builder = WindRoseSectionBuilder()
        atoms = builder.build(
            mast_name="M01",
            results=[sample_wind_rose_analysis_result],
        )

        freq_grid_atom = atoms[2]
        power_grid_atom = atoms[3]

        assert isinstance(freq_grid_atom, SingleMastMonthlyWindRoseGridAtom)
        assert isinstance(power_grid_atom, SingleMastMonthlyWindPowerRoseGridAtom)

        input_df = sample_wind_rose_analysis_result.data
        assert freq_grid_atom.df.equals(input_df)
        assert power_grid_atom.df.equals(input_df)

    def test_build_with_multiple_results_concatenates_data(
        self,
        sample_wind_rose_analysis_result: AnalysisResult[WindRoseSchema],
    ) -> None:
        """Builder concatenates multiple results before passing to atoms."""
        df2 = sample_wind_rose_analysis_result.data.with_columns(
            pl.lit(120.0).alias("height")
        )
        metadata2 = AnalysisMetadata(
            mast_name="TestMast",
            time_range="2024-01-01 to 2024-02-01",
            created_at=datetime.now(),
        )
        result2 = AnalysisResult.create(
            schema=WindRoseSchema,
            data=df2,
            metadata=metadata2,
        )

        builder = WindRoseSectionBuilder()
        atoms = builder.build(
            mast_name="M01",
            results=[sample_wind_rose_analysis_result, result2],
        )

        expected_df = pl.concat([
            sample_wind_rose_analysis_result.data,
            result2.data,
        ])

        assert atoms[2].df.equals(expected_df)
        assert atoms[3].df.equals(expected_df)

    def test_build_preserves_mast_name_in_meta(
        self,
        sample_wind_rose_analysis_result: AnalysisResult[WindRoseSchema],
    ) -> None:
        """Each atom's meta should contain the provided mast name."""
        builder = WindRoseSectionBuilder()
        atoms = builder.build(
            mast_name="CustomMast",
            results=[sample_wind_rose_analysis_result],
        )

        for atom in atoms:
            assert atom.meta.mast_name == "CustomMast"
