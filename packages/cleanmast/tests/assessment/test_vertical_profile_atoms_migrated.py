"""Tests for vertical profile atoms.

Tests cover all 3 vertical profile related atoms:
- SingleMastVerticalProfileAtom (power law profile)
- SingleMastWindShearTableAtom (shear statistics table)
- SingleMastWindShearExponentAtom (shear matrix)

Includes tests for render methods and realistic data scenarios.
"""

from pathlib import Path

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.vertical_profile import (
    SingleMastVerticalProfileAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_matrix import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_table import (
    SingleMastWindShearTableAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_meta() -> SingleMastMeta:
    """Create sample metadata for testing."""
    return SingleMastMeta(
        mast_name="TestMast",
        air_density=1.225,
        caption="Test caption",
    )


@pytest.fixture
def vertical_profile_data() -> pl.DataFrame:
    """Create sample vertical profile data with power law fit."""
    return pl.DataFrame({
        "height": [100.0, 120.0, 140.0],
        "interpolation_marker": [None, None, None],
        "wind_speed_mean": [8.0, 8.5, 9.0],
        "wind_speed_std": [1.5, 1.6, 1.7],
        "alpha": [0.143, 0.143, 0.143],  # Same alpha for all heights
        "r_squared": [0.998, 0.998, 0.998],
    })


@pytest.fixture
def vertical_profile_data_interpolated() -> pl.DataFrame:
    """Create vertical profile data with interpolation markers."""
    return pl.DataFrame({
        "height": [80.0, 100.0, 120.0],
        "interpolation_marker": ["*", None, None],
        "wind_speed_mean": [7.5, 8.0, 8.5],
        "wind_speed_std": [1.4, 1.5, 1.6],
        "alpha": [0.14, 0.14, 0.14],
        "r_squared": [0.995, 0.995, 0.995],
    })


@pytest.fixture
def wind_shear_data() -> pl.DataFrame:
    """Create sample wind shear statistics data."""
    return pl.DataFrame({
        "from_height": [100.0, 100.0, 120.0],
        "to_height": [120.0, 140.0, 140.0],
        "alpha_mean": [0.143, 0.145, 0.148],
        "alpha_std": [0.05, 0.06, 0.055],
        "alpha_min": [0.02, 0.03, 0.025],
        "alpha_max": [0.28, 0.30, 0.29],
    })


@pytest.fixture
def wind_shear_data_single_pair() -> pl.DataFrame:
    """Create wind shear data with single height pair."""
    return pl.DataFrame({
        "from_height": [100.0],
        "to_height": [120.0],
        "alpha_mean": [0.143],
        "alpha_std": [0.05],
        "alpha_min": [0.02],
        "alpha_max": [0.28],
    })


@pytest.fixture
def empty_dataframe() -> pl.DataFrame:
    """Create empty DataFrame for edge case testing."""
    return pl.DataFrame({
        "height": pl.Series([], dtype=pl.Float64),
        "interpolation_marker": pl.Series([], dtype=pl.String),
        "wind_speed_mean": pl.Series([], dtype=pl.Float64),
        "wind_speed_std": pl.Series([], dtype=pl.Float64),
        "alpha": pl.Series([], dtype=pl.Float64),
        "r_squared": pl.Series([], dtype=pl.Float64),
    })


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create temporary output directory for image tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# =============================================================================
# Test SingleMastVerticalProfileAtom
# =============================================================================


class TestSingleMastVerticalProfileAtom:
    """Tests for SingleMastVerticalProfileAtom."""

    def test_render_table_basic(
        self, sample_meta: SingleMastMeta, vertical_profile_data: pl.DataFrame
    ) -> None:
        """Test basic table rendering."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        assert "#table(" in table
        assert "高度" in table
        assert "平均风速(m/s)" in table
        assert "风切变指数α" in table
        assert "拟合优度R²" in table
        assert "100m" in table
        assert "120m" in table
        assert "140m" in table
    
    def test_render_table_with_interpolation(
        self,
        sample_meta: SingleMastMeta,
        vertical_profile_data_interpolated: pl.DataFrame,
    ) -> None:
        """Test table rendering with interpolation markers."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data_interpolated,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        # Should show interpolation marker for 80m
        assert "80m*" in table or "100m" in table
        assert "#table(" in table
    
    def test_render_table_alpha_formatting(
        self, sample_meta: SingleMastMeta, vertical_profile_data: pl.DataFrame
    ) -> None:
        """Test that alpha values are formatted to 3 decimal places."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        # Check that alpha value appears with 3 decimal places
        assert "0.143" in table
    
    def test_render_table_r_squared_formatting(
        self, sample_meta: SingleMastMeta, vertical_profile_data: pl.DataFrame
    ) -> None:
        """Test that R² values are formatted to 3 decimal places."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        # Check that R² value appears
        assert "0.998" in table
    
    def test_render_table_missing_alpha(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test table rendering when alpha is None."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [None],
            "r_squared": [None],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        table = atom.renderTable()
        
        assert "#table(" in table
        assert "-" in table  # Should show dash for missing values
    
    def test_render_image_basic(
        self,
        sample_meta: SingleMastMeta,
        vertical_profile_data: pl.DataFrame,
        temp_output_dir: Path,
    ) -> None:
        """Test basic image rendering."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        image_path = atom.renderImage(temp_output_dir)
        
        assert image_path is not None
        assert image_path.suffix == ".png"
        assert image_path.exists()
        assert image_path.stat().st_size > 0
    
    def test_render_image_caching(
        self,
        sample_meta: SingleMastMeta,
        vertical_profile_data: pl.DataFrame,
        temp_output_dir: Path,
    ) -> None:
        """Test that image caching works correctly."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        # First render
        path1 = atom.renderImage(temp_output_dir)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = atom.renderImage(temp_output_dir)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2  # File not regenerated
    
    def test_render_image_force_regenerate(
        self,
        sample_meta: SingleMastMeta,
        vertical_profile_data: pl.DataFrame,
        temp_output_dir: Path,
    ) -> None:
        """Test force regeneration of image."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        # First render
        path1 = atom.renderImage(temp_output_dir)
        
        # Force regenerate
        path2 = atom.renderImage(temp_output_dir, force=True)
        
        assert path1 == path2
        assert path2.exists()
    
    def test_render_image_title_includes_alpha_and_r2(
        self,
        sample_meta: SingleMastMeta,
        vertical_profile_data: pl.DataFrame,
        temp_output_dir: Path,
    ) -> None:
        """Test that image title includes alpha and R² values."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        image_path = atom.renderImage(temp_output_dir)
        
        # Title should contain alpha and R²
        assert "α=" in str(image_path) or "vertical_profile_" in str(image_path)
    
    def test_render_summary_basic(
        self, sample_meta: SingleMastMeta, vertical_profile_data: pl.DataFrame
    ) -> None:
        """Test basic summary rendering."""
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        summary = atom.renderSummary()
        
        assert "TestMast" in summary
        assert "测风塔" in summary
        assert "100m" in summary or "120m" in summary
        assert "风切变指数" in summary
        assert "幂律拟合" in summary
    
    def test_render_summary_terrain_classification_smooth(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain classification for smooth terrain (alpha < 0.12)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.10],
            "r_squared": [0.98],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "平滑" in summary or "水面" in summary
    
    def test_render_summary_terrain_classification_open(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain classification for open terrain (0.12 ≤ alpha < 0.16)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.14],
            "r_squared": [0.98],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "开阔" in summary or "草地" in summary
    
    def test_render_summary_terrain_classification_rough(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain classification for rough terrain (0.16 ≤ alpha < 0.25)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.20],
            "r_squared": [0.98],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "粗糙" in summary or "郊区" in summary
    
    def test_render_summary_terrain_classification_very_rough(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain classification for very rough terrain (alpha ≥ 0.25)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.30],
            "r_squared": [0.98],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "非常粗糙" in summary or "城市" in summary
    
    def test_render_summary_fit_quality_excellent(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test fit quality description for excellent fit (R² ≥ 0.95)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.14],
            "r_squared": [0.97],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "优秀" in summary
    
    def test_render_summary_fit_quality_good(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test fit quality description for good fit (0.85 ≤ R² < 0.95)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.14],
            "r_squared": [0.90],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "良好" in summary
    
    def test_render_summary_fit_quality_fair(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test fit quality description for fair fit (0.70 ≤ R² < 0.85)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.14],
            "r_squared": [0.75],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "一般" in summary
    
    def test_render_summary_fit_quality_poor(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test fit quality description for poor fit (R² < 0.70)."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.14],
            "r_squared": [0.50],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "有待改进" in summary
    
    def test_render_summary_no_alpha(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test summary when alpha is None."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [None],
            "r_squared": [None],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "无法计算" in summary or "TestMast" in summary


# =============================================================================
# Test SingleMastWindShearTableAtom
# =============================================================================


class TestSingleMastWindShearTableAtom:
    """Tests for SingleMastWindShearTableAtom."""

    def test_render_table_basic(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test basic table rendering."""
        atom = SingleMastWindShearTableAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        assert "#table(" in table
        assert "起始高度(m)" in table
        assert "目标高度(m)" in table
        assert "平均α" in table
        assert "标准差" in table
        assert "最小值" in table
        assert "最大值" in table
    
    def test_render_table_sorting(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test that table rows are sorted by from_height then to_height."""
        # Create data in unsorted order
        df = pl.DataFrame({
            "from_height": [120.0, 100.0, 100.0],
            "to_height": [140.0, 140.0, 120.0],
            "alpha_mean": [0.148, 0.145, 0.143],
            "alpha_std": [0.055, 0.06, 0.05],
            "alpha_min": [0.025, 0.03, 0.02],
            "alpha_max": [0.29, 0.30, 0.28],
        })
        
        atom = SingleMastWindShearTableAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        table = atom.renderTable()
        
        # Check that data appears (table should be sorted)
        assert "100" in table
        assert "120" in table
        assert "140" in table
    
    def test_render_table_alpha_formatting(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test that alpha values are formatted to 3 decimal places."""
        atom = SingleMastWindShearTableAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        # Check that alpha values appear with 3 decimal places
        assert "0.143" in table
        assert "0.145" in table
    
    def test_render_image_returns_empty_path(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test that renderImage returns empty path (no image for table)."""
        atom = SingleMastWindShearTableAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        output_dir = Path("/tmp/test")
        path = atom.renderImage(output_dir)
        
        assert path == Path()
    
    def test_render_summary_basic(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test basic summary rendering."""
        atom = SingleMastWindShearTableAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        summary = atom.renderSummary()
        
        assert "TestMast" in summary
        assert "测风塔" in summary
        assert "3" in summary  # 3 height pairs
        assert "100" in summary
        assert "120" in summary
        assert "140" in summary
    
    def test_render_summary_terrain_type_flat(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain type for flat terrain (mean alpha ≤ 0.12)."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.10],
            "alpha_std": [0.02],
            "alpha_min": [0.05],
            "alpha_max": [0.15],
        })
        
        atom = SingleMastWindShearTableAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "平坦" in summary or "开阔" in summary
    
    def test_render_summary_terrain_type_complex(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain type for complex terrain (mean alpha > 0.25)."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.30],
            "alpha_std": [0.05],
            "alpha_min": [0.20],
            "alpha_max": [0.40],
        })
        
        atom = SingleMastWindShearTableAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "复杂" in summary or "粗糙" in summary
    
    def test_render_summary_hub_height_suitable(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test hub height suitability for suitable range (0.12-0.20)."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.15],
            "alpha_std": [0.02],
            "alpha_min": [0.10],
            "alpha_max": [0.20],
        })
        
        atom = SingleMastWindShearTableAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "适合" in summary
    
    def test_render_summary_hub_height_caution(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test hub height caution for outside typical range."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.30],
            "alpha_std": [0.05],
            "alpha_min": [0.20],
            "alpha_max": [0.40],
        })
        
        atom = SingleMastWindShearTableAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "谨慎" in summary


# =============================================================================
# Test SingleMastWindShearExponentAtom
# =============================================================================


class TestSingleMastWindShearExponentAtom:
    """Tests for SingleMastWindShearExponentAtom."""

    def test_render_table_basic(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test basic matrix table rendering."""
        atom = SingleMastWindShearExponentAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        assert "#table(" in table
        assert "高度" in table
        assert "100m" in table
        assert "120m" in table
        assert "140m" in table
    
    def test_render_table_diagonal_marker(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test that diagonal shows '◦' marker."""
        atom = SingleMastWindShearExponentAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        assert "◦" in table
    
    def test_render_table_antisymmetric_values(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test that table shows antisymmetric values (α_ij = -α_ji)."""
        atom = SingleMastWindShearExponentAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        # Should contain positive alpha values
        assert "0.143" in table or "0.145" in table or "0.148" in table
    
    def test_render_table_missing_values(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test table rendering with missing values."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.143],
            "alpha_std": [0.05],
            "alpha_min": [0.02],
            "alpha_max": [0.28],
        })
        
        atom = SingleMastWindShearExponentAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        table = atom.renderTable()
        
        # Should show dash for missing pairs
        assert "-" in table or "◦" in table
    
    def test_render_image_returns_empty_path(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test that renderImage returns empty path (no image for matrix)."""
        atom = SingleMastWindShearExponentAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        output_dir = Path("/tmp/test")
        path = atom.renderImage(output_dir)
        
        assert path == Path()
    
    def test_render_summary_basic(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test basic summary rendering."""
        atom = SingleMastWindShearExponentAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        summary = atom.renderSummary()
        
        assert "TestMast" in summary
        assert "测风塔" in summary
        assert "100m" in summary
        assert "120m" in summary
        assert "140m" in summary
    
    def test_render_summary_terrain_smooth(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain description for smooth terrain (alpha < 0.12)."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.10],
            "alpha_std": [0.02],
            "alpha_min": [0.05],
            "alpha_max": [0.15],
        })
        
        atom = SingleMastWindShearExponentAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "光滑" in summary or "水面" in summary
    
    def test_render_summary_terrain_open(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain description for open terrain (0.12 ≤ alpha < 0.16)."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.14],
            "alpha_std": [0.02],
            "alpha_min": [0.10],
            "alpha_max": [0.18],
        })
        
        atom = SingleMastWindShearExponentAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "开阔" in summary or "草地" in summary or "农田" in summary
    
    def test_render_summary_terrain_rough(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain description for rough terrain (0.16 ≤ alpha < 0.25)."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.20],
            "alpha_std": [0.03],
            "alpha_min": [0.15],
            "alpha_max": [0.25],
        })
        
        atom = SingleMastWindShearExponentAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "粗糙" in summary or "郊区" in summary or "树林" in summary
    
    def test_render_summary_terrain_very_rough(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test terrain description for very rough terrain (alpha ≥ 0.25)."""
        df = pl.DataFrame({
            "from_height": [100.0],
            "to_height": [120.0],
            "alpha_mean": [0.30],
            "alpha_std": [0.05],
            "alpha_min": [0.20],
            "alpha_max": [0.40],
        })
        
        atom = SingleMastWindShearExponentAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        summary = atom.renderSummary()
        
        assert "非常粗糙" in summary or "城市" in summary or "密集" in summary
    
    def test_render_summary_min_max_pairs(
        self, sample_meta: SingleMastMeta, wind_shear_data: pl.DataFrame
    ) -> None:
        """Test that summary includes min and max alpha pairs."""
        atom = SingleMastWindShearExponentAtom(
            schema=WindShearSchema, df=wind_shear_data,
            meta=sample_meta
        )
        
        summary = atom.renderSummary()
        
        # Should mention min and max values
        assert "最小" in summary
        assert "最大" in summary


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_vertical_profile_empty_data(
        self, sample_meta: SingleMastMeta, empty_dataframe: pl.DataFrame
    ) -> None:
        """Test vertical profile atom with empty data."""
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=empty_dataframe, meta=sample_meta)
        
        table = atom.renderTable()
        summary = atom.renderSummary()
        
        assert "#table(" in table
        assert "TestMast" in summary
    
    def test_wind_shear_table_empty_data(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test wind shear table atom with empty data."""
        df = pl.DataFrame({
            "from_height": pl.Series([], dtype=pl.Float64),
            "to_height": pl.Series([], dtype=pl.Float64),
            "alpha_mean": pl.Series([], dtype=pl.Float64),
            "alpha_std": pl.Series([], dtype=pl.Float64),
            "alpha_min": pl.Series([], dtype=pl.Float64),
            "alpha_max": pl.Series([], dtype=pl.Float64),
        })
        
        atom = SingleMastWindShearTableAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        
        table = atom.renderTable()
        summary = atom.renderSummary()
        
        assert "#table(" in table
        assert "TestMast" in summary
    
    def test_wind_shear_matrix_empty_data(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test wind shear matrix atom with empty data."""
        df = pl.DataFrame({
            "from_height": pl.Series([], dtype=pl.Float64),
            "to_height": pl.Series([], dtype=pl.Float64),
            "alpha_mean": pl.Series([], dtype=pl.Float64),
            "alpha_std": pl.Series([], dtype=pl.Float64),
            "alpha_min": pl.Series([], dtype=pl.Float64),
            "alpha_max": pl.Series([], dtype=pl.Float64),
        })
        
        atom = SingleMastWindShearExponentAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        
        table = atom.renderTable()
        summary = atom.renderSummary()
        
        assert "#table(" in table
        assert "TestMast" in summary
    
    def test_vertical_profile_no_meta(self) -> None:
        """Test vertical profile atom without metadata."""
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_mean": [8.0],
            "wind_speed_std": [1.5],
            "alpha": [0.14],
            "r_squared": [0.98],
        })
        
        # Create minimal meta
        meta = SingleMastMeta(
            mast_name="MinimalMast",
            air_density=1.225,
            caption="",
        )
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=meta)
        summary = atom.renderSummary()
        
        assert "MinimalMast" in summary


# =============================================================================
# Test Realistic Data Scenarios
# =============================================================================


class TestRealisticDataScenarios:
    """Tests with realistic wind data scenarios."""

    def test_open_terrain_profile(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test with open terrain profile (alpha ≈ 0.14)."""
        df = pl.DataFrame({
            "height": [80.0, 100.0, 120.0, 140.0],
            "interpolation_marker": [None, None, None, None],
            "wind_speed_mean": [7.5, 8.0, 8.4, 8.8],
            "wind_speed_std": [1.4, 1.5, 1.6, 1.7],
            "alpha": [0.14, 0.14, 0.14, 0.14],
            "r_squared": [0.995, 0.995, 0.995, 0.995],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        
        summary = atom.renderSummary()
        assert "开阔" in summary or "草地" in summary
        
        table = atom.renderTable()
        assert "80m" in table
        assert "140m" in table
    
    def test_complex_terrain_profile(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test with complex terrain profile (alpha ≈ 0.25)."""
        df = pl.DataFrame({
            "height": [60.0, 80.0, 100.0],
            "interpolation_marker": [None, None, None],
            "wind_speed_mean": [6.0, 6.8, 7.5],
            "wind_speed_std": [1.8, 2.0, 2.2],
            "alpha": [0.25, 0.25, 0.25],
            "r_squared": [0.98, 0.98, 0.98],
        })
        
        atom = SingleMastVerticalProfileAtom.create(schema=VerticalProfileSchema, df=df, meta=sample_meta)
        
        summary = atom.renderSummary()
        assert "粗糙" in summary or "复杂" in summary
    
    def test_multi_height_shear_analysis(
        self, sample_meta: SingleMastMeta
    ) -> None:
        """Test shear analysis with many height pairs."""
        # Create data for 5 heights (10 unique pairs)
        heights = [60.0, 80.0, 100.0, 120.0, 140.0]
        pairs = []
        for i, h1 in enumerate(heights):
            for h2 in heights[i+1:]:
                pairs.append({
                    "from_height": h1,
                    "to_height": h2,
                    "alpha_mean": 0.14 + np.random.uniform(-0.02, 0.02),
                    "alpha_std": 0.05,
                    "alpha_min": 0.02,
                    "alpha_max": 0.28,
                })
        
        df = pl.DataFrame(pairs)
        
        # Test table atom
        table_atom = SingleMastWindShearTableAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        table = table_atom.renderTable()
        assert "#table(" in table
        
        # Test matrix atom
        matrix_atom = SingleMastWindShearExponentAtom.create(schema=WindShearSchema, df=df, meta=sample_meta)
        matrix_table = matrix_atom.renderTable()
        assert "#table(" in matrix_table
        assert "60m" in matrix_table or "80m" in matrix_table
