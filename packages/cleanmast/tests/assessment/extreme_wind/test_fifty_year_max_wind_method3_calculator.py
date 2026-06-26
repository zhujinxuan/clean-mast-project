"""Tests for fifty-year max wind Method 3 calculator."""

import math
from datetime import datetime
from pathlib import Path

import polars as pl
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_method3_atom import (
    SingleMastFiftyYearMaxWindMethod3Atom,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._builder_method3 import (
    Method3Builder,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._calculator_method3 import (
    Method3Calculator,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.method3_subsection import (
    Method3Subsection,
)
from cleanmast.subdomains.assessment.shared.ir_types import TypstSection
from cleanmast.subdomains.assessment.shared.utils.air_density import (
    STANDARD_AIR_DENSITY,
    calculate_air_density_for_height,
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
    FiftyYearMaxWindResultSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestMethod3Calculator:
    """Tests for Method3Calculator (极端风速模型法 / EWM)."""

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
            parts = col.split("_")
            height = float(parts[1].replace("m", ""))
            stat_type = parts[2]
            sensors.append(
                SensorColumn(
                    column_name=col,
                    sensor_type="WindSpeed",
                    sensor_direction="",
                    height=height,
                    stat_type=stat_type,
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

    def test_calculate_sustained_known_max(self) -> None:
        """Synthetic data with known max → assert 1.25 * known_max."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_100m_avg": [5.0, 8.0, 6.0],
                "WS_120m_avg": [7.0, 9.0, 4.0],
            },
            heights=[100.0, 120.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method3Calculator()
        result = calculator.calculate_sustained(input_data)

        assert result.schema == FiftyYearMaxWindResultSchema
        assert len(result.data) == 2

        row_100 = result.data.filter(pl.col("height") == 100.0).row(0, named=True)
        assert math.isclose(row_100["observed_max"], 8.0, rel_tol=1e-9)
        assert math.isclose(row_100["max_wind_speed"], 8.0 * 1.25, rel_tol=1e-9)
        assert row_100["wind_speed_type"] == "sustained"
        assert row_100["method"] == "method3"

        row_120 = result.data.filter(pl.col("height") == 120.0).row(0, named=True)
        assert math.isclose(row_120["observed_max"], 9.0, rel_tol=1e-9)
        assert math.isclose(row_120["max_wind_speed"], 9.0 * 1.25, rel_tol=1e-9)

    def test_calculate_extreme_fallback_when_max_sensor_missing(self) -> None:
        """Fallback when max sensor missing → extreme = sustained × 1.4."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_100m_avg": [5.0, 8.0, 6.0],
            },
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method3Calculator()
        sustained = calculator.calculate_sustained(input_data)
        extreme = calculator.calculate_extreme(input_data, sustained_result=sustained)

        assert len(extreme.data) == 1
        row = extreme.data.row(0, named=True)
        sustained_row = sustained.data.row(0, named=True)

        expected_v50 = sustained_row["max_wind_speed"] * 1.4
        assert math.isclose(row["max_wind_speed"], expected_v50, rel_tol=1e-9)
        assert math.isclose(row["observed_max"], sustained_row["observed_max"], rel_tol=1e-9)
        assert row["wind_speed_type"] == "extreme"
        assert row["method"] == "method3"

    def test_calculate_extreme_with_max_sensor(self) -> None:
        """Extreme calculation uses max sensor when available."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_100m_avg": [5.0, 8.0, 6.0],
                "WS_100m_max": [10.0, 15.0, 12.0],
            },
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method3Calculator()
        sustained = calculator.calculate_sustained(input_data)
        extreme = calculator.calculate_extreme(input_data, sustained_result=sustained)

        assert len(extreme.data) == 1
        row = extreme.data.row(0, named=True)

        assert math.isclose(row["observed_max"], 15.0, rel_tol=1e-9)
        assert math.isclose(row["max_wind_speed"], 15.0 * 1.25, rel_tol=1e-9)
        assert row["wind_speed_type"] == "extreme"

    def test_standard_density_conversion_applied(self) -> None:
        """Standard density conversion is applied correctly."""
        reference_density = 1.1

        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_100m_avg": [8.0, 8.0],
            },
            heights=[100.0],
            air_density=reference_density,
        )

        calculator = Method3Calculator()
        result = calculator.calculate_sustained(input_data)

        row = result.data.row(0, named=True)
        v50 = row["max_wind_speed"]
        v50_std = row["standard_density_wind_speed"]

        # Air density is extrapolated to target height using barometric formula
        air_density_at_height = calculate_air_density_for_height(
            height=100.0,
            reference_density=reference_density,
            reference_height=10.0,  # default when no temp/pressure sensor
        )
        expected_std = v50 * math.sqrt(air_density_at_height / STANDARD_AIR_DENSITY)
        assert math.isclose(v50_std, expected_std, rel_tol=1e-9)
        assert v50_std < v50

    def test_negative_and_zero_values_filtered(self) -> None:
        """Values <= 0 should be excluded from the max."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_100m_avg": [-1.0, 0.0, 5.0, 7.0],
            },
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method3Calculator()
        result = calculator.calculate_sustained(input_data)

        row = result.data.row(0, named=True)
        assert math.isclose(row["observed_max"], 7.0, rel_tol=1e-9)
        assert math.isclose(row["max_wind_speed"], 7.0 * 1.25, rel_tol=1e-9)

    def test_schema_columns(self) -> None:
        """All expected columns are present and method is method3."""
        input_data = self._create_test_input(
            wind_speed_values_by_col={
                "WS_100m_avg": [5.0, 5.0],
                "WS_100m_max": [10.0, 10.0],
            },
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method3Calculator()
        sustained = calculator.calculate_sustained(input_data)
        extreme = calculator.calculate_extreme(input_data, sustained_result=sustained)

        expected_columns = {
            "height",
            "interpolation_marker",
            "wind_speed_type",
            "method",
            "max_wind_speed",
            "standard_density_wind_speed",
            "observed_max",
        }
        assert set(sustained.data.columns) == expected_columns
        assert set(extreme.data.columns) == expected_columns
        assert all(m == "method3" for m in sustained.data["method"].to_list())
        assert all(m == "method3" for m in extreme.data["method"].to_list())


class TestMethod3Atom:
    """Tests for SingleMastFiftyYearMaxWindMethod3Atom."""

    def _make_atom(self, df: pl.DataFrame) -> SingleMastFiftyYearMaxWindMethod3Atom:
        meta = SingleMastMeta(mast_name="TestMast")
        return SingleMastFiftyYearMaxWindMethod3Atom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=df,
            meta=meta,
        )

    def test_render_table_long_format(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0, 120.0, 120.0],
            "interpolation_marker": [None, None, None, None],
            "wind_speed_type": ["sustained", "extreme", "sustained", "extreme"],
            "method": ["method3", "method3", "method3", "method3"],
            "max_wind_speed": [10.0, 14.0, 12.5, 17.5],
            "standard_density_wind_speed": [10.2, 14.3, 12.8, 17.9],
            "observed_max": [8.0, 11.2, 10.0, 14.0],
        })
        atom = self._make_atom(df)
        table = atom.renderTable()

        assert table is not None
        assert table.headers == ["高度(m)", "风速类型", "观测最大值(m/s)", "50年重现期风速(m/s)", "标准密度风速(m/s)"]
        assert len(table.data) == 4

        row_100_sustained = next(r for r in table.data if r[0] == "100m" and r[1] == "持续风速")
        assert row_100_sustained[2] == "8.00"
        assert row_100_sustained[3] == "10.00"
        assert row_100_sustained[4] == "10.20"

        row_100_extreme = next(r for r in table.data if r[0] == "100m" and r[1] == "极端风速")
        assert row_100_extreme[2] == "11.20"
        assert row_100_extreme[3] == "14.00"
        assert row_100_extreme[4] == "14.30"

    def test_render_image_returns_empty_path(self) -> None:
        df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["sustained"],
            "method": ["method3"],
            "max_wind_speed": [10.0],
            "standard_density_wind_speed": [10.2],
            "observed_max": [8.0],
        })
        atom = self._make_atom(df)
        path = atom.renderImage(output_dir=Path("/tmp"))
        assert path == Path()

    def test_render_summary_returns_paragraph(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method3", "method3"],
            "max_wind_speed": [10.0, 14.0],
            "standard_density_wind_speed": [10.2, 14.3],
            "observed_max": [8.0, 11.2],
        })
        atom = self._make_atom(df)
        paragraphs = atom.renderSummary()

        assert len(paragraphs) == 1
        assert "TestMast测风塔" in paragraphs[0].text
        assert "极端风速模型法" in paragraphs[0].text
        assert "100m" in paragraphs[0].text


