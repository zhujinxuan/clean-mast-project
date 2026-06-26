"""Tests for fifty-year max wind summary calculator, atoms, builder, and subsection."""

from datetime import datetime
from pathlib import Path

import polars as pl
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_summary_atom import (
    SingleMastFiftyYearMaxWindComparisonExtremeAtom,
    SingleMastFiftyYearMaxWindComparisonSustainedAtom,
    SingleMastIECWindClassAtom,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._builder_summary import (
    SummaryBuilder,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._calc_summary import (
    SummaryCalculator,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.summary_subsection import (
    SummarySubsection,
)
from cleanmast.subdomains.assessment.shared.ir_types import TypstSection
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindComparisonSchema,
    FiftyYearMaxWindMethod1DetailSchema,
    FiftyYearMaxWindResultSchema,
    IECWindClassSchema,
)


def make_metadata(mast_name: str = "TestMast") -> AnalysisMetadata:
    return AnalysisMetadata(mast_name=mast_name, time_range="", created_at=datetime.now())


class TestSummaryCalculator:
    """Tests for SummaryCalculator."""

    def test_calculate_all_methods_present(self) -> None:
        method1_df = pl.DataFrame({
            "height": [100.0, 100.0, 120.0, 120.0],
            "interpolation_marker": [None, None, None, None],
            "wind_speed_type": ["sustained", "extreme", "sustained", "extreme"],
            "method": ["method1", "method1", "method1", "method1"],
            "max_wind_speed": [30.0, 42.0, 35.0, 49.0],
            "standard_density_wind_speed": [31.0, 43.0, 36.0, 50.0],
            "average_wind_speed": [6.0, 6.0, 7.0, 7.0],
            "air_density": [1.225, 1.225, 1.225, 1.225],
        })
        method2_sustained_df = pl.DataFrame({
            "height": [100.0, 120.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "sustained"],
            "method": ["method2", "method2"],
            "max_wind_speed": [32.0, 37.0],
            "standard_density_wind_speed": [33.0, 38.0],
            "observed_max": [20.0, 22.0],
        })
        method2_extreme_df = pl.DataFrame({
            "height": [100.0, 120.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["extreme", "extreme"],
            "method": ["method2", "method2"],
            "max_wind_speed": [44.0, 51.0],
            "standard_density_wind_speed": [45.0, 52.0],
            "observed_max": [28.0, 30.0],
        })
        method3_sustained_df = pl.DataFrame({
            "height": [100.0, 120.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "sustained"],
            "method": ["method3", "method3"],
            "max_wind_speed": [34.0, 39.0],
            "standard_density_wind_speed": [35.0, 40.0],
            "observed_max": [21.0, 23.0],
        })
        method3_extreme_df = pl.DataFrame({
            "height": [100.0, 120.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["extreme", "extreme"],
            "method": ["method3", "method3"],
            "max_wind_speed": [46.0, 53.0],
            "standard_density_wind_speed": [47.0, 54.0],
            "observed_max": [29.0, 31.0],
        })

        method1_result = AnalysisResult.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            data=method1_df,
            metadata=make_metadata(),
        )
        method2_sustained = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method2_sustained_df,
            metadata=make_metadata(),
        )
        method2_extreme = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method2_extreme_df,
            metadata=make_metadata(),
        )
        method3_sustained = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method3_sustained_df,
            metadata=make_metadata(),
        )
        method3_extreme = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method3_extreme_df,
            metadata=make_metadata(),
        )

        calculator = SummaryCalculator()
        sustained_comp, extreme_comp, iec = calculator.calculate(
            method1_result=method1_result,
            method2_sustained=method2_sustained,
            method2_extreme=method2_extreme,
            method3_sustained=method3_sustained,
            method3_extreme=method3_extreme,
        )

        assert sustained_comp.schema == FiftyYearMaxWindComparisonSchema
        assert extreme_comp.schema == FiftyYearMaxWindComparisonSchema
        assert iec.schema == IECWindClassSchema

        assert len(sustained_comp.data) == 2
        assert len(extreme_comp.data) == 2
        assert len(iec.data) == 6

        row_100_sustained = sustained_comp.data.filter(pl.col("height") == 100.0).row(0, named=True)
        assert row_100_sustained["method1"] == 31.0
        assert row_100_sustained["method2"] == 33.0
        assert row_100_sustained["method3"] == 35.0
        assert row_100_sustained["conservative_max"] == 35.0
        assert row_100_sustained["wind_speed_type"] == "sustained"

        row_100_extreme = extreme_comp.data.filter(pl.col("height") == 100.0).row(0, named=True)
        assert row_100_extreme["method1"] == 43.0
        assert row_100_extreme["method2"] == 45.0
        assert row_100_extreme["method3"] == 47.0
        assert row_100_extreme["conservative_max"] == 47.0
        assert row_100_extreme["wind_speed_type"] == "extreme"

        # IEC classification: 100m sustained=35.0, extreme=47.0 -> III
        # 120m sustained=40.0, extreme=54.0 -> II
        iec_rows = iec.data.to_dicts()
        assert len(iec_rows) == 6
        ref_classes = [r["wind_class"] for r in iec_rows[:4]]
        assert ref_classes == ["I", "II", "III", "S"]

        row_100_iec = iec.data.filter((pl.col("height") == 100.0) & (pl.col("conservative_sustained").is_not_null())).row(0, named=True)
        assert row_100_iec["wind_class"] == "III"
        assert row_100_iec["conservative_sustained"] == 35.0
        assert row_100_iec["conservative_extreme"] == 47.0

        row_120_iec = iec.data.filter((pl.col("height") == 120.0) & (pl.col("conservative_sustained").is_not_null())).row(0, named=True)
        assert row_120_iec["wind_class"] == "II"
        assert row_120_iec["conservative_sustained"] == 40.0
        assert row_120_iec["conservative_extreme"] == 54.0

    def test_calculate_missing_method_values(self) -> None:
        method1_df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        empty_df = FiftyYearMaxWindResultSchema.validate(pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "method": pl.Series([], dtype=pl.String),
            "max_wind_speed": pl.Series([], dtype=pl.Float64),
            "standard_density_wind_speed": pl.Series([], dtype=pl.Float64),
            "observed_max": pl.Series([], dtype=pl.Float64),
        }), cast=True)

        method1_result = AnalysisResult.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            data=method1_df,
            metadata=make_metadata(),
        )
        empty_result = AnalysisResult(
            schema=FiftyYearMaxWindResultSchema,
            data=empty_df,
            metadata=make_metadata(),
        )

        calculator = SummaryCalculator()
        sustained_comp, extreme_comp, iec = calculator.calculate(
            method1_result=method1_result,
            method2_sustained=empty_result,
            method2_extreme=empty_result,
            method3_sustained=empty_result,
            method3_extreme=empty_result,
        )

        row_100 = sustained_comp.data.filter(pl.col("height") == 100.0).row(0, named=True)
        assert row_100["method1"] == 31.0
        assert row_100["method2"] == 0.0
        assert row_100["method3"] == 0.0
        assert row_100["conservative_max"] == 31.0

    def test_iec_wind_class_values(self) -> None:
        method1_df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        empty_df = FiftyYearMaxWindResultSchema.validate(pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "method": pl.Series([], dtype=pl.String),
            "max_wind_speed": pl.Series([], dtype=pl.Float64),
            "standard_density_wind_speed": pl.Series([], dtype=pl.Float64),
            "observed_max": pl.Series([], dtype=pl.Float64),
        }), cast=True)

        method1_result = AnalysisResult.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            data=method1_df,
            metadata=make_metadata(),
        )
        empty_result = AnalysisResult(
            schema=FiftyYearMaxWindResultSchema,
            data=empty_df,
            metadata=make_metadata(),
        )

        calculator = SummaryCalculator()
        _, _, iec = calculator.calculate(
            method1_result=method1_result,
            method2_sustained=empty_result,
            method2_extreme=empty_result,
            method3_sustained=empty_result,
            method3_extreme=empty_result,
        )

        # 4 reference rows + 1 classification row for 100m
        assert len(iec.data) == 5
        ref_classes = iec.data.filter(pl.col("height").is_null())["wind_class"].to_list()
        assert ref_classes == ["I", "II", "III", "S"]

        i_row = iec.data.filter((pl.col("wind_class") == "I") & (pl.col("height").is_null())).row(0, named=True)
        assert i_row["sustained_threshold"] == 50.0
        assert i_row["extreme_threshold"] == 70.0

        class_row = iec.data.filter(pl.col("height") == 100.0).row(0, named=True)
        assert class_row["wind_class"] == "III"
        assert class_row["conservative_sustained"] == 31.0
        assert class_row["conservative_extreme"] == 43.0


