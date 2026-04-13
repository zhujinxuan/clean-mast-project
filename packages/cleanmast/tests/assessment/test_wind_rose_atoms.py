"""Tests for WindRose report atoms."""

from pathlib import Path

import matplotlib.figure
import matplotlib.projections.polar
import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose import (
    WIND_ROSE_COLORS,
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_grid import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_power_grid import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindRoseSchema,
)
from matplotlib.figure import Figure
from typst_ir import TypstParagraph, TypstTable


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_wind_rose_data() -> pl.DataFrame:
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

    rows = []
    for month in [1, 2, 3]:
        month_name = f"{month}月"
        for height, marker in [(50.0, None), (100.0, None), (120.0, "外推"), (125.0, "内插")]:
            base_frequencies = [
                0.03, 0.04, 0.05, 0.06, 0.08, 0.07, 0.06, 0.05,
                0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.09, 0.04
            ]

            variation = (height - 100) / 1000
            frequencies = [max(0.01, f + variation * ((i % 3) - 1) * 0.01) for i, f in enumerate(base_frequencies)]
            total = sum(frequencies)
            frequencies = [f / total for f in frequencies]

            base_power = 200 + (height - 50) * 2
            raw_energy = [f * (1 + 0.05 * (s % 4)) for s, f in enumerate(frequencies)]
            energy_total = sum(raw_energy)
            energy_frequencies = [e / energy_total for e in raw_energy]

            for sector, freq in enumerate(frequencies):
                power = base_power * 1.1 * (1 + freq * 2)
                rows.append({
                    "month": month,
                    "month_name": month_name,
                    "sector": sector,
                    "sector_name": sector_names[sector],
                    "height": height,
                    "frequency": freq,
                    "wind_power_density": max(50.0, power),
                    "energy_frequency": energy_frequencies[sector],
                    "interpolation_marker": marker,
                })

    return pl.DataFrame(rows)


