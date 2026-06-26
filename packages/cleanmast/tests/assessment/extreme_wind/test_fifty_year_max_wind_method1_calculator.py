"""Tests for fifty-year max wind Method 1 calculator."""

import math
from datetime import datetime
from pathlib import Path

import polars as pl
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_method1_atom import (
    SingleMastFiftyYearMaxWindMethod1Atom,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._builder_method1 import (
    Method1Builder,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._calculator_method1 import (
    Method1Calculator,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.method1_subsection import (
    Method1Subsection,
)
from cleanmast.subdomains.assessment.shared.ir_types import TypstSection
from cleanmast.subdomains.assessment.shared.utils.air_density import (
    STANDARD_AIR_DENSITY,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_parameters import (
    AnalysisParameters,
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
    FiftyYearMaxWindMethod1DetailSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestMethod1Calculator:
    """Tests for Method1Calculator (五倍风速法)."""

    def _create_test_input(
        self,
        wind_speed_values_by_col: dict[str, list[float]],
        heights: list[float],
        timestamps: list[str] | None = None,
        mast_name: str = "TestMast",
        air_density: float = 1.225,
    ) -> SingleMastAnalysisInput:
        if timestamps is None:
            n_rows = len(next(iter(wind_speed_values_by_col.values())))
            timestamps = [f"2024-01-{i + 1:02d}T00:00:00" for i in range(n_rows)]

        data = {"timestamp": pl.Series(timestamps).str.to_datetime()}
        data.update({col: pl.Series(values) for col, values in wind_speed_values_by_col.items()})
        df = pl.DataFrame(data)

        sensors = []
        for col, values in wind_speed_values_by_col.items():
            height = float(col.split("_")[1].replace("m", ""))
            sensors.append(
                SensorColumn(
                    column_name=col,
                    sensor_type="WindSpeed",
                    sensor_direction="",
                    height=height,
                    stat_type="avg",
                    unit="m/s",
                )
            )

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=heights, air_density=air_density)

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name=mast_name,
        )

    def test_calculate_basic_three_heights(self) -> None:
        """Test basic calculation at 120m, 140m, 160m."""
        ws_120 = [6.0, 6.0, 6.0]
        ws_140 = [7.0, 7.0, 7.0]
        ws_160 = [8.0, 8.0, 8.0]

        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_120m_avg": ws_120,
                "WS_140m_avg": ws_140,
                "WS_160m_avg": ws_160,
            },
            heights=[120.0, 140.0, 160.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method1Calculator()
        result = calculator.calculate(input_data)

        assert result.schema == FiftyYearMaxWindMethod1DetailSchema
        assert len(result.data) == 6  # 3 heights x 2 wind_speed_types

        for height, expected_avg in [(120.0, 6.0), (140.0, 7.0), (160.0, 8.0)]:
            height_rows = result.data.filter(pl.col("height") == height)
            assert len(height_rows) == 2

            sustained_row = height_rows.filter(pl.col("wind_speed_type") == "sustained").row(0, named=True)
            extreme_row = height_rows.filter(pl.col("wind_speed_type") == "extreme").row(0, named=True)

            expected_sustained = 5.0 * expected_avg
            expected_extreme = 1.4 * expected_sustained

            assert math.isclose(sustained_row["max_wind_speed"], expected_sustained, rel_tol=1e-9)
            assert math.isclose(extreme_row["max_wind_speed"], expected_extreme, rel_tol=1e-9)
            assert math.isclose(sustained_row["average_wind_speed"], expected_avg, rel_tol=1e-9)
            assert math.isclose(extreme_row["average_wind_speed"], expected_avg, rel_tol=1e-9)

    def test_missing_data_skips_height(self) -> None:
        """Sensor exists but all values are null/NaN — height should be skipped."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_100m_avg": [float("nan"), float("nan")],
                "WS_120m_avg": [5.0, 6.0],
            },
            heights=[100.0, 120.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method1Calculator()
        result = calculator.calculate(input_data)

        heights = result.data["height"].unique().to_list()
        assert 100.0 not in heights
        assert 120.0 in heights

    def test_standard_density_conversion(self) -> None:
        """Standard density conversion is applied correctly."""
        avg_speed = 7.0
        actual_density = 1.1  # lower than standard 1.225

        input_data = self._create_test_input(
            wind_speed_values_by_col={"WS_100m_avg": [avg_speed, avg_speed]},
            heights=[100.0],
            air_density=actual_density,
        )

        calculator = Method1Calculator()
        result = calculator.calculate(input_data)

        sustained_row = result.data.filter(pl.col("wind_speed_type") == "sustained").row(0, named=True)
        sustained = sustained_row["max_wind_speed"]
        sustained_std = sustained_row["standard_density_wind_speed"]
        air_density_at_height = sustained_row["air_density"]

        expected_std = sustained * math.sqrt(air_density_at_height / STANDARD_AIR_DENSITY)
        assert math.isclose(sustained_std, expected_std, rel_tol=1e-9)
        assert sustained_std < sustained  # lower density means lower standard-density equivalent

    def test_method_and_schema_columns(self) -> None:
        """All expected columns are present and method is method1."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={"WS_100m_avg": [5.0, 5.0]},
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method1Calculator()
        result = calculator.calculate(input_data)

        expected_columns = {
            "height",
            "interpolation_marker",
            "wind_speed_type",
            "method",
            "max_wind_speed",
            "standard_density_wind_speed",
            "average_wind_speed",
            "air_density",
        }
        assert set(result.data.columns) == expected_columns
        assert all(m == "method1" for m in result.data["method"].to_list())

    def test_negative_and_zero_values_are_filtered(self) -> None:
        """Values <= 0 should be excluded from the mean."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={"WS_100m_avg": [-1.0, 0.0, 5.0, 7.0]},
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method1Calculator()
        result = calculator.calculate(input_data)

        row = result.data.filter(pl.col("wind_speed_type") == "sustained").row(0, named=True)
        expected_avg = 6.0
        expected_sustained = 5.0 * expected_avg
        assert math.isclose(row["average_wind_speed"], expected_avg, rel_tol=1e-9)
        assert math.isclose(row["max_wind_speed"], expected_sustained, rel_tol=1e-9)


class TestMethod1Atom:
    """Tests for SingleMastFiftyYearMaxWindMethod1Atom."""

    def _make_atom(self, df: pl.DataFrame) -> SingleMastFiftyYearMaxWindMethod1Atom:
        meta = SingleMastMeta(mast_name="TestMast")
        return SingleMastFiftyYearMaxWindMethod1Atom.create(
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
        assert table.headers == ["高度(m)", "50年最大持续风速(m/s)", "标准密度持续风速(m/s)", "50年极大极端风速(m/s)", "标准密度极端风速(m/s)"]
        assert len(table.data) == 2

        row_100 = next(r for r in table.data if r[0] == "100m")
        assert row_100[1] == "30.00"
        assert row_100[2] == "31.00"
        assert row_100[3] == "42.00"
        assert row_100[4] == "43.00"

        row_120 = next(r for r in table.data if r[0] == "120m")
        assert row_120[1] == "35.00"
        assert row_120[2] == "36.00"
        assert row_120[3] == "49.00"
        assert row_120[4] == "50.00"

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
        assert "五倍平均风速法" in paragraphs[0].text
        assert "100m" in paragraphs[0].text


class TestMethod1Builder:
    """Tests for Method1Builder."""

    def test_build_returns_single_atom(self) -> None:
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

        result = AnalysisResult.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            data=df,
            metadata=AnalysisMetadata(mast_name="TestMast", time_range="", created_at=datetime.now()),
        )

        builder = Method1Builder()
        atoms = builder.build("TestMast", result)

        assert len(atoms) == 1
        assert isinstance(atoms[0], SingleMastFiftyYearMaxWindMethod1Atom)


class TestMethod1Subsection:
    """Tests for Method1Subsection."""

    def test_render_ir_returns_typst_section(self) -> None:
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
        meta = SingleMastMeta(mast_name="TestMast")
        atom = SingleMastFiftyYearMaxWindMethod1Atom.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            df=df,
            meta=meta,
        )
        collection = AtomCollection.from_dict({"TestMast": [atom]})
        subsection = Method1Subsection(atoms=collection)

        ir = subsection.render_ir(images_dir=Path("/tmp/images"))

        assert isinstance(ir, TypstSection)
        assert ir.heading.text == "五倍风速法"
        assert len(ir.body) > 0