class TestComparisonSustainedAtom:
    """Tests for SingleMastFiftyYearMaxWindComparisonSustainedAtom."""

    def _make_atom(self, df: pl.DataFrame) -> SingleMastFiftyYearMaxWindComparisonSustainedAtom:
        meta = SingleMastMeta(mast_name="TestMast")
        return SingleMastFiftyYearMaxWindComparisonSustainedAtom.create(
            schema=FiftyYearMaxWindComparisonSchema,
            df=df,
            meta=meta,
        )

    def test_render_table_with_all_methods(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 120.0],
            "method1": [31.0, 36.0],
            "method2": [33.0, 38.0],
            "method3": [35.0, 40.0],
            "conservative_max": [35.0, 40.0],
            "wind_speed_type": ["sustained", "sustained"],
            "interpolation_marker": [None, "外推"],
        })
        atom = self._make_atom(df)
        table = atom.renderTable()

        assert table is not None
        assert table.headers == ["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"]
        assert len(table.data) == 2

        row_100 = next(r for r in table.data if r[0] == "100m")
        assert row_100[1] == "31.00"
        assert row_100[2] == "33.00"
        assert row_100[3] == "35.00"
        assert row_100[4] == "35.00"

        row_120 = next(r for r in table.data if r[0] == "120m 外推")
        assert row_120[1] == "36.00"
        assert row_120[2] == "38.00"
        assert row_120[3] == "40.00"
        assert row_120[4] == "40.00"

    def test_render_table_missing_methods_show_empty(self) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "method1": [31.0],
            "method2": [0.0],
            "method3": [35.0],
            "conservative_max": [35.0],
            "wind_speed_type": ["sustained"],
            "interpolation_marker": [None],
        })
        atom = self._make_atom(df)
        table = atom.renderTable()

        assert table is not None
        row = table.data[0]
        assert row[1] == "31.00"
        assert row[2] == ""
        assert row[3] == "35.00"
        assert row[4] == "35.00"

    def test_render_image_returns_empty_path(self) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "method1": [31.0],
            "method2": [33.0],
            "method3": [35.0],
            "conservative_max": [35.0],
            "wind_speed_type": ["sustained"],
            "interpolation_marker": [None],
        })
        atom = self._make_atom(df)
        assert atom.renderImage(output_dir=Path("/tmp")) == Path()

    def test_render_summary_returns_paragraph(self) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "method1": [31.0],
            "method2": [33.0],
            "method3": [35.0],
            "conservative_max": [35.0],
            "wind_speed_type": ["sustained"],
            "interpolation_marker": [None],
        })
        atom = self._make_atom(df)
        paragraphs = atom.renderSummary()

        assert len(paragraphs) == 1
        assert "TestMast测风塔" in paragraphs[0].text
        assert "持续风速" in paragraphs[0].text
        assert "100m" in paragraphs[0].text


