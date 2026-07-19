"""Tests for extreme wind atoms and assembly — reporting domain."""

from pathlib import Path

import polars as pl
from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.subdomains.extreme_wind.assemble import (
    build_iec_standards_atom,
    build_method1_atom,
    build_method3_atom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.iec_atom import (
    IEC_STANDARDS_DATA,
    IECStandardsAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method1_atom import (
    Method1Atom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method2_atom import (
    Method2ParamsAtom,
    Method2QQExtremeAtom,
    Method2QQSustainedAtom,
    Method2ResultAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method3_atom import (
    Method3Atom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.report_meta import (
    ExtremeWindAtomMeta,
    IECStandardsAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.schemas import (
    FiftyYearMaxWindComparisonSchema,
    FiftyYearMaxWindMethod1DetailSchema,
    FiftyYearMaxWindResultSchema,
    GumbelParameterSchema,
    IECStandardsSchema,
    IECWindClassSchema,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.summary_atom import (
    ComparisonSustainedAtom,
    IECWindClassAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.section import (
    ExtremeWindSection,
)

# =============================================================================
# Report Meta
# =============================================================================


class TestReportMeta:
    def test_get_height_display_name_no_marker(self) -> None:
        assert get_height_display_name(70.0, "") == "70m"

    def test_get_height_display_name_with_extrapolation(self) -> None:
        assert get_height_display_name(70.0, "外推") == "70m(外推)"

    def test_get_height_display_name_with_interpolation(self) -> None:
        assert get_height_display_name(120.0, "内插") == "120m(内插)"


# =============================================================================
# Method 1 Atom
# =============================================================================


class TestMethod1Atom:
    def _make_atom(self, df: pl.DataFrame) -> Method1Atom:
        meta = ExtremeWindAtomMeta(mast_name="TestMast")
        return Method1Atom.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            df=df,
            meta=meta,
        )

    def test_render_table_pivots_sustained_and_extreme(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0, 120.0, 120.0],
            "interpolation_marker": [None, None, None, None],
            "wind_speed_type": ["sustained", "extreme", "sustained", "extreme"],
            "method": ["method1", "method1", "method1", "method1"],
            "max_wind_speed": [30.0, 42.0, 35.0, 49.0],
            "standard_density_wind_speed": [31.0, 43.0, 36.0, 50.0],
            "average_wind_speed": [6.0, 6.0, 7.0, 7.0],
            "air_density": [1.225, 1.225, 1.225, 1.225],
        })
        atom = self._make_atom(df)
        table = atom.renderTable()
        assert table is not None
        assert "高度(m)" in table.headers
        assert len(table.data) == 2

    def test_render_image_returns_empty_path(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        atom = self._make_atom(df)
        path = atom.renderImage(output_dir=Path("/tmp"))
        assert path == Path()

    def test_render_summary_returns_paragraph(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        atom = self._make_atom(df)
        paragraphs = atom.renderSummary()
        assert len(paragraphs) == 1
        assert "TestMast测风塔" in paragraphs[0].text


# =============================================================================
# Method 2 Atoms
# =============================================================================


class TestMethod2Atoms:
    def test_result_atom_render_table(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method2", "method2"],
            "max_wind_speed": [25.0, 35.0],
            "standard_density_wind_speed": [26.0, 36.0],
            "observed_max": [20.0, 30.0],
        })
        atom = Method2ResultAtom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        table = atom.renderTable()
        assert table is not None
        assert "高度(m)" in table.headers
        assert len(table.data) == 2

    def test_params_atom_render_table(self) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "wind_speed_type": ["sustained"],
            "mu": [20.0],
            "beta": [3.0],
            "sample_count": [50],
            "sample_mean": [21.0],
            "sample_std": [4.0],
            "sample_data": [[20.0, 22.0]],
        })
        atom = Method2ParamsAtom.create(
            schema=GumbelParameterSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        table = atom.renderTable()
        assert table is not None
        assert "μ" in table.headers
        assert len(table.data) == 1

    def test_qq_sustained_atom_generates_png(self, tmp_path: Path) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "wind_speed_type": ["sustained"],
            "mu": [20.0],
            "beta": [3.0],
            "sample_count": [50],
            "sample_mean": [21.0],
            "sample_std": [4.0],
            "sample_data": [[20.0 + i for i in range(50)]],
        })
        atom = Method2QQSustainedAtom.create(
            schema=GumbelParameterSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        path = atom.renderImage(tmp_path)
        assert path.exists()
        assert path.suffix == ".png"

    def test_qq_extreme_atom_generates_png(self, tmp_path: Path) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "wind_speed_type": ["extreme"],
            "mu": [20.0],
            "beta": [3.0],
            "sample_count": [50],
            "sample_mean": [21.0],
            "sample_std": [4.0],
            "sample_data": [[20.0 + i for i in range(50)]],
        })
        atom = Method2QQExtremeAtom.create(
            schema=GumbelParameterSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        path = atom.renderImage(tmp_path)
        assert path.exists()
        assert path.suffix == ".png"


# =============================================================================
# Method 3 Atom
# =============================================================================


class TestMethod3Atom:
    def test_render_table(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method3", "method3"],
            "max_wind_speed": [25.0, 35.0],
            "standard_density_wind_speed": [26.0, 36.0],
            "observed_max": [20.0, 28.0],
        })
        atom = Method3Atom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        table = atom.renderTable()
        assert table is not None
        assert len(table.data) == 2

    def test_render_summary(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method3", "method3"],
            "max_wind_speed": [25.0, 35.0],
            "standard_density_wind_speed": [26.0, 36.0],
            "observed_max": [20.0, 28.0],
        })
        atom = Method3Atom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        paragraphs = atom.renderSummary()
        assert len(paragraphs) == 1
        assert "TestMast" in paragraphs[0].text


# =============================================================================
# IEC Standards Atom
# =============================================================================


class TestIECStandardsAtom:
    def test_render_table(self) -> None:
        atom = IECStandardsAtom.create(
            schema=IECStandardsSchema,
            df=IEC_STANDARDS_DATA,
            meta=IECStandardsAtomMeta(),
        )
        table = atom.renderTable()
        assert table is not None
        assert "IEC 等级" in table.headers
        assert len(table.data) == 4


# =============================================================================
# Summary Atoms
# =============================================================================


class TestSummaryAtoms:
    def test_comparison_sustained_render_table(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 120.0],
            "method1": [30.0, 35.0],
            "method2": [31.0, 36.0],
            "method3": [29.0, 34.0],
            "conservative_max": [31.0, 36.0],
            "wind_speed_type": ["sustained", "sustained"],
            "interpolation_marker": ["", ""],
        })
        atom = ComparisonSustainedAtom.create(
            schema=FiftyYearMaxWindComparisonSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        table = atom.renderTable()
        assert table is not None
        assert len(table.data) == 2

    def test_iec_wind_class_render_table(self) -> None:
        df = pl.DataFrame({
            "wind_class": ["I", "II", "III", "S"],
            "height": [None, None, None, None],
            "sustained_threshold": [50.0, 42.5, 37.5, 0.0],
            "extreme_threshold": [70.0, 59.5, 52.5, 0.0],
            "conservative_sustained": [None, None, None, None],
            "conservative_extreme": [None, None, None, None],
        })
        atom = IECWindClassAtom.create(
            schema=IECWindClassSchema,
            df=df,
            meta=ExtremeWindAtomMeta(mast_name="TestMast"),
        )
        table = atom.renderTable()
        assert table is not None
        assert len(table.data) == 4


# =============================================================================
# Assembly
# =============================================================================


class TestAssembly:
    def test_build_method1_atom(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        atom = build_method1_atom("TestMast", df)
        assert isinstance(atom, Method1Atom)

    def test_build_iec_standards_atom(self) -> None:
        atom = build_iec_standards_atom()
        assert isinstance(atom, IECStandardsAtom)

    def test_build_method3_atom(self) -> None:
        sus = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["sustained"],
            "method": ["method3"],
            "max_wind_speed": [25.0],
            "standard_density_wind_speed": [26.0],
            "observed_max": [20.0],
        })
        ext = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["extreme"],
            "method": ["method3"],
            "max_wind_speed": [35.0],
            "standard_density_wind_speed": [36.0],
            "observed_max": [28.0],
        })
        atom = build_method3_atom("TestMast", sus, ext)
        assert isinstance(atom, Method3Atom)
        assert len(atom.df) == 1


