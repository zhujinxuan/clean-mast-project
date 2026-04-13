"""Tests for ReportGenerationService fifty-year max wind section generation."""

import math

import polars as pl
import pytest
from cleanmast.subdomains.assessment.application.services.report_generation_service import (
    ReportGenerationService,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.fifty_year_max_wind_method1 import (
    SingleMastFiftyYearMaxWindMethod1Atom,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_section import (
    FiftyYearMaxWindSection,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestReportGenerationServiceFiftyYear:
    """Tests for generate_fifty_year_max_wind_section."""

    @pytest.fixture
    def service(self) -> ReportGenerationService:
        return ReportGenerationService()

    def _create_test_data(
        self,
        mast_name: str = "M01",
        heights: list[float] | None = None,
        interpolated_heights: list[float] | None = None,
    ) -> tuple[TimeSeriesData, SingleMastMeta]:
        heights = heights or [100.0, 120.0, 140.0, 160.0, 180.0]
        interpolated_heights = interpolated_heights or [120.0]

        n_rows = 30
        timestamps = [f"2024-01-{i + 1:02d}T00:00:00" for i in range(n_rows)]
        data: dict[str, pl.Series] = {
            "timestamp": pl.Series(timestamps).str.to_datetime(),
        }
        sensors: list[SensorColumn] = []

        for h in heights:
            base_col = f"WS_{h:.0f}m_avg"
            if h in interpolated_heights:
                col = f"{base_col}_fill:interpolated"
            else:
                col = base_col
            values = [5.0 + h / 100.0 + math.sin(i) for i in range(n_rows)]
            data[col] = pl.Series(values)
            sensors.append(
                SensorColumn(
                    column_name=col,
                    sensor_type="WindSpeed",
                    sensor_direction="",
                    height=h,
                    stat_type="avg",
                    unit="m/s",
                )
            )

        df = pl.DataFrame(data)
        time_series = TimeSeriesData(df=df, sensors=sensors)
        meta = SingleMastMeta(mast_name=mast_name, air_density=1.225)
        return time_series, meta

    def test_height_filtering_excludes_out_of_range_and_interpolated(
        self,
        service: ReportGenerationService,
    ) -> None:
        time_series, meta = self._create_test_data(
            heights=[100.0, 120.0, 140.0, 160.0, 180.0],
            interpolated_heights=[120.0],
        )
        input_data = service._create_analysis_input(time_series, meta)

        result = service.generate_fifty_year_max_wind_section([(input_data, meta)])

        assert isinstance(result, FiftyYearMaxWindSection)

        atom = result.method1.atoms.get("M01", SingleMastFiftyYearMaxWindMethod1Atom)
        assert atom is not None
        actual_heights = sorted(atom.df["height"].unique().to_list())
        assert actual_heights == [140.0, 160.0]

    def test_multi_mast_aggregation(self, service: ReportGenerationService) -> None:
        ts1, meta1 = self._create_test_data(
            "M01", heights=[140.0], interpolated_heights=[]
        )
        ts2, meta2 = self._create_test_data(
            "M02", heights=[160.0], interpolated_heights=[]
        )
        input1 = service._create_analysis_input(ts1, meta1)
        input2 = service._create_analysis_input(ts2, meta2)

        result = service.generate_fifty_year_max_wind_section([
            (input1, meta1),
            (input2, meta2),
        ])

        assert isinstance(result, FiftyYearMaxWindSection)
        assert "M01" in result.method1.atoms.masts
        assert "M02" in result.method1.atoms.masts
        assert "M01" in result.method2.atoms.masts
        assert "M02" in result.method2.atoms.masts
        assert "M01" in result.method3.atoms.masts
        assert "M02" in result.method3.atoms.masts
        assert "M01" in result.summary.atoms.masts
        assert "M02" in result.summary.atoms.masts

    def test_skip_mast_when_no_heights_remain(
        self,
        service: ReportGenerationService,
    ) -> None:
        ts, meta = self._create_test_data(
            "M01",
            heights=[100.0, 120.0],
            interpolated_heights=[120.0],
        )
        input_data = service._create_analysis_input(ts, meta)

        result = service.generate_fifty_year_max_wind_section([(input_data, meta)])

        assert isinstance(result, FiftyYearMaxWindSection)
        assert result.method1.atoms.masts == []