class TestComparisonExtremeAtom:
    """Tests for SingleMastFiftyYearMaxWindComparisonExtremeAtom."""

    def _make_atom(self, df: pl.DataFrame) -> SingleMastFiftyYearMaxWindComparisonExtremeAtom:
        meta = SingleMastMeta(mast_name="TestMast")
        return SingleMastFiftyYearMaxWindComparisonExtremeAtom.create(
            schema=FiftyYearMaxWindComparisonSchema,
            df=df,
            meta=meta,
        )

    def test_render_table_with_all_methods(self) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "method1": [43.0],
            "method2": [45.0],
            "method3": [47.0],
            "conservative_max": [47.0],
            "wind_speed_type": ["extreme"],
            "interpolation_marker": [None],
        })
        atom = self._make_atom(df)
        table = atom.renderTable()

        assert table is not None
        assert table.headers == ["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"]
        row = table.data[0]
        assert row[0] == "100m"
        assert row[1] == "43.00"
        assert row[2] == "45.00"
        assert row[3] == "47.00"
        assert row[4] == "47.00"

    def test_render_summary_returns_paragraph(self) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "method1": [43.0],
            "method2": [0.0],
            "method3": [47.0],
            "conservative_max": [47.0],
            "wind_speed_type": ["extreme"],
            "interpolation_marker": [None],
        })
        atom = self._make_atom(df)
        paragraphs = atom.renderSummary()

        assert len(paragraphs) == 1
        assert "TestMast测风塔" in paragraphs[0].text
        assert "极端风速" in paragraphs[0].text
        assert "100m" in paragraphs[0].text


