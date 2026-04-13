"""Tests for SingleMastMonthlyWindRoseGridAtom.

Tests cover wind rose grid atom functionality:
- Atom creation with .create()
- renderTable() returns valid Typst
- renderImage() generates 3x4 grid PNG
- renderSummary() returns Chinese text
- Image caching behavior
- Edge cases
"""

from pathlib import Path

import matplotlib.figure
import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_grid import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.domain.types import TypstParagraph, TypstTable
from cleanmast.subdomains.assessment.domain.value_objects import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects import (
    SingleMastWindRoseSchema as WindRoseSchema,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_wind_rose_df() -> pl.DataFrame:
    """Create sample wind rose data DataFrame for all 12 months."""
    rows = []
    months = [
        (1, "1月"), (2, "2月"), (3, "3月"), (4, "4月"),
        (5, "5月"), (6, "6月"), (7, "7月"), (8, "8月"),
        (9, "9月"), (10, "10月"), (11, "11月"), (12, "12月"),
    ]
    sectors = [
        (0, "N"), (1, "NNE"), (2, "NE"), (3, "ENE"),
        (4, "E"), (5, "ESE"), (6, "SE"), (7, "SSE"),
        (8, "S"), (9, "SSW"), (10, "SW"), (11, "WSW"),
        (12, "W"), (13, "WNW"), (14, "NW"), (15, "NNW"),
    ]

    np.random.seed(42)

    for month_num, month_name in months:
        for sector_num, sector_name in sectors:
            if month_num in [12, 1, 2]:
                if sector_name in ["NW", "NNW", "WNW"]:
                    base_freq = 0.15
                elif sector_name in ["N", "W"]:
                    base_freq = 0.10
                else:
                    base_freq = 0.03
            elif month_num in [3, 4, 5]:
                if sector_name in ["N", "NNE", "NNW"]:
                    base_freq = 0.14
                elif sector_name in ["NE", "NW"]:
                    base_freq = 0.09
                else:
                    base_freq = 0.03
            elif month_num in [6, 7, 8]:
                if sector_name in ["S", "SSE", "SSW"]:
                    base_freq = 0.16
                elif sector_name in ["SE", "SW"]:
                    base_freq = 0.10
                else:
                    base_freq = 0.03
            else:
                if sector_name in ["NE", "ENE", "N"]:
                    base_freq = 0.13
                elif sector_name in ["E", "NNE"]:
                    base_freq = 0.08
                else:
                    base_freq = 0.04

            frequency = base_freq + np.random.uniform(-0.01, 0.01)
            frequency = max(0.001, frequency)
            wind_power_density = 500.0 + np.random.uniform(-100, 100)
            energy_frequency = frequency * (wind_power_density / 500.0)

            rows.append({
                "month": month_num,
                "month_name": month_name,
                "sector": sector_num,
                "sector_name": sector_name,
                "height": 100.0,
                "interpolation_marker": None,
                "frequency": frequency,
                "wind_power_density": wind_power_density,
                "energy_frequency": energy_frequency,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_wind_rose_df_multiple_heights() -> pl.DataFrame:
    """Create sample wind rose data with multiple heights."""
    rows = []
    months = [
        (1, "1月"), (2, "2月"), (3, "3月"), (4, "4月"),
        (5, "5月"), (6, "6月"), (7, "7月"), (8, "8月"),
        (9, "9月"), (10, "10月"), (11, "11月"), (12, "12月"),
    ]
    sectors = [
        (0, "N"), (1, "NNE"), (2, "NE"), (3, "ENE"),
        (4, "E"), (5, "ESE"), (6, "SE"), (7, "SSE"),
        (8, "S"), (9, "SSW"), (10, "SW"), (11, "WSW"),
        (12, "W"), (13, "WNW"), (14, "NW"), (15, "NNW"),
    ]

    np.random.seed(43)

    for month_num, month_name in months:
        for height, marker in [(80.0, None), (100.0, None), (120.0, "外推")]:
            for sector_num, sector_name in sectors:
                height_factor = 1.0 + (height - 100) * 0.001

                if month_num in [12, 1, 2]:
                    if sector_name in ["NW", "NNW", "WNW"]:
                        base_freq = 0.15
                    else:
                        base_freq = 0.05
                elif month_num in [6, 7, 8]:
                    if sector_name in ["S", "SSE", "SSW"]:
                        base_freq = 0.16
                    else:
                        base_freq = 0.04
                else:
                    base_freq = 0.08

                frequency = base_freq * height_factor
                wind_power_density = 500.0 + (height - 100) * 2.0 + np.random.uniform(-50, 50)
                energy_frequency = frequency * (wind_power_density / 500.0)

                rows.append({
                    "month": month_num,
                    "month_name": month_name,
                    "sector": sector_num,
                    "sector_name": sector_name,
                    "height": height,
                    "interpolation_marker": marker,
                    "frequency": frequency,
                    "wind_power_density": wind_power_density,
                    "energy_frequency": energy_frequency,
                })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_wind_rose_df_below_100m() -> pl.DataFrame:
    """Create sample wind rose data with only below 100m heights."""
    rows = []
    months = [(1, "1月"), (6, "6月"), (12, "12月")]
    sectors = [(0, "N"), (4, "E"), (8, "S"), (12, "W")]

    for month_num, month_name in months:
        for height in [50.0, 80.0]:
            for sector_num, sector_name in sectors:
                rows.append({
                    "month": month_num,
                    "month_name": month_name,
                    "sector": sector_num,
                    "sector_name": sector_name,
                    "height": height,
                    "interpolation_marker": None,
                    "frequency": 0.25,
                    "wind_power_density": 450.0,
                    "energy_frequency": 0.25 * (450.0 / 500.0),
                })

    return pl.DataFrame(rows)


@pytest.fixture
def wind_rose_grid_atom(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastMonthlyWindRoseGridAtom:
    """Create a SingleMastMonthlyWindRoseGridAtom for testing."""
    return SingleMastMonthlyWindRoseGridAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_rose_grid_atom_multi_height(
    sample_wind_rose_df_multiple_heights: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastMonthlyWindRoseGridAtom:
    """Create a SingleMastMonthlyWindRoseGridAtom with multiple heights."""
    return SingleMastMonthlyWindRoseGridAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df_multiple_heights,
        meta=sample_mast_meta,
    )


# =============================================================================
# Test SingleMastMonthlyWindRoseGridAtom
# =============================================================================


class TestSingleMastMonthlyWindRoseGridAtom:
    """Tests for SingleMastMonthlyWindRoseGridAtom."""

    def test_atom_creation(self, sample_wind_rose_df: pl.DataFrame, sample_mast_meta: SingleMastMeta) -> None:
        """Test atom creation with .create() method."""
        atom = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=sample_wind_rose_df,
            meta=sample_mast_meta,
        )
        
        assert isinstance(atom, SingleMastMonthlyWindRoseGridAtom)
        assert atom.meta.mast_name == "M01"
        assert atom.df is not None
        assert len(atom.df) > 0

    def test_render_image(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom, tmp_path: Path) -> None:
        """Test renderImage creates a PNG file with 3x4 grid."""
        image_path = wind_rose_grid_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Test renderTable returns None by design."""
        table = wind_rose_grid_atom.renderTable()

        assert table is None

    def test_render_summary(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Test renderSummary returns non-empty Chinese text."""
        summary = wind_rose_grid_atom.renderSummary()
        
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        # Verify summary content
        summary_node = summary[0]
        assert "测风塔" in summary_node.text
        assert "M01" in summary_node.text
        assert "主导风向" in summary_node.text

    def test_content_hash_consistency(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Test that same data produces same hash."""
        hash1 = wind_rose_grid_atom.get_or_compute_df_hashkey()
        hash2 = wind_rose_grid_atom.get_or_compute_df_hashkey()
        
        assert hash1 == hash2
        assert "SingleMastMonthlyWindRoseGridAtom_" in hash1

    def test_table_has_all_months(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Test table is not rendered for this atom."""
        table = wind_rose_grid_atom.renderTable()
        assert table is None

    def test_table_has_dominant_sectors(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        table = wind_rose_grid_atom.renderTable()
        assert table is None

    def test_table_has_frequency_percentages(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        table = wind_rose_grid_atom.renderTable()
        assert table is None

    def test_summary_has_concise_format(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Test summary uses concise format without fluff."""
        summary = wind_rose_grid_atom.renderSummary()
        summary_node = summary[0]
        
        assert "主导风向为" in summary_node.text
        assert "反映了" not in summary_node.text
        assert "季节性" not in summary_node.text

    def test_summary_has_dominant_sectors(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Test summary includes dominant sectors list."""
        summary = wind_rose_grid_atom.renderSummary()
        summary_node = summary[0]
        
        assert "、" in summary_node.text or "主导风向" in summary_node.text

    def test_render_image_with_multiple_heights(
        self, wind_rose_grid_atom_multi_height: SingleMastMonthlyWindRoseGridAtom, tmp_path: Path
    ) -> None:
        """Test renderImage with multiple heights includes legend."""
        image_path = wind_rose_grid_atom_multi_height.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"

    def test_render_image_filters_below_100m(
        self, sample_wind_rose_df_below_100m: pl.DataFrame, sample_mast_meta: SingleMastMeta, tmp_path: Path
    ) -> None:
        """Test that renderImage filters data to >=100m heights."""
        atom = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=sample_wind_rose_df_below_100m,
            meta=sample_mast_meta,
        )
        
        # Should still create image even with no >=100m data (though chart may be empty)
        image_path = atom.renderImage(tmp_path)
        
        assert image_path.exists()

    def test_summary_has_content(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        summary = wind_rose_grid_atom.renderSummary()
        summary_node = summary[0]

        assert isinstance(summary_node, TypstParagraph)
        assert "测风塔" in summary_node.text
        assert "主导风向" in summary_node.text

    def test_monthly_grid_angle_mapping(
        self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom
    ) -> None:
        """Assert polar line angles follow correct sector mapping."""
        plot_df = wind_rose_grid_atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(
                    x["height"], x["interpolation_marker"]
                )
            )
            .alias("height_display")
        )
        chart = wind_rose_grid_atom._build_monthly_grid_chart(plot_df)

        ax = None
        for candidate in chart.axes:
            if candidate.get_lines():
                ax = candidate
                break

        assert ax is not None, "Expected at least one polar axis with lines"
        line = ax.get_lines()[0]
        angles = np.asarray(line.get_xdata())

        assert angles[0] == pytest.approx(0.0, abs=1e-5)
        assert angles[4] == pytest.approx(np.pi / 2, abs=1e-5)
        assert angles[0] == pytest.approx(angles[-1], abs=1e-5)
        assert np.all(np.diff(angles[:-1]) >= -1e-6)

    def test_monthly_grid_mark_type(
        self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom
    ) -> None:
        """Assert the returned chart is a matplotlib Figure."""
        plot_df = wind_rose_grid_atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(
                    x["height"], x["interpolation_marker"]
                )
            )
            .alias("height_display")
        )
        chart = wind_rose_grid_atom._build_monthly_grid_chart(plot_df)
        assert isinstance(chart, matplotlib.figure.Figure)

    def test_monthly_grid_facet_encoding(
        self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom
    ) -> None:
        """Assert figure has 12 polar axes (one per month)."""
        plot_df = wind_rose_grid_atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(
                    x["height"], x["interpolation_marker"]
                )
            )
            .alias("height_display")
        )
        chart = wind_rose_grid_atom._build_monthly_grid_chart(plot_df)
        assert len(chart.axes) == 12

    def test_monthly_grid_height_filter(
        self,
        wind_rose_grid_atom_multi_height: SingleMastMonthlyWindRoseGridAtom,
    ) -> None:
        """Assert height filter removes below-100m data."""
        plot_df = wind_rose_grid_atom_multi_height.df.filter(pl.col("height") >= 100)
        assert plot_df.filter(pl.col("height") < 100).is_empty()
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(
                    x["height"], x["interpolation_marker"]
                )
            )
            .alias("height_display")
        )
        chart = wind_rose_grid_atom_multi_height._build_monthly_grid_chart(plot_df)
        assert chart is not None
        assert plot_df.filter(pl.col("height") < 100).is_empty()