# =============================================================================
# Section
# =============================================================================


class TestExtremeWindSection:
    def test__from_computed_results(self) -> None:
        m1 = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        section = ExtremeWindSection._from_computed_results(
            mast_name="TestMast",
            method1_df=m1,
        )
        assert section.iec_atoms is not None
        assert section.method1_atoms is not None
        assert len(section.summary_atoms) >= 1

    def test_render_ir(self) -> None:
        m1 = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        section = ExtremeWindSection._from_computed_results(
            mast_name="TestMast",
            method1_df=m1,
        )
        ir = section.render_ir(images_dir=Path("/tmp/images"))
        assert ir.heading.text == "五十年一遇最大风速"
        assert len(ir.subsections) >= 2  # IEC + M1


# =============================================================================
# Gumbel Q-Q plot service
# =============================================================================


class TestGumbelQQ:
    def test_monte_carlo_band_correctness(self) -> None:
        from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.gumbel_qq import (
            generate_qq_monte_carlo_bands,
        )
        mu = 10.0
        beta = 2.0
        n = 50
        empirical_probs = [i / (n + 1) for i in range(1, n + 1)]
        df = generate_qq_monte_carlo_bands(
            empirical_probs=empirical_probs, mu=mu, beta=beta, n=n, n_monte_carlo=500,
        )
        lower = df["lower"].to_list()
        quantiles = df["quantiles"].to_list()
        upper = df["upper"].to_list()
        assert len(lower) == n
        for lo, q, u in zip(lower, quantiles, upper):
            assert lo <= q
            assert q <= u

    def test_generate_subgrid_returns_png(self, tmp_path: Path) -> None:
        from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.gumbel_qq import (
            generate_gumbel_qq_subgrid,
        )
        data_list = [{
            "height": 100.0,
            "wind_data": [20.0 + i for i in range(50)],
            "mu": 20.0,
            "beta": 3.0,
        }]
        path = generate_gumbel_qq_subgrid(
            data_list=data_list,
            mast_name="TestMast",
            output_dir=tmp_path,
            wind_speed_type="sustained",
        )
        assert path.exists()
        assert path.suffix == ".png"
