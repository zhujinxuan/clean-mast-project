"""Tests for wind frequency report atoms.

Tests cover all 4 wind frequency atoms:
- SingleMastWindFrequencyDistributionAtom
- SingleMastWindFrequencyTableAtom
- SingleMastWindPowerFrequencyTableAtom
- SingleMastWindRangeSummaryAtom
"""

from pathlib import Path
from typing import Any

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_distribution import (
    SingleMastWindFrequencyDistributionAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_table import (
    SingleMastWindFrequencyTableAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_power_frequency_table import (
    SingleMastWindPowerFrequencyTableAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_range_summary import (
    SingleMastWindRangeSummaryAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindFrequencySchema,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_wind_frequency_df_single() -> pl.DataFrame:
    """Create sample wind frequency data DataFrame with single height."""
    rows = []
    height = 100.0
    
    # Create bins from 0 to 28 m/s
    for bin_idx in range(29):
        bin_start = float(bin_idx)
        bin_end = float(bin_idx + 1) if bin_idx < 28 else 100.0
        bin_center = bin_start + 0.5
        
        # Simulate realistic Weibull-like distribution
        # Peak around 6-8 m/s, tapering off
        if bin_center < 6:
            freq = 0.02 + bin_center * 0.015
        elif bin_center < 10:
            freq = 0.12 - (bin_center - 8) * 0.01
        else:
            freq = max(0.02 - (bin_center - 10) * 0.002, 0.001)
        
        occurrence_hours = freq * 8760.0
        
        # Power frequency (peaks at higher speeds due to v³)
        power_factor = bin_center ** 3
        p_freq = freq * power_factor
        
        rows.append({
            "height": height,
            "interpolation_marker": None,
            "bin_start": bin_start,
            "bin_end": bin_end,
            "bin_center": bin_center,
            "frequency": freq,
            "occurrence_hours": occurrence_hours,
            "power_frequency": p_freq,
            "power_hours": p_freq * 8760.0,
        })
    
    # Normalize frequencies to sum to 1.0
    total_freq = sum(r["frequency"] for r in rows)
    total_power_freq = sum(r["power_frequency"] for r in rows)
    
    for r in rows:
        r["frequency"] = r["frequency"] / total_freq
        r["occurrence_hours"] = r["frequency"] * 8760.0
        r["power_frequency"] = r["power_frequency"] / total_power_freq
        r["power_hours"] = r["power_frequency"] * 8760.0
    
    return pl.DataFrame(rows)


@pytest.fixture
def sample_wind_frequency_df_multiple() -> pl.DataFrame:
    """Create sample wind frequency data DataFrame with multiple heights."""
    rows = []
    
    for height in [100.0, 120.0, 140.0]:
        marker = "外推" if height > 100 else None
        
        # Slightly different distributions per height (higher = more high-speed bins)
        speed_shift = (height - 100) * 0.02
        
        for bin_idx in range(29):
            bin_start = float(bin_idx)
            bin_end = float(bin_idx + 1) if bin_idx < 28 else 100.0
            bin_center = bin_start + 0.5
            
            # Distribution shifts to higher speeds with height
            effective_center = bin_center - speed_shift
            
            if effective_center < 6:
                freq = 0.02 + effective_center * 0.015
            elif effective_center < 10:
                freq = 0.12 - (effective_center - 8) * 0.01
            else:
                freq = max(0.02 - (effective_center - 10) * 0.002, 0.001)
            
            occurrence_hours = freq * 8760.0
            
            # Power frequency
            power_factor = bin_center ** 3
            p_freq = freq * power_factor
            
            rows.append({
                "height": height,
                "interpolation_marker": marker,
                "bin_start": bin_start,
                "bin_end": bin_end,
                "bin_center": bin_center,
                "frequency": freq,
                "occurrence_hours": occurrence_hours,
                "power_frequency": p_freq,
                "power_hours": p_freq * 8760.0,
            })
        
        # Normalize per height
        height_rows = [r for r in rows if r["height"] == height]
        total_freq = sum(r["frequency"] for r in height_rows)
        total_power_freq = sum(r["power_frequency"] for r in height_rows)
        
        for r in height_rows:
            r["frequency"] = r["frequency"] / total_freq
            r["occurrence_hours"] = r["frequency"] * 8760.0
            r["power_frequency"] = r["power_frequency"] / total_power_freq
            r["power_hours"] = r["power_frequency"] * 8760.0
    
    return pl.DataFrame(rows)


@pytest.fixture
def wind_frequency_distribution_atom(
    sample_wind_frequency_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindFrequencyDistributionAtom:
    """Create a SingleMastWindFrequencyDistributionAtom for testing."""
    return SingleMastWindFrequencyDistributionAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_multiple,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_frequency_table_atom(
    sample_wind_frequency_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindFrequencyTableAtom:
    """Create a SingleMastWindFrequencyTableAtom for testing."""
    return SingleMastWindFrequencyTableAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_multiple,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_frequency_table_atom(
    sample_wind_frequency_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindPowerFrequencyTableAtom:
    """Create a SingleMastWindPowerFrequencyTableAtom for testing."""
    return SingleMastWindPowerFrequencyTableAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_multiple,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_range_summary_atom(
    sample_wind_frequency_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindRangeSummaryAtom:
    """Create a SingleMastWindRangeSummaryAtom for testing."""
    return SingleMastWindRangeSummaryAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df_multiple,
        meta=sample_mast_meta,
    )


# =============================================================================
# Test SingleMastWindFrequencyDistributionAtom
# =============================================================================


class TestSingleMastWindFrequencyDistributionAtom:
    """Tests for SingleMastWindFrequencyDistributionAtom."""

    def test_render_image(
        self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom,
        tmp_path: Path
    ) -> None:
        """Test renderImage creates a PNG file with grouped bar chart."""
        image_path = wind_frequency_distribution_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom) -> None:
        """Test renderTable returns empty string (chart only)."""
        table = wind_frequency_distribution_atom.renderTable()
        
        # Distribution atom returns empty table (chart only)
        assert table == ""

    def test_render_summary(self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = wind_frequency_distribution_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "M01" in summary
        assert "风频" in summary or "风能" in summary

    def test_content_hash_consistency(
        self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_frequency_distribution_atom.get_or_compute_df_hashkey()
        hash2 = wind_frequency_distribution_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWindFrequencyDistributionAtom_" in hash1

    def test_summary_has_distribution_analysis(
        self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom
    ) -> None:
        """Test summary includes distribution analysis."""
        summary = wind_frequency_distribution_atom.renderSummary()
        
        # Should contain statistical information
        assert "风速频率峰值" in summary
        assert "风能频率峰值" in summary
        assert "平均风速" in summary

    def test_summary_has_multiple_heights(
        self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom
    ) -> None:
        """Test summary includes analysis for all heights."""
        summary = wind_frequency_distribution_atom.renderSummary()
        
        # Should mention all heights
        assert "100m" in summary
        assert "120m" in summary
        assert "140m" in summary

    def test_single_height_render_image(
        self, sample_wind_frequency_df_single: pl.DataFrame,
        sample_mast_meta: SingleMastMeta,
        tmp_path: Path
    ) -> None:
        """Test renderImage with single height data."""
        atom = SingleMastWindFrequencyDistributionAtom.create(
            schema=WindFrequencySchema,
            df=sample_wind_frequency_df_single,
            meta=sample_mast_meta,
        )
        
        image_path = atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"


# =============================================================================
# Test SingleMastWindFrequencyTableAtom
# =============================================================================


class TestSingleMastWindFrequencyTableAtom:
    """Tests for SingleMastWindFrequencyTableAtom."""

    def test_render_image(
        self, wind_frequency_table_atom: SingleMastWindFrequencyTableAtom, tmp_path: Path
    ) -> None:
        """Test renderImage returns empty Path (no image for table)."""
        image_path = wind_frequency_table_atom.renderImage(tmp_path)
        
        # Table atom returns empty Path (no image generation)
        assert image_path == Path()

    def test_render_table(self, wind_frequency_table_atom: SingleMastWindFrequencyTableAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = wind_frequency_table_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "风速(m/s)" in table
        assert "合计" in table

    def test_render_summary(self, wind_frequency_table_atom: SingleMastWindFrequencyTableAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = wind_frequency_table_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "风速频率分布" in summary

    def test_content_hash_consistency(
        self, wind_frequency_table_atom: SingleMastWindFrequencyTableAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_frequency_table_atom.get_or_compute_df_hashkey()
        hash2 = wind_frequency_table_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWindFrequencyTableAtom_" in hash1

    def test_table_has_all_heights(
        self, wind_frequency_table_atom: SingleMastWindFrequencyTableAtom
    ) -> None:
        """Test table includes all heights."""
        table = wind_frequency_table_atom.renderTable()
        
        assert "100m" in table
        assert "120m" in table
        assert "140m" in table

    def test_table_has_frequency_percentages(
        self, wind_frequency_table_atom: SingleMastWindFrequencyTableAtom
    ) -> None:
        """Test table includes frequency as percentages."""
        table = wind_frequency_table_atom.renderTable()
        
        # Should have percentage signs
        assert "%" in table

    def test_table_has_total_row(
        self, wind_frequency_table_atom: SingleMastWindFrequencyTableAtom
    ) -> None:
        """Test table includes total row."""
        table = wind_frequency_table_atom.renderTable()
        
        assert "合计" in table


# =============================================================================
# Test SingleMastWindPowerFrequencyTableAtom
# =============================================================================


class TestSingleMastWindPowerFrequencyTableAtom:
    """Tests for SingleMastWindPowerFrequencyTableAtom."""

    def test_render_image(
        self, wind_power_frequency_table_atom: SingleMastWindPowerFrequencyTableAtom,
        tmp_path: Path
    ) -> None:
        """Test renderImage returns empty Path (no image for table)."""
        image_path = wind_power_frequency_table_atom.renderImage(tmp_path)
        
        # Power frequency table atom returns empty Path
        assert image_path == Path()

    def test_render_table(self, wind_power_frequency_table_atom: SingleMastWindPowerFrequencyTableAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = wind_power_frequency_table_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "风速(m/s)" in table

    def test_render_summary(self, wind_power_frequency_table_atom: SingleMastWindPowerFrequencyTableAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = wind_power_frequency_table_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "风能频率" in summary

    def test_content_hash_consistency(
        self, wind_power_frequency_table_atom: SingleMastWindPowerFrequencyTableAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_power_frequency_table_atom.get_or_compute_df_hashkey()
        hash2 = wind_power_frequency_table_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWindPowerFrequencyTableAtom_" in hash1

    def test_summary_has_energy_analysis(
        self, wind_power_frequency_table_atom: SingleMastWindPowerFrequencyTableAtom
    ) -> None:
        """Test summary includes energy distribution analysis."""
        summary = wind_power_frequency_table_atom.renderSummary()
        
        # Should mention energy contribution
        assert "能量贡献" in summary
        assert "有效风速" in summary

    def test_summary_has_v3_explanation(
        self, wind_power_frequency_table_atom: SingleMastWindPowerFrequencyTableAtom
    ) -> None:
        """Test summary explains v³ relationship."""
        summary = wind_power_frequency_table_atom.renderSummary()
        
        # Should mention cubic relationship
        assert "三次方" in summary or "v³" in summary


# =============================================================================
# Test SingleMastWindRangeSummaryAtom
# =============================================================================


class TestSingleMastWindRangeSummaryAtom:
    """Tests for SingleMastWindRangeSummaryAtom."""

    def test_render_image(
        self, wind_range_summary_atom: SingleMastWindRangeSummaryAtom, tmp_path: Path
    ) -> None:
        """Test renderImage returns empty Path (no image for summary)."""
        image_path = wind_range_summary_atom.renderImage(tmp_path)
        
        # Range summary atom returns empty Path
        assert image_path == Path()

    def test_render_table(self, wind_range_summary_atom: SingleMastWindRangeSummaryAtom) -> None:
        """Test renderTable returns non-empty Typst summary table."""
        table = wind_range_summary_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "高度" in table
        assert "3-25m/s频率" in table
        assert "3-25m/s小时数" in table
        assert "风能频率" in table
        assert "风能小时数" in table

    def test_render_summary(self, wind_range_summary_atom: SingleMastWindRangeSummaryAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = wind_range_summary_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "有效风速区间" in summary
        assert "3-25m/s" in summary

    def test_content_hash_consistency(
        self, wind_range_summary_atom: SingleMastWindRangeSummaryAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_range_summary_atom.get_or_compute_df_hashkey()
        hash2 = wind_range_summary_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWindRangeSummaryAtom_" in hash1

    def test_table_has_all_heights(
        self, wind_range_summary_atom: SingleMastWindRangeSummaryAtom
    ) -> None:
        """Test table includes all heights."""
        table = wind_range_summary_atom.renderTable()
        
        assert "100m" in table
        assert "120m" in table
        assert "140m" in table

    def test_summary_has_productivity_assessment(
        self, wind_range_summary_atom: SingleMastWindRangeSummaryAtom
    ) -> None:
        """Test summary includes productivity assessment."""
        summary = wind_range_summary_atom.renderSummary()
        
        # Should have resource level assessment
        assert "资源等级" in summary or "评定" in summary

    def test_summary_has_best_height(
        self, wind_range_summary_atom: SingleMastWindRangeSummaryAtom
    ) -> None:
        """Test summary identifies best height."""
        summary = wind_range_summary_atom.renderSummary()
        
        # Should mention optimal height
        assert "最优高度" in summary


# =============================================================================
# Cross-cutting Tests
# =============================================================================


class TestAllWindFrequencyAtoms:
    """Tests that apply to all wind frequency atoms."""

    @pytest.fixture
    def all_wind_frequency_atoms(
        self,
        wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom,
        wind_frequency_table_atom: SingleMastWindFrequencyTableAtom,
        wind_power_frequency_table_atom: SingleMastWindPowerFrequencyTableAtom,
        wind_range_summary_atom: SingleMastWindRangeSummaryAtom,
    ) -> list[Any]:
        """Return a list of all wind frequency atom types for testing."""
        return [
            wind_frequency_distribution_atom,
            wind_frequency_table_atom,
            wind_power_frequency_table_atom,
            wind_range_summary_atom,
        ]

    def test_all_atoms_have_mast_name(self, all_wind_frequency_atoms: list[Any]) -> None:
        """Verify all atoms have correct mast name in meta."""
        for atom in all_wind_frequency_atoms:
            assert atom.meta.mast_name == "M01"

    def test_all_atoms_have_consistent_hashes(self, all_wind_frequency_atoms: list[Any]) -> None:
        """Verify all atoms produce consistent hashes."""
        for atom in all_wind_frequency_atoms:
            hash1 = atom.get_or_compute_df_hashkey()
            hash2 = atom.get_or_compute_df_hashkey()
            assert hash1 == hash2
            assert len(hash1) > 0

    def test_summary_output_is_string(self, all_wind_frequency_atoms: list[Any]) -> None:
        """Verify all atoms return string from renderSummary."""
        for atom in all_wind_frequency_atoms:
            summary = atom.renderSummary()
            assert isinstance(summary, str)
            assert len(summary) > 0


class TestImageCaching:
    """Tests for image caching behavior."""

    def test_distribution_image_caching(
        self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom,
        tmp_path: Path
    ) -> None:
        """Verify distribution images are cached."""
        # First render
        path1 = wind_frequency_distribution_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = wind_frequency_distribution_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2  # File not modified

    def test_distribution_force_regenerate(
        self, wind_frequency_distribution_atom: SingleMastWindFrequencyDistributionAtom,
        tmp_path: Path
    ) -> None:
        """Verify force=True regenerates distribution images."""
        # First render
        path1 = wind_frequency_distribution_atom.renderImage(tmp_path)
        
        # Force regenerate
        path2 = wind_frequency_distribution_atom.renderImage(tmp_path, force=True)
        
        assert path1 == path2
        assert path2.exists()


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_single_row_data(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test atoms with single row of data."""
        single_row_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "bin_start": [5.0],
            "bin_end": [6.0],
            "bin_center": [5.5],
            "frequency": [1.0],
            "occurrence_hours": [8760.0],
            "power_frequency": [1.0],
            "power_hours": [8760.0],
        })
        
        atom = SingleMastWindFrequencyTableAtom.create(
            schema=WindFrequencySchema,
            df=single_row_df,
            meta=sample_mast_meta,
        )
        
        table = atom.renderTable()
        assert "100m" in table
        
        summary = atom.renderSummary()
        assert isinstance(summary, str)

    def test_frequency_sum_constraint(
        self, sample_wind_frequency_df_single: pl.DataFrame
    ) -> None:
        """Test that frequency sums to 1.0."""
        total_freq = sample_wind_frequency_df_single["frequency"].sum()
        assert total_freq == pytest.approx(1.0, abs=0.01)

    def test_power_frequency_sum_constraint(
        self, sample_wind_frequency_df_single: pl.DataFrame
    ) -> None:
        """Test that power frequency sums to 1.0."""
        total_power_freq = sample_wind_frequency_df_single["power_frequency"].sum()
        assert total_power_freq == pytest.approx(1.0, abs=0.01)

    def test_occurrence_hours_calculation(
        self, sample_wind_frequency_df_single: pl.DataFrame
    ) -> None:
        """Test that occurrence_hours = frequency * 8760."""
        for row in sample_wind_frequency_df_single.iter_rows(named=True):
            expected_hours = row["frequency"] * 8760.0
            assert row["occurrence_hours"] == pytest.approx(expected_hours, abs=0.1)

    def test_power_hours_calculation(
        self, sample_wind_frequency_df_single: pl.DataFrame
    ) -> None:
        """Test that power_hours = power_frequency * 8760."""
        for row in sample_wind_frequency_df_single.iter_rows(named=True):
            expected_hours = row["power_frequency"] * 8760.0
            assert row["power_hours"] == pytest.approx(expected_hours, abs=0.1)

    @pytest.mark.xfail(reason="Empty dataframe handling not yet implemented in atoms")
    def test_empty_dataframe(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test wind frequency atoms with empty DataFrame."""
        empty_df = pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "bin_start": pl.Series([], dtype=pl.Float64),
            "bin_end": pl.Series([], dtype=pl.Float64),
            "bin_center": pl.Series([], dtype=pl.Float64),
            "frequency": pl.Series([], dtype=pl.Float64),
            "occurrence_hours": pl.Series([], dtype=pl.Float64),
            "power_frequency": pl.Series([], dtype=pl.Float64),
            "power_hours": pl.Series([], dtype=pl.Float64),
        })
        
        atom = SingleMastWindFrequencyTableAtom.create(
            schema=WindFrequencySchema,
            df=empty_df,
            meta=sample_mast_meta,
        )
        
        table = atom.renderTable()
        assert isinstance(table, str)
        
        summary = atom.renderSummary()
        assert isinstance(summary, str)
