"""Failing TDD scaffold for ReportGenerationService multi-mast contract.

Waves 2-3 RED phase: these tests establish the new signature contract
(list[tuple[...]]) and assert multi-mast AtomCollection aggregation.
They are expected to FAIL until the service methods are refactored.
"""

from unittest.mock import MagicMock

import pytest
from cleanmast.subdomains.assessment.application.services.report_generation_service import (
    ReportGenerationService,
)
from cleanmast.subdomains.assessment.domain.services.sections.turbulence_subsection import (
    TurbulenceSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.vertical_profile_subsection import (
    VerticalProfileSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.weibull_subsection import (
    WeibullSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.wind_frequency_subsection import (
    WindFrequencySubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.wind_rose import (
    WindRoseSection,
)
from cleanmast.subdomains.assessment.domain.services.sections.wind_temporal_subsection import (
    WindTemporalSubsection,
)
from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta


class TestReportGenerationServiceMultiMastContract:
    """RED-phase tests for multi-mast service method signatures."""

    @pytest.fixture
    def service(self) -> ReportGenerationService:
        return ReportGenerationService()



    def test_generate_wind_rose_section_accepts_multi_mast(
        self,
        service: ReportGenerationService,
    ) -> None:
        """Contract: accept list[tuple[TimeSeriesData, SingleMastMeta]]."""
        from unittest.mock import MagicMock

        import polars as pl

        ws_sensor = MagicMock()
        ws_sensor.sensor_type = "WindSpeed"
        ws_sensor.stat_type = "avg"
        ws_sensor.height = 100.0
        ws_sensor.column_name = "WS_100m_avg"
        ws_sensor.detect_interpolation_marker.return_value = None

        wd_sensor = MagicMock()
        wd_sensor.sensor_type = "WindDirection"
        wd_sensor.stat_type = "avg"
        wd_sensor.height = 100.0
        wd_sensor.column_name = "WD_100m_avg"
        wd_sensor.detect_interpolation_marker.return_value = None

        ts = MagicMock()
        ts.sensors = [ws_sensor, wd_sensor]
        ts.df = pl.DataFrame({
            "timestamp": pl.Series(["2024-01-01T00:00:00"]).str.to_datetime(),
            "WS_100m_avg": [5.0],
            "WD_100m_avg": [0.0],
        })
        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        result = service.generate_wind_rose_section([
            (ts, meta1),
            (ts, meta2),
        ])

        assert isinstance(result, WindRoseSection)
        assert "M01" in result.atoms.masts
        assert "M02" in result.atoms.masts

    # ==========================================================================
    # SingleMastAnalysisInput-based methods (5 methods)
    # ==========================================================================

    def test_generate_weibull_section_accepts_multi_mast(
        self,
        service: ReportGenerationService,
    ) -> None:
        """Contract: accept list[tuple[SingleMastAnalysisInput, SingleMastMeta]]."""
        inp = MagicMock()
        inp.time_series.sensors = []
        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        result = service.generate_weibull_section([
            (inp, meta1),
            (inp, meta2),
        ])

        assert isinstance(result, WeibullSubsection)
        assert "M01" in result.atoms.masts
        assert "M02" in result.atoms.masts

    def test_generate_vertical_profile_section_accepts_multi_mast(
        self,
        service: ReportGenerationService,
    ) -> None:
        """Contract: accept list[tuple[SingleMastAnalysisInput, SingleMastMeta]]."""
        inp = MagicMock()
        inp.time_series.sensors = []
        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        result = service.generate_vertical_profile_section([
            (inp, meta1),
            (inp, meta2),
        ])

        assert isinstance(result, VerticalProfileSubsection)
        assert "M01" in result.atoms.masts
        assert "M02" in result.atoms.masts

    def test_generate_wind_frequency_section_accepts_multi_mast(
        self,
        service: ReportGenerationService,
    ) -> None:
        """Contract: accept list[tuple[SingleMastAnalysisInput, SingleMastMeta]]."""
        inp = MagicMock()
        inp.time_series.sensors = []
        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        result = service.generate_wind_frequency_section([
            (inp, meta1),
            (inp, meta2),
        ])

        assert isinstance(result, WindFrequencySubsection)
        assert "M01" in result.atoms.masts
        assert "M02" in result.atoms.masts

    def test_generate_turbulence_section_accepts_multi_mast(
        self,
        service: ReportGenerationService,
    ) -> None:
        """Contract: accept list[tuple[SingleMastAnalysisInput, SingleMastMeta]]."""
        inp = MagicMock()
        inp.time_series.sensors = []
        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        result = service.generate_turbulence_section([
            (inp, meta1),
            (inp, meta2),
        ])

        assert isinstance(result, TurbulenceSubsection)
        assert "M01" in result.atoms.masts
        assert "M02" in result.atoms.masts

    def test_generate_temporal_section_accepts_multi_mast(
        self,
        service: ReportGenerationService,
    ) -> None:
        """Contract: accept list[tuple[SingleMastAnalysisInput, SingleMastMeta]]."""
        inp = MagicMock()
        inp.time_series.sensors = []
        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        result = service.generate_temporal_section([
            (inp, meta1),
            (inp, meta2),
        ])

        assert isinstance(result, WindTemporalSubsection)
        assert "M01" in result.atoms.masts
        assert "M02" in result.atoms.masts