class TestIECWindClassAtom:
    """Tests for SingleMastIECWindClassAtom."""

    def _make_atom(self, df: pl.DataFrame) -> SingleMastIECWindClassAtom:
        meta = SingleMastMeta(mast_name="TestMast")
        return SingleMastIECWindClassAtom.create(
            schema=IECWindClassSchema,
            df=df,
            meta=meta,
        )

    def test_render_table(self) -> None:
        df = pl.DataFrame({
            "wind_class": ["I", "II", "III", "S", "II"],
            "height": [None, None, None, None, 100.0],
            "sustained_threshold": [50.0, 42.5, 37.5, 0.0, 0.0],
            "extreme_threshold": [70.0, 59.5, 52.5, 0.0, 0.0],
            "conservative_sustained": [None, None, None, None, 35.0],
            "conservative_extreme": [None, None, None, None, 48.0],
        })
        atom = self._make_atom(df)
        table = atom.renderTable()

        assert table is not None
        assert table.headers == ["高度(m)", "风区等级", "最大持续风速Vref(m/s)", "极大极端风速Ve50(m/s)"]
        assert len(table.data) == 5

        i_row = next(r for r in table.data if r[1] == "I类")
        assert i_row[0] == "—"
        assert i_row[2] == "50.0"
        assert i_row[3] == "70.0"

        s_row = next(r for r in table.data if r[1] == "S类")
        assert s_row[0] == "—"
        assert s_row[2] == "场址专用"
        assert s_row[3] == "场址专用"

        class_row = next(r for r in table.data if r[0] == "100.0")
        assert class_row[1] == "II类"
        assert class_row[2] == "35.00"
        assert class_row[3] == "48.00"

    def test_render_image_returns_empty_path(self) -> None:
        df = pl.DataFrame({
            "wind_class": ["I"],
            "height": [None],
            "sustained_threshold": [50.0],
            "extreme_threshold": [70.0],
            "conservative_sustained": [None],
            "conservative_extreme": [None],
        })
        atom = self._make_atom(df)
        assert atom.renderImage(output_dir=Path("/tmp")) == Path()

    def test_render_summary_empty(self) -> None:
        df = pl.DataFrame({
            "wind_class": ["I"],
            "height": [None],
            "sustained_threshold": [50.0],
            "extreme_threshold": [70.0],
            "conservative_sustained": [None],
            "conservative_extreme": [None],
        })
        atom = self._make_atom(df)
        assert atom.renderSummary() == []