class TestMethod3Builder:
    """Tests for Method3Builder."""

    def test_build_returns_single_atom(self) -> None:
        sustained_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["sustained"],
            "method": ["method3"],
            "max_wind_speed": [10.0],
            "standard_density_wind_speed": [10.2],
            "observed_max": [8.0],
        })
        extreme_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["extreme"],
            "method": ["method3"],
            "max_wind_speed": [14.0],
            "standard_density_wind_speed": [14.3],
            "observed_max": [11.2],
        })

        sustained_result = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=sustained_df,
            metadata=AnalysisMetadata(mast_name="TestMast", time_range="", created_at=datetime.now()),
        )
        extreme_result = AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=extreme_df,
            metadata=AnalysisMetadata(mast_name="TestMast", time_range="", created_at=datetime.now()),
        )

        builder = Method3Builder()
        atoms = builder.build("TestMast", sustained_result, extreme_result)

        assert len(atoms) == 1
        assert isinstance(atoms[0], SingleMastFiftyYearMaxWindMethod3Atom)
        assert len(atoms[0].df) == 2


class TestMethod3Subsection:
    """Tests for Method3Subsection."""

    def test_render_ir_returns_typst_section(self) -> None:
        df = pl.DataFrame({
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "wind_speed_type": ["sustained", "extreme"],
            "method": ["method3", "method3"],
            "max_wind_speed": [10.0, 14.0],
            "standard_density_wind_speed": [10.2, 14.3],
            "observed_max": [8.0, 11.2],
        })
        meta = SingleMastMeta(mast_name="TestMast")
        atom = SingleMastFiftyYearMaxWindMethod3Atom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=df,
            meta=meta,
        )
        collection = AtomCollection.from_dict({"TestMast": [atom]})
        subsection = Method3Subsection(atoms=collection)

        ir = subsection.render_ir(images_dir=Path("/tmp/images"))

        assert isinstance(ir, TypstSection)
        assert ir.heading.text == "极端风速模型（EWM）法"
        assert len(ir.body) > 0
