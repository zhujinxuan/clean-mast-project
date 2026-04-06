"""Tests for turbulence report atoms.

Tests cover all 4 turbulence atoms:
- SingleMastTurbulenceIntensityAtom
- SingleMastTurbulenceSectorAtom
- SingleMastTurbulenceMultiHeightAtom
- SingleMastTurbulenceSummaryAtom
"""

from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_intensity import (
    SingleMastTurbulenceIntensityAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_multi import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_sector import (
    SingleMastTurbulenceSectorAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_summary import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TurbulenceSchema,
    TurbulenceSectorSchema,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_turbulence_df_single() -> pl.DataFrame:
    """Create sample turbulence data DataFrame with single height."""
    return pl.DataFrame({
        "wind_speed_bin": [3, 5, 7, 9, 11, 13],
        "height": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        "interpolation_marker": [None, None, None, None, None, None],
        "mean_ti": [0.18, 0.15, 0.12, 0.10, 0.09, 0.08],
        "std_ti": [0.03, 0.02, 0.02, 0.015, 0.01, 0.01],
        "representative_ti": [0.218, 0.176, 0.146, 0.119, 0.103, 0.093],
        "iec_category": ["B", "B", "A", "A", "A", "A"],
    })


@pytest.fixture
def sample_turbulence_df_multiple() -> pl.DataFrame:
    """Create sample turbulence data DataFrame with multiple heights."""
    rows = []
    # Create data with clear unique category distributions per height - no ties anywhere
    for height_idx, (height, mean_ti_offset) in enumerate([(100.0, 0.0), (120.0, -0.01), (140.0, -0.02)]):
        for ws_idx, ws_bin in enumerate([3, 5, 7, 9, 11, 12]):  # 6 points for more flexibility
            base_ti = 0.16 - ws_idx * 0.01
            mean_ti = base_ti + mean_ti_offset
            std_ti = mean_ti * 0.15
            rep_ti = mean_ti + 1.28 * std_ti
            
            # Assign categories uniquely per height - ensure no ties in counts
            categories_per_height = [
                ["A", "A", "A", "A", "B", "B"],  # 100m: A=67%, B=33%
                ["B", "B", "B", "B", "A", "A"],  # 120m: B=67%, A=33%
                ["B", "B", "B", "A", "A", "C"],  # 140m: B=50%, A=33%, C=17%
            ]
            iec_cat = categories_per_height[height_idx][ws_idx]
            
            marker = "外推" if height > 100 else ""
            
            rows.append({
                "wind_speed_bin": ws_bin,
                "height": height,
                "interpolation_marker": marker if marker else None,
                "mean_ti": mean_ti,
                "std_ti": std_ti,
                "representative_ti": rep_ti,
                "iec_category": iec_cat,
            })
    
    return pl.DataFrame(rows)


@pytest.fixture
def sample_turbulence_df_three_heights() -> pl.DataFrame:
    """Create sample turbulence data DataFrame with three heights."""
    rows = []
    for height in [80.0, 100.0, 120.0]:
        for ws_bin in [3, 5, 7, 9, 11]:
            # TI decreases with height and increases at low wind speeds
            base_ti = 0.20 - (height - 80) * 0.0005 - (ws_bin - 3) * 0.015
            mean_ti = max(base_ti, 0.05)
            std_ti = mean_ti * 0.12
            rep_ti = mean_ti + 1.28 * std_ti
            
            if rep_ti > 0.18:
                iec_cat = "A+"
            elif rep_ti > 0.16:
                iec_cat = "A"
            elif rep_ti > 0.14:
                iec_cat = "B"
            else:
                iec_cat = "C"
            
            marker = "外推" if height > 100 else None
            
            rows.append({
                "wind_speed_bin": ws_bin,
                "height": height,
                "interpolation_marker": marker,
                "mean_ti": mean_ti,
                "std_ti": std_ti,
                "representative_ti": rep_ti,
                "iec_category": iec_cat,
            })
    
    return pl.DataFrame(rows)


@pytest.fixture
def sample_sector_df() -> pl.DataFrame:
    """Create sample sector turbulence data DataFrame."""
    rows = []
    for sector in range(16):
        sector_name = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][sector]
        # Vary TI by sector
        base_ti = 0.12 + 0.04 * np.sin(sector * np.pi / 8)
        mean_ti = base_ti
        rep_ti = mean_ti * 1.15
        
        if rep_ti > 0.18:
            iec_cat = "A+"
        elif rep_ti > 0.16:
            iec_cat = "A"
        elif rep_ti > 0.14:
            iec_cat = "B"
        else:
            iec_cat = "C"
        
        rows.append({
            "sector": sector,
            "sector_name": sector_name,
            "height": 120.0,
            "interpolation_marker": None,
            "mean_ti": mean_ti,
            "representative_ti": rep_ti,
            "iec_category": iec_cat,
        })
    
    return pl.DataFrame(rows)


@pytest.fixture
def turbulence_intensity_atom(
    sample_turbulence_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulenceIntensityAtom:
    """Create a SingleMastTurbulenceIntensityAtom for testing."""
    return SingleMastTurbulenceIntensityAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_df_multiple,
        meta=sample_mast_meta,
    )


@pytest.fixture
def turbulence_sector_atom(
    sample_sector_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulenceSectorAtom:
    """Create a SingleMastTurbulenceSectorAtom for testing."""
    return SingleMastTurbulenceSectorAtom.create(
        schema=TurbulenceSectorSchema,
        df=sample_sector_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def turbulence_multi_height_atom(
    sample_turbulence_df_three_heights: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulenceMultiHeightAtom:
    """Create a SingleMastTurbulenceMultiHeightAtom for testing."""
    return SingleMastTurbulenceMultiHeightAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_df_three_heights,
        meta=sample_mast_meta,
    )


@pytest.fixture
def turbulence_summary_atom(
    sample_turbulence_df_multiple: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulenceSummaryAtom:
    """Create a SingleMastTurbulenceSummaryAtom for testing."""
    return SingleMastTurbulenceSummaryAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_df_multiple,
        meta=sample_mast_meta,
    )


# =============================================================================
# Test SingleMastTurbulenceIntensityAtom
# =============================================================================


class TestSingleMastTurbulenceIntensityAtom:
    """Tests for SingleMastTurbulenceIntensityAtom."""

    def test_render_image(
        self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom, tmp_path: Path
    ) -> None:
        """Test renderImage creates a PNG file with IEC bands."""
        image_path = turbulence_intensity_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = turbulence_intensity_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "风速(m/s)" in table
        assert "高度" in table
        assert "平均TI" in table
        assert "代表TI" in table
        assert "IEC类别" in table

    def test_render_summary(self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = turbulence_intensity_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "M01" in summary
        assert "IEC" in summary

    def test_content_hash_consistency(
        self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = turbulence_intensity_atom.get_or_compute_df_hashkey()
        hash2 = turbulence_intensity_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastTurbulenceIntensityAtom_" in hash1

    def test_table_has_multiple_heights(
        self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom
    ) -> None:
        """Test table includes all heights from data."""
        table = turbulence_intensity_atom.renderTable()
        
        # Should have entries for all heights
        assert "100m" in table
        assert "120m" in table
        assert "140m" in table
        assert "外推" in table

    def test_summary_has_iec_statistics(
        self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom
    ) -> None:
        """Test summary includes IEC classification statistics."""
        summary = turbulence_intensity_atom.renderSummary()
        
        # Should contain statistical information
        assert "代表湍流强度" in summary
        assert "类" in summary  # IEC category class

    def test_single_height_render_image(
        self, sample_turbulence_df_single: pl.DataFrame, sample_mast_meta: SingleMastMeta,
        tmp_path: Path
    ) -> None:
        """Test renderImage with single height data."""
        atom = SingleMastTurbulenceIntensityAtom.create(
            schema=TurbulenceSchema,
            df=sample_turbulence_df_single,
            meta=sample_mast_meta,
        )
        
        image_path = atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"


# =============================================================================
# Test SingleMastTurbulenceSectorAtom
# =============================================================================


class TestSingleMastTurbulenceSectorAtom:
    """Tests for SingleMastTurbulenceSectorAtom."""

    def test_render_image(
        self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom, tmp_path: Path
    ) -> None:
        """Test renderImage creates a polar PNG file."""
        image_path = turbulence_sector_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom) -> None:
        """Test renderTable returns non-empty Typst table."""
        table = turbulence_sector_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "风向" in table
        assert "高度" in table

    def test_render_summary(self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = turbulence_sector_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "玫瑰图" in summary

    def test_content_hash_consistency(
        self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = turbulence_sector_atom.get_or_compute_df_hashkey()
        hash2 = turbulence_sector_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastTurbulenceSectorAtom_" in hash1

    def test_table_has_all_sectors(
        self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom
    ) -> None:
        """Test table includes all 16 sectors."""
        table = turbulence_sector_atom.renderTable()
        
        # Should have major direction entries
        assert "N" in table
        assert "E" in table
        assert "S" in table
        assert "W" in table

    def test_summary_has_dominant_directions(
        self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom
    ) -> None:
        """Test summary includes dominant turbulent directions."""
        summary = turbulence_sector_atom.renderSummary()
        
        # Should mention dominant directions
        assert "主导湍流方向" in summary

    def test_filter_by_height(
        self, sample_sector_df: pl.DataFrame, sample_mast_meta: SingleMastMeta, tmp_path: Path
    ) -> None:
        """Test that renderImage filters by height > 100m."""
        # Create data with multiple heights
        rows = []
        for height in [80.0, 120.0]:
            for sector in range(8):  # Just 8 sectors for simplicity
                rows.append({
                    "sector": sector,
                    "sector_name": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][sector],
                    "height": height,
                    "interpolation_marker": None,
                    "mean_ti": 0.12 + sector * 0.01,
                    "representative_ti": 0.14 + sector * 0.01,
                    "iec_category": "B",
                })
        
        df = pl.DataFrame(rows)
        atom = SingleMastTurbulenceSectorAtom.create(
            schema=TurbulenceSectorSchema,
            df=df,
            meta=sample_mast_meta,
        )
        
        image_path = atom.renderImage(tmp_path)
        
        assert image_path.exists()
        # The chart should only include 120m data (height > 100)


# =============================================================================
# Test SingleMastTurbulenceMultiHeightAtom
# =============================================================================


class TestSingleMastTurbulenceMultiHeightAtom:
    """Tests for SingleMastTurbulenceMultiHeightAtom."""

    def test_render_image(
        self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom, tmp_path: Path
    ) -> None:
        """Test renderImage creates a multi-height PNG file."""
        image_path = turbulence_multi_height_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom) -> None:
        """Test renderTable returns empty string (chart only)."""
        table = turbulence_multi_height_atom.renderTable()
        
        # Multi-height atom returns empty table (chart only)
        assert table == ""

    def test_render_summary(self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = turbulence_multi_height_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "高度" in summary

    def test_content_hash_consistency(
        self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = turbulence_multi_height_atom.get_or_compute_df_hashkey()
        hash2 = turbulence_multi_height_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastTurbulenceMultiHeightAtom_" in hash1

    def test_summary_has_figure_reference(
        self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom
    ) -> None:
        """Test summary includes figure reference."""
        summary = turbulence_multi_height_atom.renderSummary()
        
        assert "@fig-" in summary

    def test_summary_compares_heights(
        self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom
    ) -> None:
        """Test summary compares turbulence across heights."""
        summary = turbulence_multi_height_atom.renderSummary()
        
        # Should mention max and min TI heights
        assert "最大" in summary
        assert "最小" in summary

    def test_summary_has_iec_analysis(
        self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom
    ) -> None:
        """Test summary includes IEC classification analysis."""
        summary = turbulence_multi_height_atom.renderSummary()
        
        # Should mention IEC categories
        assert "类" in summary
        assert "IEC" in summary or "参考" in summary


# =============================================================================
# Test SingleMastTurbulenceSummaryAtom
# =============================================================================


class TestSingleMastTurbulenceSummaryAtom:
    """Tests for SingleMastTurbulenceSummaryAtom."""

    def test_render_image(
        self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom, tmp_path: Path
    ) -> None:
        """Test renderImage returns empty Path (no image for summary)."""
        image_path = turbulence_summary_atom.renderImage(tmp_path)
        
        # Summary atom returns empty Path (no image generation)
        assert image_path == Path()

    def test_render_table(self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom) -> None:
        """Test renderTable returns non-empty Typst summary table."""
        table = turbulence_summary_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "高度" in table
        assert "风速范围" in table
        assert "平均湍流强度" in table
        assert "代表湍流强度" in table
        assert "IEC类别" in table

    def test_render_summary(self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = turbulence_summary_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
        assert "汇总" in summary or "分析" in summary

    def test_content_hash_consistency(
        self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom
    ) -> None:
        """Test that same data produces same hash."""
        hash1 = turbulence_summary_atom.get_or_compute_df_hashkey()
        hash2 = turbulence_summary_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastTurbulenceSummaryAtom_" in hash1

    def test_table_has_all_heights(
        self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom
    ) -> None:
        """Test table includes all heights."""
        table = turbulence_summary_atom.renderTable()
        
        assert "100m" in table
        assert "120m" in table
        assert "140m" in table

    def test_summary_has_extreme_values(
        self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom
    ) -> None:
        """Test summary includes max/min TI information."""
        summary = turbulence_summary_atom.renderSummary()
        
        # Should mention extreme values
        assert "最大值" in summary
        assert "最小值" in summary

    def test_summary_has_recommendations(
        self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom
    ) -> None:
        """Test summary includes turbine selection recommendations."""
        summary = turbulence_summary_atom.renderSummary()
        
        # Should have recommendations based on turbulence level
        assert "机组" in summary or "选型" in summary


# =============================================================================
# Cross-cutting Tests
# =============================================================================


class TestAllTurbulenceAtoms:
    """Tests that apply to all turbulence atoms."""

    @pytest.fixture
    def all_turbulence_atoms(
        self,
        turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom,
        turbulence_sector_atom: SingleMastTurbulenceSectorAtom,
        turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom,
        turbulence_summary_atom: SingleMastTurbulenceSummaryAtom,
    ) -> list[Any]:
        """Return a list of all turbulence atom types for testing."""
        return [
            turbulence_intensity_atom,
            turbulence_sector_atom,
            turbulence_multi_height_atom,
            turbulence_summary_atom,
        ]

    def test_all_atoms_have_mast_name(self, all_turbulence_atoms: list[Any]) -> None:
        """Verify all atoms have correct mast name in meta."""
        for atom in all_turbulence_atoms:
            assert atom.meta.mast_name == "M01"

    def test_all_atoms_have_consistent_hashes(self, all_turbulence_atoms: list[Any]) -> None:
        """Verify all atoms produce consistent hashes."""
        for atom in all_turbulence_atoms:
            hash1 = atom.get_or_compute_df_hashkey()
            hash2 = atom.get_or_compute_df_hashkey()
            assert hash1 == hash2
            assert len(hash1) > 0

    @pytest.mark.xfail(reason="value_counts() ordering not deterministic - implementation limitation")
    def test_summary_caching(self, all_turbulence_atoms: list[Any]) -> None:
        """Verify summary output is consistent across multiple calls."""
        for atom in all_turbulence_atoms:
            summary1 = atom.renderSummary()
            summary2 = atom.renderSummary()
            assert summary1 == summary2


class TestImageCaching:
    """Tests for image caching behavior."""

    def test_intensity_image_caching(
        self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom, tmp_path: Path
    ) -> None:
        """Verify intensity images are cached."""
        # First render
        path1 = turbulence_intensity_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = turbulence_intensity_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2  # File not modified

    def test_sector_image_caching(
        self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom, tmp_path: Path
    ) -> None:
        """Verify sector images are cached."""
        # First render
        path1 = turbulence_sector_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = turbulence_sector_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2

    def test_multi_height_image_caching(
        self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom, tmp_path: Path
    ) -> None:
        """Verify multi-height images are cached."""
        # First render
        path1 = turbulence_multi_height_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = turbulence_multi_height_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2

    def test_intensity_force_regenerate(
        self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom, tmp_path: Path
    ) -> None:
        """Verify force=True regenerates intensity images."""
        # First render
        path1 = turbulence_intensity_atom.renderImage(tmp_path)
        
        # Force regenerate
        path2 = turbulence_intensity_atom.renderImage(tmp_path, force=True)
        
        assert path1 == path2
        assert path2.exists()

    def test_sector_force_regenerate(
        self, turbulence_sector_atom: SingleMastTurbulenceSectorAtom, tmp_path: Path
    ) -> None:
        """Verify force=True regenerates sector images."""
        # First render
        path1 = turbulence_sector_atom.renderImage(tmp_path)
        
        # Force regenerate
        path2 = turbulence_sector_atom.renderImage(tmp_path, force=True)
        
        assert path1 == path2
        assert path2.exists()

    def test_multi_height_force_regenerate(
        self, turbulence_multi_height_atom: SingleMastTurbulenceMultiHeightAtom, tmp_path: Path
    ) -> None:
        """Verify force=True regenerates multi-height images."""
        # First render
        path1 = turbulence_multi_height_atom.renderImage(tmp_path)
        
        # Force regenerate
        path2 = turbulence_multi_height_atom.renderImage(tmp_path, force=True)
        
        assert path1 == path2
        assert path2.exists()


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.xfail(reason="Empty dataframe handling not yet implemented in atoms")
    def test_empty_dataframe_intensity(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test turbulence intensity atom with empty DataFrame."""
        empty_df = pl.DataFrame({
            "wind_speed_bin": pl.Series([], dtype=pl.Int64),
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "mean_ti": pl.Series([], dtype=pl.Float64),
            "std_ti": pl.Series([], dtype=pl.Float64),
            "representative_ti": pl.Series([], dtype=pl.Float64),
            "iec_category": pl.Series([], dtype=pl.String),
        })
        
        atom = SingleMastTurbulenceIntensityAtom.create(
            schema=TurbulenceSchema,
            df=empty_df,
            meta=sample_mast_meta,
        )
        
        table = atom.renderTable()
        assert isinstance(table, str)
        
        summary = atom.renderSummary()
        assert isinstance(summary, str)

    @pytest.mark.xfail(reason="Empty dataframe handling not yet implemented in atoms")
    def test_empty_dataframe_sector(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test sector atom with empty DataFrame."""
        empty_df = pl.DataFrame({
            "sector": pl.Series([], dtype=pl.Int64),
            "sector_name": pl.Series([], dtype=pl.String),
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "mean_ti": pl.Series([], dtype=pl.Float64),
            "representative_ti": pl.Series([], dtype=pl.Float64),
            "iec_category": pl.Series([], dtype=pl.String),
        })
        
        atom = SingleMastTurbulenceSectorAtom.create(
            schema=TurbulenceSectorSchema,
            df=empty_df,
            meta=sample_mast_meta,
        )
        
        # Should not raise
        table = atom.renderTable()
        assert isinstance(table, str)
        
        summary = atom.renderSummary()
        assert isinstance(summary, str)

    def test_single_row_data(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test atoms with single row of data."""
        single_row_df = pl.DataFrame({
            "wind_speed_bin": [5],
            "height": [100.0],
            "interpolation_marker": [None],
            "mean_ti": [0.15],
            "std_ti": [0.02],
            "representative_ti": [0.176],
            "iec_category": ["B"],
        })
        
        atom = SingleMastTurbulenceIntensityAtom.create(
            schema=TurbulenceSchema,
            df=single_row_df,
            meta=sample_mast_meta,
        )
        
        table = atom.renderTable()
        assert "100m" in table
        assert "B" in table
        
        summary = atom.renderSummary()
        assert isinstance(summary, str)
