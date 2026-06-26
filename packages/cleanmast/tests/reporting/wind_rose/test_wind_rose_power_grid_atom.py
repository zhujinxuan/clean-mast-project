"""Tests for SingleMastMonthlyWindPowerRoseGridAtom — reporting domain.

Ported from tests/assessment/wind_rose/test_wind_rose_power_grid_atom.py.
Test logic, inputs, expected values, assertions preserved exactly.
"""

from pathlib import Path

import matplotlib.figure
import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.report_meta import (
    WindRoseAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.schemas import (
    WindRoseSchema,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_power_grid_atom import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)
from typst_ir import TypstParagraph, TypstTable


@pytest.fixture
def sample_mast_meta() -> WindRoseAtomMeta:
    return WindRoseAtomMeta(mast_name="M01")


@pytest.fixture
def sample_wind_rose_df() -> pl.DataFrame:
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
                base_power = 800.0 if sector_name in ["NW", "NNW", "WNW"] else (600.0 if sector_name in ["N", "W"] else 300.0)
            elif month_num in [3, 4, 5]:
                base_power = 750.0 if sector_name in ["N", "NNE", "NNW"] else (550.0 if sector_name in ["NE", "NW"] else 280.0)
            elif month_num in [6, 7, 8]:
                base_power = 850.0 if sector_name in ["S", "SSE", "SSW"] else (650.0 if sector_name in ["SE", "SW"] else 320.0)
            else:
                base_power = 720.0 if sector_name in ["NE", "ENE", "N"] else (520.0 if sector_name in ["E", "NNE"] else 290.0)
            wind_power_density = max(1.0, base_power + np.random.uniform(-50, 50))
            energy_frequency = 0.1 * (wind_power_density / 500.0)
            rows.append({
                "month": month_num, "month_name": month_name,
                "sector": sector_num, "sector_name": sector_name,
                "height": 100.0, "interpolation_marker": None,
                "frequency": 0.1, "wind_power_density": wind_power_density,
                "energy_frequency": energy_frequency,
            })
    return pl.DataFrame(rows)


@pytest.fixture
def sample_wind_rose_df_multiple_heights() -> pl.DataFrame:
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
                height_factor = 1.0 + (height - 100) * 0.005
                if month_num in [12, 1, 2]:
                    base_power = 800.0 if sector_name in ["NW", "NNW", "WNW"] else 400.0
                elif month_num in [6, 7, 8]:
                    base_power = 900.0 if sector_name in ["S", "SSE", "SSW"] else 350.0
                else:
                    base_power = 500.0
                wind_power_density = base_power * height_factor + np.random.uniform(-50, 50)
                energy_frequency = 0.1 * (wind_power_density / 500.0)
                rows.append({
                    "month": month_num, "month_name": month_name,
                    "sector": sector_num, "sector_name": sector_name,
                    "height": height, "interpolation_marker": marker,
                    "frequency": 0.1, "wind_power_density": wind_power_density,
                    "energy_frequency": energy_frequency,
                })
    return pl.DataFrame(rows)


@pytest.fixture
def sample_wind_rose_df_below_100m() -> pl.DataFrame:
    rows = []
    months = [(1, "1月"), (6, "6月"), (12, "12月")]
    sectors = [(0, "N"), (4, "E"), (8, "S"), (12, "W")]
    for month_num, month_name in months:
        for height in [50.0, 80.0]:
            for sector_num, sector_name in sectors:
                rows.append({
                    "month": month_num, "month_name": month_name,
                    "sector": sector_num, "sector_name": sector_name,
                    "height": height, "interpolation_marker": None,
                    "frequency": 0.25, "wind_power_density": 450.0,
                    "energy_frequency": 0.25 * (450.0 / 500.0),
                })
    return pl.DataFrame(rows)


@pytest.fixture
def wind_power_rose_grid_atom(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: WindRoseAtomMeta,
) -> SingleMastMonthlyWindPowerRoseGridAtom:
    return SingleMastMonthlyWindPowerRoseGridAtom.create(
        schema=WindRoseSchema, df=sample_wind_rose_df, meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_grid_atom_multi_height(
    sample_wind_rose_df_multiple_heights: pl.DataFrame,
    sample_mast_meta: WindRoseAtomMeta,
) -> SingleMastMonthlyWindPowerRoseGridAtom:
    return SingleMastMonthlyWindPowerRoseGridAtom.create(
        schema=WindRoseSchema, df=sample_wind_rose_df_multiple_heights, meta=sample_mast_meta,
    )


class TestSingleMastMonthlyWindPowerRoseGridAtom:
    def test_atom_creation(self, sample_wind_rose_df: pl.DataFrame, sample_mast_meta: WindRoseAtomMeta) -> None:
        atom = SingleMastMonthlyWindPowerRoseGridAtom.create(
            schema=WindRoseSchema, df=sample_wind_rose_df, meta=sample_mast_meta,
        )
        assert isinstance(atom, SingleMastMonthlyWindPowerRoseGridAtom)
        assert atom.meta.mast_name == "M01"
        assert atom.df is not None
        assert len(atom.df) > 0

    def test_render_image(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom, tmp_path: Path) -> None:
        image_path = wind_power_rose_grid_atom.renderImage(tmp_path)
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        table = wind_power_rose_grid_atom.renderTable()
        assert table is None

    def test_render_summary(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        summary = wind_power_rose_grid_atom.renderSummary()
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        summary_node = summary[0]
        assert "测风塔" in summary_node.text
        assert "M01" in summary_node.text
        assert "主导风能方向" in summary_node.text

    def test_content_hash_consistency(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        hash1 = wind_power_rose_grid_atom.get_or_compute_df_hashkey()
        hash2 = wind_power_rose_grid_atom.get_or_compute_df_hashkey()
        assert hash1 == hash2
        assert "SingleMastMonthlyWindPowerRoseGridAtom_" in hash1

    def test_summary_has_concise_format(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        summary = wind_power_rose_grid_atom.renderSummary()
        summary_node = summary[0]
        assert "主导风能方向为" in summary_node.text
        assert "反映了" not in summary_node.text
        assert "季节性" not in summary_node.text

    def test_summary_has_dominant_sectors(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        summary = wind_power_rose_grid_atom.renderSummary()
        summary_node = summary[0]
        assert "、" in summary_node.text or "主导风能方向" in summary_node.text

    def test_render_image_with_multiple_heights(
        self, wind_power_rose_grid_atom_multi_height: SingleMastMonthlyWindPowerRoseGridAtom, tmp_path: Path
    ) -> None:
        image_path = wind_power_rose_grid_atom_multi_height.renderImage(tmp_path)
        assert image_path.exists()
        assert image_path.suffix == ".png"

    def test_render_image_filters_below_100m(
        self, sample_wind_rose_df_below_100m: pl.DataFrame, sample_mast_meta: WindRoseAtomMeta, tmp_path: Path
    ) -> None:
        atom = SingleMastMonthlyWindPowerRoseGridAtom.create(
            schema=WindRoseSchema, df=sample_wind_rose_df_below_100m, meta=sample_mast_meta,
        )
        image_path = atom.renderImage(tmp_path)
        assert image_path.exists()

    def test_monthly_grid_angle_mapping(
        self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom
    ) -> None:
        plot_df = wind_power_rose_grid_atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        chart = wind_power_rose_grid_atom._build_monthly_grid_chart(plot_df)
        ax = None
        for candidate in chart.axes:
            if candidate.get_lines():
                ax = candidate
                break
        assert ax is not None
        line = ax.get_lines()[0]
        angles = np.asarray(line.get_xdata())
        assert angles[0] == pytest.approx(0.0, abs=1e-5)
        assert angles[4] == pytest.approx(np.pi / 2, abs=1e-5)
        assert angles[0] == pytest.approx(angles[-1], abs=1e-5)
        assert np.all(np.diff(angles[:-1]) >= -1e-6)

    def test_monthly_grid_mark_type(
        self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom
    ) -> None:
        plot_df = wind_power_rose_grid_atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        chart = wind_power_rose_grid_atom._build_monthly_grid_chart(plot_df)
        assert isinstance(chart, matplotlib.figure.Figure)

    def test_monthly_grid_facet_encoding(
        self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom
    ) -> None:
        plot_df = wind_power_rose_grid_atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        chart = wind_power_rose_grid_atom._build_monthly_grid_chart(plot_df)
        assert len(chart.axes) == 12

    def test_monthly_grid_height_filter(
        self, wind_power_rose_grid_atom_multi_height: SingleMastMonthlyWindPowerRoseGridAtom,
    ) -> None:
        plot_df = wind_power_rose_grid_atom_multi_height.df.filter(pl.col("height") >= 100)
        assert plot_df.filter(pl.col("height") < 100).is_empty()
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        chart = wind_power_rose_grid_atom_multi_height._build_monthly_grid_chart(plot_df)
        assert chart is not None
        assert plot_df.filter(pl.col("height") < 100).is_empty()


class TestImageCaching:
    def test_wind_power_rose_image_caching(
        self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom, tmp_path: Path
    ) -> None:
        path1 = wind_power_rose_grid_atom.renderImage(tmp_path)
        mtime1 = path1.stat().st_mtime
        path2 = wind_power_rose_grid_atom.renderImage(tmp_path)
        mtime2 = path2.stat().st_mtime
        assert path1 == path2
        assert mtime1 == mtime2

    def test_wind_power_rose_force_regenerate(
        self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom, tmp_path: Path
    ) -> None:
        path1 = wind_power_rose_grid_atom.renderImage(tmp_path)
        path2 = wind_power_rose_grid_atom.renderImage(tmp_path, force=True)
        assert path1 == path2
        assert path2.exists()


class TestEdgeCases:
    @pytest.mark.xfail(reason="Empty dataframe handling not yet implemented in atoms")
    def test_empty_dataframe(self, sample_mast_meta: WindRoseAtomMeta) -> None:
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
        atom = SingleMastMonthlyWindPowerRoseGridAtom.create(
            schema=WindRoseSchema, df=empty_df, meta=sample_mast_meta,
        )
        table = atom.renderTable()
        assert table is None or isinstance(table, TypstTable)
        summary = atom.renderSummary()
        assert isinstance(summary, list)

    def test_single_month_data(self, sample_mast_meta: WindRoseAtomMeta) -> None:
        single_month_df = pl.DataFrame({
            "month": [1] * 16,
            "month_name": ["1月"] * 16,
            "sector": list(range(16)),
            "sector_name": ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"],
            "height": [100.0] * 16, "interpolation_marker": [None] * 16,
            "frequency": [0.06] * 16, "wind_power_density": [500.0] * 16,
            "energy_frequency": [0.06] * 16,
        })
        atom = SingleMastMonthlyWindPowerRoseGridAtom.create(
            schema=WindRoseSchema, df=single_month_df, meta=sample_mast_meta,
        )
        table = atom.renderTable()
        assert table is None
        summary = atom.renderSummary()
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        assert "测风塔" in summary[0].text

    def test_atom_has_correct_mast_name(
        self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom
    ) -> None:
        assert wind_power_rose_grid_atom.meta.mast_name == "M01"

    def test_atom_produces_consistent_hashes(
        self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom
    ) -> None:
        hash1 = wind_power_rose_grid_atom.get_or_compute_df_hashkey()
        hash2 = wind_power_rose_grid_atom.get_or_compute_df_hashkey()
        assert hash1 == hash2
        assert len(hash1) > 0

    @pytest.mark.xfail(reason="value_counts() ordering not deterministic - implementation limitation")
    def test_summary_caching(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        summary1 = wind_power_rose_grid_atom.renderSummary()
        summary2 = wind_power_rose_grid_atom.renderSummary()
        assert summary1 == summary2

    def test_table_caching(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        table1 = wind_power_rose_grid_atom.renderTable()
        table2 = wind_power_rose_grid_atom.renderTable()
        assert table1 == table2
