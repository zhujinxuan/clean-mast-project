"""Tests for fifty-year max wind Method 2 calculator."""

import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from cleanmast.subdomains.assessment.domain.entities.single_mast.fifty_year_max_wind_method2 import (
    SingleMastFiftyYearMaxWindMethod2ParamsAtom,
    SingleMastFiftyYearMaxWindMethod2QQExtremeAtom,
    SingleMastFiftyYearMaxWindMethod2QQSustainedAtom,
    SingleMastFiftyYearMaxWindMethod2ResultAtom,
)
from cleanmast.subdomains.assessment.domain.services.builders.fifty_year_max_wind_method2_builder import (
    Method2Builder,
)
from cleanmast.subdomains.assessment.domain.services.calculators.fifty_year_max_wind_method2_calculator import (
    Method2Calculator,
    calculate_gumbel_return_period,
    extract_five_day_maxima,
    fit_gumbel_distribution,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_method2_subsection import (
    Method2Subsection,
)
from cleanmast.subdomains.assessment.domain.types import TypstSection
from cleanmast.subdomains.assessment.domain.value_objects.air_density import (
    STANDARD_AIR_DENSITY,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    FiftyYearMaxWindResultSchema,
    GumbelParameterSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from scipy.stats import gumbel_r


class TestExtractFiveDayMaxima:
    """Tests for extract_five_day_maxima function."""

    def test_known_timestamps_correct_maxima_count(self) -> None:
        timestamps = pl.Series([datetime(2024, 1, d) for d in range(1, 16)])
        wind_speeds = pl.Series([float(d) for d in range(1, 16)])
        result = extract_five_day_maxima(wind_speeds, timestamps)
        assert len(result) == 3
        assert result.to_list() == [5.0, 10.0, 15.0]


class TestFitGumbelDistribution:
    """Tests for fit_gumbel_distribution function."""

    def test_synthetic_gumbel_data_within_tolerance(self) -> None:
        mu_true = 20.0
        beta_true = 3.0
        rng = np.random.default_rng(42)
        data = gumbel_r.rvs(loc=mu_true, scale=beta_true, size=500, random_state=rng)
        fit = fit_gumbel_distribution(data.tolist())
        assert fit is not None
        mu_fit, beta_fit = fit
        assert math.isclose(mu_fit, mu_true, rel_tol=0.06)
        assert math.isclose(beta_fit, beta_true, rel_tol=0.06)

    def test_insufficient_data_returns_none(self) -> None:
        assert fit_gumbel_distribution([1.0, 2.0, 3.0]) is None

    def test_fit_gumbel_near_zero_variance(self) -> None:
        data = [10.0] * 20  # identical values
        result = fit_gumbel_distribution(data)
        assert result is not None


class TestCalculateGumbelReturnPeriod:
    """Tests for calculate_gumbel_return_period function."""

    def test_known_values(self) -> None:
        mu = 20.0
        beta = 3.0
        result = calculate_gumbel_return_period(mu, beta)
        t = 50.0 * 365.0 / 5.0
        p = 1.0 - 1.0 / t
        expected = mu - beta * math.log(-math.log(p))
        assert math.isclose(result, expected, rel_tol=1e-9)


class TestMethod2Calculator:
    """Tests for Method2Calculator."""

    def _create_test_input(
        self,
        wind_speed_values_by_col: dict[str, list[float]],
        heights: list[float],
        timestamps: list[datetime] | None = None,
        mast_name: str = "TestMast",
        air_density: float | None = None,
    ) -> SingleMastAnalysisInput:
        if timestamps is None:
            n_rows = len(next(iter(wind_speed_values_by_col.values())))
            timestamps = [
                datetime(2024, 1, 1) + timedelta(days=i)
                for i in range(n_rows)
            ]

        data = {"timestamp": pl.Series(timestamps)}
        data.update({col: pl.Series(values) for col, values in wind_speed_values_by_col.items()})
        df = pl.DataFrame(data)

        sensors = []
        for col, values in wind_speed_values_by_col.items():
            height = float(col.split("_")[1].replace("m", ""))
            stat_type = "max" if "max" in col else "avg"
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

    def test_calculate_sustained_with_synthetic_data(self) -> None:
        rng = np.random.default_rng(42)
        mu_true = 15.0
        beta_true = 2.0
        data = gumbel_r.rvs(loc=mu_true, scale=beta_true, size=1000, random_state=rng)

        input_data = self._create_test_input(
            wind_speed_values_by_col={"WS_100m_avg": data.tolist()},
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method2Calculator()
        wind_result, param_result = calculator.calculate_sustained(input_data)

        assert wind_result.schema == FiftyYearMaxWindResultSchema
        assert param_result.schema == GumbelParameterSchema
        assert len(wind_result.data) == 1
        assert len(param_result.data) == 1

        wind_row = wind_result.data.row(0, named=True)
        assert wind_row["wind_speed_type"] == "sustained"
        assert wind_row["method"] == "method2"
        assert wind_row["height"] == 100.0

        param_row = param_result.data.row(0, named=True)
        assert param_row["wind_speed_type"] == "sustained"
        assert param_row["sample_count"] == 200
        assert param_row["sample_data"] is not None
        assert len(param_row["sample_data"]) == 200

    def test_fallback_when_max_sensor_missing(self) -> None:
        rng = np.random.default_rng(42)
        data = gumbel_r.rvs(loc=15.0, scale=2.0, size=1000, random_state=rng)

        input_data = self._create_test_input(
            wind_speed_values_by_col={"WS_100m_avg": data.tolist()},
            heights=[100.0],
            air_density=STANDARD_AIR_DENSITY,
        )

        calculator = Method2Calculator()
        sustained_wind, _ = calculator.calculate_sustained(input_data)
        extreme_wind, extreme_params = calculator.calculate_extreme(input_data, sustained_wind)

        assert len(extreme_wind.data) == 1
        extreme_row = extreme_wind.data.row(0, named=True)
        assert extreme_row["wind_speed_type"] == "extreme"

        sustained_row = sustained_wind.data.row(0, named=True)
        expected_extreme = sustained_row["max_wind_speed"] * 1.4
        assert math.isclose(extreme_row["max_wind_speed"], expected_extreme, rel_tol=1e-9)

        assert len(extreme_params.data) == 0


class TestMethod2Atoms:
    """Tests for Method 2 report atoms."""

    def _make_result_atom(self, df: pl.DataFrame) -> SingleMastFiftyYearMaxWindMethod2ResultAtom:
        meta = SingleMastMeta(mast_name="TestMast")
        return SingleMastFiftyYearMaxWindMethod2ResultAtom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=df,
            meta=meta,
        )

    def _make_params_atom(self, df: pl.DataFrame) -> SingleMastFiftyYearMaxWindMethod2ParamsAtom:
        meta = SingleMastMeta(mast_name="TestMast")
        return SingleMastFiftyYearMaxWindMethod2ParamsAtom.create(
            schema=GumbelParameterSchema,
            df=df,
            meta=meta,
        )

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
        atom = self._make_result_atom(df)
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
        atom = self._make_params_atom(df)
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
        meta = SingleMastMeta(mast_name="TestMast")
        atom = SingleMastFiftyYearMaxWindMethod2QQSustainedAtom.create(
            schema=GumbelParameterSchema,
            df=df,
            meta=meta,
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
        meta = SingleMastMeta(mast_name="TestMast")
        atom = SingleMastFiftyYearMaxWindMethod2QQExtremeAtom.create(
            schema=GumbelParameterSchema,
            df=df,
            meta=meta,
        )
        path = atom.renderImage(tmp_path)
        assert path.exists()
        assert path.suffix == ".png"


class TestMethod2Builder:
    """Tests for Method2Builder."""

    def test_build_returns_four_atoms(self) -> None:
        wind_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["sustained"],
            "method": ["method2"],
            "max_wind_speed": [25.0],
            "standard_density_wind_speed": [26.0],
            "observed_max": [20.0],
        })
        param_df = pl.DataFrame({
            "height": [100.0],
            "wind_speed_type": ["sustained"],
            "mu": [20.0],
            "beta": [3.0],
            "sample_count": [50],
            "sample_mean": [21.0],
            "sample_std": [4.0],
            "sample_data": [[20.0]],
        })
        meta = AnalysisMetadata(mast_name="TestMast", time_range="", created_at=datetime.now())
        sustained_wind = AnalysisResult.create(schema=FiftyYearMaxWindResultSchema, data=wind_df, metadata=meta)
        sustained_params = AnalysisResult.create(schema=GumbelParameterSchema, data=param_df, metadata=meta)
        empty_wind_df = pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "method": pl.Series([], dtype=pl.String),
            "max_wind_speed": pl.Series([], dtype=pl.Float64),
            "standard_density_wind_speed": pl.Series([], dtype=pl.Float64),
            "observed_max": pl.Series([], dtype=pl.Float64),
        })
        empty_param_df = pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "mu": pl.Series([], dtype=pl.Float64),
            "beta": pl.Series([], dtype=pl.Float64),
            "sample_count": pl.Series([], dtype=pl.Int64),
            "sample_mean": pl.Series([], dtype=pl.Float64),
            "sample_std": pl.Series([], dtype=pl.Float64),
            "sample_data": pl.Series([], dtype=pl.List(pl.Float64)),
        })
        extreme_wind = AnalysisResult.create(schema=FiftyYearMaxWindResultSchema, data=empty_wind_df, metadata=meta)
        extreme_params = AnalysisResult.create(schema=GumbelParameterSchema, data=empty_param_df, metadata=meta)

        builder = Method2Builder()
        atoms = builder.build("TestMast", sustained_wind, sustained_params, extreme_wind, extreme_params, Path("/tmp"))

        assert len(atoms) == 4
        assert isinstance(atoms[0], SingleMastFiftyYearMaxWindMethod2ResultAtom)
        assert isinstance(atoms[1], SingleMastFiftyYearMaxWindMethod2ParamsAtom)
        assert isinstance(atoms[2], SingleMastFiftyYearMaxWindMethod2QQSustainedAtom)
        assert isinstance(atoms[3], SingleMastFiftyYearMaxWindMethod2QQExtremeAtom)


class TestMethod2Subsection:
    """Tests for Method2Subsection."""

    def test_render_ir_returns_typst_section(self) -> None:
        wind_df = pl.DataFrame({
            "height": [100.0],
            "interpolation_marker": [None],
            "wind_speed_type": ["sustained"],
            "method": ["method2"],
            "max_wind_speed": [25.0],
            "standard_density_wind_speed": [26.0],
            "observed_max": [20.0],
        })
        meta = SingleMastMeta(mast_name="TestMast")
        atom = SingleMastFiftyYearMaxWindMethod2ResultAtom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=wind_df,
            meta=meta,
        )
        collection = AtomCollection.from_dict({"TestMast": [atom]})
        subsection = Method2Subsection(atoms=collection)

        ir = subsection.render_ir(images_dir=Path("/tmp/images"))
        assert isinstance(ir, TypstSection)
        assert ir.heading.text == "五日最大法"
        assert len(ir.body) > 0