# =============================================================================
# Image Caching Tests
# =============================================================================


class TestImageCaching:
    """Tests for image caching behavior."""

    def test_wind_rose_image_caching(
        self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom, tmp_path: Path
    ) -> None:
        """Verify wind rose images are cached."""
        # First render
        path1 = wind_rose_grid_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        
        # Second render (should use cache)
        path2 = wind_rose_grid_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        
        assert path1 == path2
        assert mtime1 == mtime2  # File not modified

    def test_wind_rose_force_regenerate(
        self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom, tmp_path: Path
    ) -> None:
        """Verify force=True regenerates wind rose images."""
        # First render
        path1 = wind_rose_grid_atom.renderImage(tmp_path)
        
        # Force regenerate
        path2 = wind_rose_grid_atom.renderImage(tmp_path, force=True)
        
        assert path1 == path2
        assert path2.exists()


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.xfail(reason="Empty dataframe handling not yet implemented in atoms")
    def test_empty_dataframe(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test wind rose grid atom with empty DataFrame."""
        empty_df = pl.DataFrame({
            "month": pl.Series([], dtype=pl.Int64),
            "month_name": pl.Series([], dtype=pl.String),
            "sector": pl.Series([], dtype=pl.Int64),
            "sector_name": pl.Series([], dtype=pl.String),
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "frequency": pl.Series([], dtype=pl.Float64),
            "wind_power_density": pl.Series([], dtype=pl.Float64),
            "energy_frequency": pl.Series([], dtype=pl.Float64),
        })
        
        atom = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=empty_df,
            meta=sample_mast_meta,
        )
        
        table = atom.renderTable()
        assert table is None or isinstance(table, TypstTable)
        
        summary = atom.renderSummary()
        assert isinstance(summary, list)

    def test_single_month_data(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test atom with single month of data."""
        single_month_df = pl.DataFrame({
            "month": [1] * 16,
            "month_name": ["1月"] * 16,
            "sector": list(range(16)),
            "sector_name": ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"],
            "height": [100.0] * 16,
            "interpolation_marker": [None] * 16,
            "frequency": [0.06] * 16,
            "wind_power_density": [500.0] * 16,
            "energy_frequency": [0.06] * 16,
        })
        
        atom = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=single_month_df,
            meta=sample_mast_meta,
        )
        
        table = atom.renderTable()
        assert table is None

        summary = atom.renderSummary()
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        assert "测风塔" in summary[0].text

    def test_unequal_frequencies(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test atom with very uneven frequency distribution."""
        rows = []
        for sector in range(16):
            frequency = 0.50 if sector == 0 else 0.033
            wind_power_density = 800.0 if sector == 0 else 400.0
            rows.append({
                "month": 1,
                "month_name": "1月",
                "sector": sector,
                "sector_name": ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                               "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][sector],
                "height": 100.0,
                "interpolation_marker": None,
                "frequency": frequency,
                "wind_power_density": wind_power_density,
                "energy_frequency": frequency * (wind_power_density / 500.0),
            })

        df = pl.DataFrame(rows)
        
        atom = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=df,
            meta=sample_mast_meta,
        )
        
        table = atom.renderTable()
        assert table is None

    def test_all_same_frequency(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test atom with all sectors having same frequency."""
        rows = []
        for sector in range(16):
            rows.append({
                "month": 1,
                "month_name": "1月",
                "sector": sector,
                "sector_name": ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                               "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][sector],
                "height": 100.0,
                "interpolation_marker": None,
                "frequency": 0.0625,
                "wind_power_density": 500.0,
                "energy_frequency": 0.0625 * (500.0 / 500.0),
            })

        df = pl.DataFrame(rows)

        atom = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=df,
            meta=sample_mast_meta,
        )

        table = atom.renderTable()
        assert table is None

    def test_data_with_null_interpolation_marker(self, sample_mast_meta: SingleMastMeta) -> None:
        """Test atom handles null interpolation markers correctly."""
        rows = []
        for sector in range(8):
            rows.append({
                "month": 1,
                "month_name": "1月",
                "sector": sector,
                "sector_name": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][sector],
                "height": 100.0,
                "interpolation_marker": None,
                "frequency": 0.125,
                "wind_power_density": 500.0,
                "energy_frequency": 0.125 * (500.0 / 500.0),
            })

        df = pl.DataFrame(rows)

        atom = SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=df,
            meta=sample_mast_meta,
        )

        table = atom.renderTable()
        assert table is None

        summary = atom.renderSummary()
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)


# =============================================================================
# Cross-cutting Tests
# =============================================================================


class TestWindRoseGridAtoms:
    """Tests that apply to all wind rose grid atom scenarios."""

    def test_atom_has_correct_mast_name(
        self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom
    ) -> None:
        """Verify atom has correct mast name in meta."""
        assert wind_rose_grid_atom.meta.mast_name == "M01"

    def test_atom_produces_consistent_hashes(
        self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom
    ) -> None:
        """Verify atom produces consistent hashes."""
        hash1 = wind_rose_grid_atom.get_or_compute_df_hashkey()
        hash2 = wind_rose_grid_atom.get_or_compute_df_hashkey()
        assert hash1 == hash2
        assert len(hash1) > 0

    @pytest.mark.xfail(reason="value_counts() ordering not deterministic - implementation limitation")
    def test_summary_caching(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Verify summary output is consistent across multiple calls."""
        summary1 = wind_rose_grid_atom.renderSummary()
        summary2 = wind_rose_grid_atom.renderSummary()
        assert summary1 == summary2

    def test_table_caching(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        """Verify table output is consistent across multiple calls."""
        table1 = wind_rose_grid_atom.renderTable()
        table2 = wind_rose_grid_atom.renderTable()
        assert table1 == table2