@pytest.fixture
def wind_frequency_rose_atom(
    sample_wind_rose_data: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastMonthlyWindFrequencyRoseAtom:
    return SingleMastMonthlyWindFrequencyRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_data,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_atom(
    sample_wind_rose_data: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindPowerRoseAtom:
    return SingleMastWindPowerRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_data,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_rose_grid_atom(
    sample_wind_rose_data: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastMonthlyWindRoseGridAtom:
    return SingleMastMonthlyWindRoseGridAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_data,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_grid_atom(
    sample_wind_rose_data: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastMonthlyWindPowerRoseGridAtom:
    return SingleMastMonthlyWindPowerRoseGridAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_data,
        meta=sample_mast_meta,
    )


class TestSingleMastMonthlyWindFrequencyRoseAtom:
    def test_render_image(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom, tmp_path: Path) -> None:
        image_path = wind_frequency_rose_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        table = wind_frequency_rose_atom.renderTable()
        
        assert isinstance(table, TypstTable)
        assert table.caption == "M01 风向频率分布表"
        assert table.headers == ["风向", "100m", "120m 外推", "125m 内插"]
        assert table.data[0] == ["N", "2.94", "2.92", "2.92"]
        assert table.data[13] == ["WNW", "11.76", "11.77", "11.77"]

    def test_default_captions(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        assert wind_frequency_rose_atom.default_image_caption == "M01 风向频率玫瑰图"
        assert wind_frequency_rose_atom.default_table_caption == "M01 风向频率分布表"

    def test_render_summary(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        summary = wind_frequency_rose_atom.renderSummary()
        
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        text = summary[0].text
        assert "测风塔在" in text
        assert "主风向为" in text
        assert "次主风向为" in text
        assert "125m(内插)" in text
        assert "WNW(11.8%)" in text
        assert "W(9.8%)" in text

    def test_frequency_rose_mark_type(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        atom = wind_frequency_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        chart = atom._build_frequency_rose_chart(plot_df)
        assert isinstance(chart, matplotlib.figure.Figure)

    def test_frequency_rose_color_encoding(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        atom = wind_frequency_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        chart = atom._build_frequency_rose_chart(plot_df)
        ax = chart.axes[0]
        lines = ax.get_lines()
        height_order = (
            plot_df.select(["height", "height_display"])
            .unique()
            .sort("height", descending=True)["height_display"]
            .to_list()
        )
        assert len(lines) == len(height_order)
        for i, line in enumerate(lines):
            assert line.get_color() == WIND_ROSE_COLORS[i % len(WIND_ROSE_COLORS)]

    def test_frequency_rose_has_polar_axes(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        atom = wind_frequency_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        chart = atom._build_frequency_rose_chart(plot_df)
        assert isinstance(chart.axes[0], matplotlib.projections.polar.PolarAxes)

    def test_frequency_rose_angle_mapping(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        atom = wind_frequency_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        plot_df = plot_df.filter(pl.col("month") == 1)
        chart = atom._build_frequency_rose_chart(plot_df)
        ax = chart.axes[0]
        line = ax.get_lines()[0]
        angles = np.asarray(line.get_xdata())
        assert angles[0] == pytest.approx(0.0, abs=1e-5)
        assert angles[4] == pytest.approx(np.pi / 2, abs=1e-5)
        assert angles[0] == angles[-1]
        assert np.all(np.diff(angles[:-1]) >= -1e-6)


class TestSingleMastWindPowerRoseAtom:
    def test_render_image(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom, tmp_path: Path) -> None:
        image_path = wind_power_rose_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_power_rose_mark_type(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        atom = wind_power_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        chart = atom._build_power_rose_chart(plot_df)
        assert isinstance(chart, matplotlib.figure.Figure)

    def test_power_rose_color_encoding(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        atom = wind_power_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        chart = atom._build_power_rose_chart(plot_df)
        ax = chart.axes[0]
        lines = ax.get_lines()
        height_order = (
            plot_df.select(["height", "height_display"])
            .unique()
            .sort("height", descending=True)["height_display"]
            .to_list()
        )
        assert len(lines) == len(height_order)
        for i, line in enumerate(lines):
            assert line.get_color() == WIND_ROSE_COLORS[i % len(WIND_ROSE_COLORS)]

    def test_power_rose_has_polar_axes(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        atom = wind_power_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        chart = atom._build_power_rose_chart(plot_df)
        assert isinstance(chart.axes[0], matplotlib.projections.polar.PolarAxes)

    def test_power_rose_angle_mapping(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        atom = wind_power_rose_atom
        plot_df = atom.df.filter(pl.col("height") >= 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(lambda x: get_height_display_name(x["height"], x["interpolation_marker"]))
            .alias("height_display")
        )
        plot_df = plot_df.with_columns((pl.col("frequency") * 100).alias("frequency_pct"))
        plot_df = plot_df.filter(pl.col("month") == 1)
        chart = atom._build_power_rose_chart(plot_df)
        ax = chart.axes[0]
        line = ax.get_lines()[0]
        angles = np.asarray(line.get_xdata())
        assert angles[0] == pytest.approx(0.0, abs=1e-5)
        assert angles[4] == pytest.approx(np.pi / 2, abs=1e-5)
        assert angles[0] == angles[-1]
        assert np.all(np.diff(angles[:-1]) >= -1e-6)

    def test_render_table(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        table = wind_power_rose_atom.renderTable()
        
        assert isinstance(table, TypstTable)
        assert table.caption == "M01 风能频率分布表"
        assert table.headers == ["风向", "100m", "120m 外推", "125m 内插"]
        assert table.data[0] == ["N", "2.74", "2.72", "2.72"]
        assert table.data[13] == ["WNW", "11.51", "11.51", "11.51"]

    def test_default_captions(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        assert wind_power_rose_atom.default_image_caption == "M01 风能频率玫瑰图"
        assert wind_power_rose_atom.default_table_caption == "M01 风能频率分布表"

    def test_render_summary(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        summary = wind_power_rose_atom.renderSummary()
        
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
        text = summary[0].text
        assert "测风塔在" in text
        assert "主导风能方向为" in text
        assert "次主导风能方向为" in text
        assert "125m(内插)" in text
        assert "WNW(11.5%)" in text
        assert "W(9.1%)" in text

    def test_power_rose_image_uses_energy_frequency(
        self,
        wind_power_rose_atom: SingleMastWindPowerRoseAtom,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: list[pl.DataFrame] = []

        def mock_build(atom_self: SingleMastWindPowerRoseAtom, plot_df: pl.DataFrame) -> Figure:
            captured.append(plot_df)
            return Figure()

        monkeypatch.setattr(SingleMastWindPowerRoseAtom, "_build_power_rose_chart", mock_build)
        wind_power_rose_atom.renderImage(tmp_path)

        assert len(captured) == 1
        plot_df = captured[0]

        wnw_125 = plot_df.filter((pl.col("sector_name") == "WNW") & (pl.col("height") == 125.0))
        assert wnw_125["frequency_pct"].item() == pytest.approx(11.5148677, abs=1e-5)

        raw_freq_pct = (
            wind_power_rose_atom.df
            .filter((pl.col("sector_name") == "WNW") & (pl.col("height") == 125.0))
            ["frequency"]
            .mean()
            * 100
        )
        assert raw_freq_pct == pytest.approx(11.7675901, abs=1e-5)
        assert wnw_125["frequency_pct"].item() != pytest.approx(raw_freq_pct, abs=1e-3)


class TestSingleMastMonthlyWindRoseGridAtom:
    def test_render_image(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom, tmp_path: Path) -> None:
        image_path = wind_rose_grid_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        table = wind_rose_grid_atom.renderTable()
        assert table is None

    def test_default_captions(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        assert wind_rose_grid_atom.default_image_caption == "M01 各高度（100m 以上）各月风向玫瑰图"
        assert wind_rose_grid_atom.default_table_caption == "M01 月风向频率分布表"

    def test_render_summary(self, wind_rose_grid_atom: SingleMastMonthlyWindRoseGridAtom) -> None:
        summary = wind_rose_grid_atom.renderSummary()
        
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)


class TestSingleMastMonthlyWindPowerRoseGridAtom:
    def test_render_image(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom, tmp_path: Path) -> None:
        image_path = wind_power_rose_grid_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        table = wind_power_rose_grid_atom.renderTable()
        assert table is None

    def test_default_captions(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        assert wind_power_rose_grid_atom.default_image_caption == "M01 各高度（100m 以上）各月风能玫瑰图"
        assert wind_power_rose_grid_atom.default_table_caption == "M01 月风能频率分布表"

    def test_render_summary(self, wind_power_rose_grid_atom: SingleMastMonthlyWindPowerRoseGridAtom) -> None:
        summary = wind_power_rose_grid_atom.renderSummary()
        
        assert isinstance(summary, list)
        assert isinstance(summary[0], TypstParagraph)