class TestSummaryBuilder:
    """Tests for SummaryBuilder."""

    def test_build_returns_three_atoms(self) -> None:
        method1_df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method1", "method1"],
            "max_wind_speed": [30.0, 42.0],
            "standard_density_wind_speed": [31.0, 43.0],
            "average_wind_speed": [6.0, 6.0],
            "air_density": [1.225, 1.225],
        })
        method2_sustained_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["sustained"],
            "method": ["method2"],
            "max_wind_speed": [32.0],
            "standard_density_wind_speed": [33.0],
            "observed_max": [20.0],
        })
        method2_extreme_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["extreme"],
            "method": ["method2"],
            "max_wind_speed": [44.0],
            "standard_density_wind_speed": [45.0],
            "observed_max": [28.0],
        })
        method3_sustained_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["sustained"],
            "method": ["method3"],
            "max_wind_speed": [34.0],
            "standard_density_wind_speed": [35.0],
            "observed_max": [21.0],
        })
        method3_extreme_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["extreme"],
            "method": ["method3"],
            "max_wind_speed": [46.0],
            "standard_density_wind_speed": [47.0],
            "observed_max": [29.0],
        })

        method1_result = AnalysisResult.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            data=method1_df,
            metadata=make_metadata(),
        )
        method2_sustained = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method2_sustained_df,
            metadata=make_metadata(),
        )
        method2_extreme = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method2_extreme_df,
            metadata=make_metadata(),
        )
        method3_sustained = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method3_sustained_df,
            metadata=make_metadata(),
        )
        method3_extreme = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=method3_extreme_df,
            metadata=make_metadata(),
        )

        builder = SummaryBuilder()
        atoms = builder.build(
            mast_name="TestMast",
            method1_result=method1_result,
            method2_sustained=method2_sustained,
            method2_extreme=method2_extreme,
            method3_sustained=method3_sustained,
            method3_extreme=method3_extreme,
        )

        assert len(atoms) == 3
        assert isinstance(atoms[0], SingleMastFiftyYearMaxWindComparisonSustainedAtom)
        assert isinstance(atoms[1], SingleMastFiftyYearMaxWindComparisonExtremeAtom)
        assert isinstance(atoms[2], SingleMastIECWindClassAtom)


class TestSummarySubsection:
    """Tests for SummarySubsection."""

    def test_render_ir_returns_typst_section(self) -> None:
        sustained_df = pl.DataFrame({
            "height": [100.0],
            "method1": [31.0],
            "method2": [33.0],
            "method3": [35.0],
            "conservative_max": [35.0],
            "wind_speed_type": ["sustained"],
            "interpolation_marker": [None],
        })
        extreme_df = pl.DataFrame({
            "height": [100.0],
            "method1": [43.0],
            "method2": [45.0],
            "method3": [47.0],
            "conservative_max": [47.0],
            "wind_speed_type": ["extreme"],
            "interpolation_marker": [None],
        })
        iec_df = pl.DataFrame({
            "wind_class": ["I"],
            "height": [None],
            "sustained_threshold": [50.0],
            "extreme_threshold": [70.0],
            "conservative_sustained": [None],
            "conservative_extreme": [None],
        })

        meta = SingleMastMeta(mast_name="TestMast")
        atom1 = SingleMastFiftyYearMaxWindComparisonSustainedAtom.create(
            schema=FiftyYearMaxWindComparisonSchema,
            df=sustained_df,
            meta=meta,
        )
        atom2 = SingleMastFiftyYearMaxWindComparisonExtremeAtom.create(
            schema=FiftyYearMaxWindComparisonSchema,
            df=extreme_df,
            meta=meta,
        )
        atom3 = SingleMastIECWindClassAtom.create(
            schema=IECWindClassSchema,
            df=iec_df,
            meta=meta,
        )

        collection = AtomCollection.from_dict({"TestMast": [atom1, atom2, atom3]})
        subsection = SummarySubsection(atoms=collection)
        ir = subsection.render_ir(images_dir=Path("/tmp/images"))

        assert isinstance(ir, TypstSection)
        assert ir.heading.text == "五十年一遇风速总结"
        assert len(ir.body) > 0
