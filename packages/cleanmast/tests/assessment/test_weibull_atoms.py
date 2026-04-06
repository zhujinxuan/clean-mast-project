"""Tests for Weibull report atoms.

Tests cover all 3 Weibull atoms:
- SingleMastWeibullParametersAtom
- SingleMastWeibullDistributionAtom
- SingleMastWeibullMultiHeightAtom
"""

from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_distribution import (
    SingleMastWeibullDistributionAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_multi import (
    SingleMastWeibullMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_parameters import (
    SingleMastWeibullParametersAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WeibullSchema,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_weibull_df_single() -> pl.DataFrame:
    """Create sample Weibull data DataFrame with single height."""
    np.random.seed(42)
    shape_k, scale_c = 2.0, 8.0
    wind_speeds = scale_c * np.random.weibull(shape_k, 1000)
    
    # Calculate histogram bins
    max_speed = float(np.max(wind_speeds))
    bin_edges = np.arange(0, int(max_speed) + 2, 1.0)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    observed_counts, _ = np.histogram(wind_speeds, bins=bin_edges)
    observed_density = observed_counts / (len(wind_speeds) * 1.0)
    
    # Calculate fitted density (simplified)
    fitted_density = observed_density * 0.95 + np.random.uniform(0, 0.001, len(observed_density))
    
    mean_speed = float(np.mean(wind_speeds))
    
    return pl.DataFrame({
        "height": [100.0],
        "interpolation_marker": [None],
        "shape_k": [shape_k],
        "scale_c": [scale_c],
        "mean_speed": [mean_speed],
        "bin_centers": [bin_centers.tolist()],
        "observed_density": [observed_density.tolist()],
        "fitted_density": [fitted_density.tolist()],
    })


@pytest.fixture
def sample_weibull_df_multiple() -> pl.DataFrame:
    """Create sample Weibull data DataFrame with multiple heights."""
    np.random.seed(42)
    
    rows = []
    for height, shape_k, scale_c in [(100.0, 2.0, 8.0), (120.0, 2.2, 9.0)]:
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)
        
        max_speed = float(np.max(wind_speeds))
        bin_edges = np.arange(0, int(max_speed) + 2, 1.0)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        observed_counts, _ = np.histogram(wind_speeds, bins=bin_edges)
        observed_density = observed_counts / (len(wind_speeds) * 1.0)
        fitted_density = observed_density * 0.95
        
        mean_speed = float(np.mean(wind_speeds))
        marker = "外推" if height > 100 else None
        
        rows.append({
            "height": height,
            "interpolation_marker": marker,
            "shape_k": shape_k,
            "scale_c": scale_c,
            "mean_speed": mean_speed,
            "bin_centers": bin_centers.tolist(),
            "observed_density": observed_density.tolist(),
            "fitted_density": fitted_density.tolist(),
        })
    
    return pl.DataFrame(rows)


@pytest.fixture
def sample_weibull_df_three_heights() -> pl.DataFrame:
    """Create sample Weibull data DataFrame with three heights for multi-atom."""
    np.random.seed(42)
    
    rows = []
    for height, shape_k, scale_c in [(80.0, 1.8, 7.0), (100.0, 2.0, 8.0), (120.0, 2.2, 9.0)]:
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)
        
        max_speed = float(np.max(wind_speeds))
        bin_edges = np.arange(0, int(max_speed) + 2, 1.0)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        observed_counts, _ = np.histogram(wind_speeds, bins=bin_edges)
        observed_density = observed_counts / (len(wind_speeds) * 1.0)
        fitted_density = observed_density * 0.95
        
        mean_speed = float(np.mean(wind_speeds))
        marker = "外推" if height > 100 else None
        
        rows.append({
            "height": height,
            "interpolation_marker": marker,
            "shape_k": shape_k,
            "scale_c": scale_c,
            "mean_speed": mean_speed,
            "bin_centers": bin_centers.tolist(),
            "observed_density": observed_density.tolist(),
            "fitted_density": fitted_density.tolist(),
        })
    
    return pl.DataFrame(rows)


@pytest.fixture
def weibull_parameters_atom(
    sample_weibull_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWeibullParametersAtom:
    """Create a SingleMastWeibullParametersAtom for testing."""
    return SingleMastWeibullParametersAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df_multiple,
        meta=sample_mast_meta,
    )


@pytest.fixture
def weibull_distribution_atom(
    sample_weibull_df_single: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWeibullDistributionAtom:
    """Create a SingleMastWeibullDistributionAtom for testing."""
    return SingleMastWeibullDistributionAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df_single,
        meta=sample_mast_meta,
    )


@pytest.fixture
def weibull_distribution_multi_atom(
    sample_weibull_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWeibullDistributionAtom:
    """Create a SingleMastWeibullDistributionAtom with multiple heights."""
    return SingleMastWeibullDistributionAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df_multiple,
        meta=sample_mast_meta,
    )


@pytest.fixture
def weibull_multi_height_atom(
    sample_weibull_df_three_heights: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWeibullMultiHeightAtom:
    """Create a SingleMastWeibullMultiHeightAtom for testing."""
    return SingleMastWeibullMultiHeightAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df_three_heights,
        meta=sample_mast_meta,
    )


# =============================================================================
# Test SingleMastWeibullParametersAtom
# =============================================================================


class TestSingleMastWeibullParametersAtom:
    """Tests for SingleMastWeibullParametersAtom."""

    def test_render_image(self, weibull_parameters_atom: SingleMastWeibullParametersAtom, tmp_path: Path) -> None:
        """Test renderImage returns empty Path for parameters atom."""
        image_path = weibull_parameters_atom.renderImage(tmp_path)
        
        # Parameters atom returns empty Path (no image generation)
        assert image_path == Path()

    def test_render_table(self, weibull_parameters_atom: SingleMastWeibullParametersAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = weibull_parameters_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "高度" in table
        assert "形状参数k" in table
        assert "尺度参数c" in table
        assert "平均风速" in table

    def test_render_summary(self, weibull_parameters_atom: SingleMastWeibullParametersAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = weibull_parameters_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "Weibull" in summary or "形状参数" in summary

    def test_content_hash_consistency(self, weibull_parameters_atom: SingleMastWeibullParametersAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = weibull_parameters_atom.get_or_compute_df_hashkey()
        hash2 = weibull_parameters_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWeibullParametersAtom_" in hash1

    def test_table_has_multiple_heights(self, weibull_parameters_atom: SingleMastWeibullParametersAtom) -> None:
        """Test table includes all heights from data."""
        table = weibull_parameters_atom.renderTable()
        
        # Should have entries for both heights
        assert "100m" in table
        assert "120m" in table
        assert "外推" in table  # 120m has interpolation marker

    def test_summary_has_statistics(self, weibull_parameters_atom: SingleMastWeibullParametersAtom) -> None:
        """Test summary includes statistical analysis."""
        summary = weibull_parameters_atom.renderSummary()
        
        # Should contain statistical information
        assert "形状参数k" in summary
        assert "尺度参数c" in summary
        assert "平均风速" in summary


# =============================================================================
# Test SingleMastWeibullDistributionAtom
# =============================================================================


class TestSingleMastWeibullDistributionAtom:
    """Tests for SingleMastWeibullDistributionAtom."""

    def test_render_image(self, weibull_distribution_atom: SingleMastWeibullDistributionAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file."""
        image_path = weibull_distribution_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_image_multiple_heights(
        self, weibull_distribution_multi_atom: SingleMastWeibullDistributionAtom, tmp_path: Path
    ) -> None:
        """Test renderImage creates PNG with multiple heights."""
        image_path = weibull_distribution_multi_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, weibull_distribution_atom: SingleMastWeibullDistributionAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = weibull_distribution_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "高度" in table
        assert "形状参数k" in table
        assert "尺度参数c" in table

    def test_render_summary(self, weibull_distribution_atom: SingleMastWeibullDistributionAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = weibull_distribution_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "Weibull" in summary

    def test_content_hash_consistency(self, weibull_distribution_atom: SingleMastWeibullDistributionAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = weibull_distribution_atom.get_or_compute_df_hashkey()
        hash2 = weibull_distribution_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWeibullDistributionAtom_" in hash1

    def test_summary_includes_fit_quality(self, weibull_distribution_atom: SingleMastWeibullDistributionAtom) -> None:
        """Test summary includes fit quality metrics."""
        summary = weibull_distribution_atom.renderSummary()
        
        # Should mention RMSE or fit quality
        assert "RMSE" in summary or "拟合" in summary

    def test_summary_includes_distribution_type(self, weibull_distribution_atom: SingleMastWeibullDistributionAtom) -> None:
        """Test summary includes distribution type description."""
        summary = weibull_distribution_atom.renderSummary()
        
        # Should describe the distribution type based on k value
        assert any(term in summary for term in ["分布", "正态", "瑞利", "偏态"])


# =============================================================================
# Test SingleMastWeibullMultiHeightAtom
# =============================================================================


class TestSingleMastWeibullMultiHeightAtom:
    """Tests for SingleMastWeibullMultiHeightAtom."""

    def test_render_image(self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file with multi-height curves."""
        image_path = weibull_multi_height_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = weibull_multi_height_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "高度" in table
        assert "形状参数k" in table
        assert "平均风速" in table

    def test_render_summary(self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = weibull_multi_height_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "多高度" in summary or "高度" in summary

    def test_content_hash_consistency(self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = weibull_multi_height_atom.get_or_compute_df_hashkey()
        hash2 = weibull_multi_height_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastWeibullMultiHeightAtom_" in hash1

    def test_table_has_all_heights(self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom) -> None:
        """Test table includes all three heights."""
        table = weibull_multi_height_atom.renderTable()
        
        assert "80m" in table
        assert "100m" in table
        assert "120m" in table

    def test_summary_has_figure_reference(self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom) -> None:
        """Test summary includes figure reference."""
        summary = weibull_multi_height_atom.renderSummary()
        
        assert "@fig-" in summary

    def test_summary_compares_heights(self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom) -> None:
        """Test summary compares parameters across heights."""
        summary = weibull_multi_height_atom.renderSummary()
        
        # Should compare shape and scale parameters
        assert "形状参数" in summary
        assert "尺度参数" in summary


# =============================================================================
# Cross-cutting Tests
# =============================================================================


class TestAllWeibullAtoms:
    """Tests that apply to all Weibull atoms."""

    @pytest.fixture
    def all_weibull_atoms(
        self,
        weibull_parameters_atom: SingleMastWeibullParametersAtom,
        weibull_distribution_atom: SingleMastWeibullDistributionAtom,
        weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom,
    ) -> list[Any]:
        """Return a list of all Weibull atom types for testing."""
        return [
            weibull_parameters_atom,
            weibull_distribution_atom,
            weibull_multi_height_atom,
        ]

    def test_all_atoms_have_mast_name(self, all_weibull_atoms: list[Any]) -> None:
        """Verify all atoms have correct mast name in meta."""
        for atom in all_weibull_atoms:
            assert atom.meta.mast_name == "M01"

    def test_all_atoms_produce_non_empty_tables(self, all_weibull_atoms: list[Any]) -> None:
        """Verify all atoms produce non-empty tables."""
        for atom in all_weibull_atoms:
            table = atom.renderTable()
            assert isinstance(table, str)
            assert len(table) > 0
            assert "#table(" in table

    def test_all_atoms_produce_chinese_summaries(self, all_weibull_atoms: list[Any]) -> None:
        """Verify all atoms produce Chinese summaries."""
        for atom in all_weibull_atoms:
            summary = atom.renderSummary()
            assert isinstance(summary, str)
            assert len(summary) > 0
            # Should contain Chinese characters
            assert any("\u4e00" <= char <= "\u9fff" for char in summary)

    def test_all_atoms_have_consistent_hashes(self, all_weibull_atoms: list[Any]) -> None:
        """Verify all atoms produce consistent hashes."""
        for atom in all_weibull_atoms:
            hash1 = atom.get_or_compute_df_hashkey()
            hash2 = atom.get_or_compute_df_hashkey()
            assert hash1 == hash2
            assert len(hash1) > 0

    def test_table_caching(self, all_weibull_atoms: list[Any]) -> None:
        """Verify table output is consistent across multiple calls."""
        for atom in all_weibull_atoms:
            table1 = atom.renderTable()
            table2 = atom.renderTable()
            assert table1 == table2

    def test_summary_caching(self, all_weibull_atoms: list[Any]) -> None:
        """Verify summary output is consistent across multiple calls."""
        for atom in all_weibull_atoms:
            summary1 = atom.renderSummary()
            summary2 = atom.renderSummary()
            assert summary1 == summary2


class TestImageCaching:
    """Tests for image caching behavior."""

    def test_distribution_image_caching(
        self, weibull_distribution_atom: SingleMastWeibullDistributionAtom, tmp_path: Path
    ) -> None:
        """Verify distribution images are cached."""
        # First render
        path1 = weibull_distribution_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = weibull_distribution_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2  # File not modified

    def test_multi_height_image_caching(
        self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom, tmp_path: Path
    ) -> None:
        """Verify multi-height images are cached."""
        # First render
        path1 = weibull_multi_height_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = weibull_multi_height_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2

    def test_distribution_force_regenerate(
        self, weibull_distribution_atom: SingleMastWeibullDistributionAtom, tmp_path: Path
    ) -> None:
        """Verify force=True regenerates distribution images."""
        # First render
        path1 = weibull_distribution_atom.renderImage(tmp_path)
        
        # Force regenerate
        path2 = weibull_distribution_atom.renderImage(tmp_path, force=True)
        
        assert path1 == path2
        assert path2.exists()

    def test_multi_height_force_regenerate(
        self, weibull_multi_height_atom: SingleMastWeibullMultiHeightAtom, tmp_path: Path
    ) -> None:
        """Verify force=True regenerates multi-height images."""
        # First render
        path1 = weibull_multi_height_atom.renderImage(tmp_path)
        
        # Force regenerate
        path2 = weibull_multi_height_atom.renderImage(tmp_path, force=True)
        
        assert path1 == path2
        assert path2.exists()
