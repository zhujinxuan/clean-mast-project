"""Report generation service for assessment subdomain.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Application Service ✓ | Service Layer ✓
Description: Application service that coordinates calculators and builders for report generation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cleanmast.subdomains.assessment.domain.services.builders import (
    TurbulenceSectionBuilder,
    VerticalProfileSectionBuilder,
    WeibullSectionBuilder,
    WindFrequencySectionBuilder,
    WindRoseSectionBuilder,
    WindTemporalSectionBuilder,
)
from cleanmast.subdomains.assessment.domain.services.calculators import (
    MonthlyPowerCalculator,
    MonthlyStatsCalculator,
    WeibullFitter,
    WindRoseCalculator,
)
from cleanmast.subdomains.assessment.domain.services.calculators.turbulence_calculator import (
    TurbulenceCalculator,
)
from cleanmast.subdomains.assessment.domain.services.calculators.vertical_profile_analyzer import (
    VerticalProfileAnalyzer,
)
from cleanmast.subdomains.assessment.domain.services.calculators.wind_frequency_calculator import (
    WindFrequencyCalculator,
)
from cleanmast.subdomains.assessment.domain.services.calculators.wind_temporal_analyzer import (
    WindTemporalAnalyzer,
)
from cleanmast.subdomains.assessment.domain.services.sections.representative_wind_power import (
    RepresentativeWindPowerSection,
)
from cleanmast.subdomains.assessment.domain.services.sections.representative_wind_speed import (
    RepresentativeWindSpeedSection,
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
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
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
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.monthly_wind import (
    SingleMastMonthlyWindAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.monthly_wind_power import (
    SingleMastMonthlyWindPowerAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta as ReportingMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    MonthlyWindPowerSchema as ReportingMonthlyWindPowerSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    MonthlyWindSchema as ReportingMonthlyWindSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WeibullSchema,
    WindRoseSchema,
)

if TYPE_CHECKING:
    from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData


class ReportGenerationService:
    """Service for coordinating report section generation.

    This application service provides a thin orchestration layer between:
    - Domain calculators (process raw data -> AnalysisResult)
    - Domain builders (AnalysisResult -> ReportAtoms)
    - Section assemblers (atoms -> renderable sections)
    """

    def __init__(self) -> None:
        """Initialize the service with all required calculators and builders."""
        self._wind_rose_calculator = WindRoseCalculator()
        self._monthly_stats_calculator = MonthlyStatsCalculator()
        self._monthly_power_calculator = MonthlyPowerCalculator()
        self._weibull_fitter = WeibullFitter()
        self._turbulence_calculator = TurbulenceCalculator()
        self._wind_temporal_analyzer = WindTemporalAnalyzer()
        self._vertical_profile_analyzer = VerticalProfileAnalyzer()
        self._wind_frequency_calculator = WindFrequencyCalculator()

        self._wind_rose_builder = WindRoseSectionBuilder()
        self._weibull_builder = WeibullSectionBuilder()
        self._turbulence_builder = TurbulenceSectionBuilder()
        self._wind_temporal_builder = WindTemporalSectionBuilder()
        self._vertical_profile_builder = VerticalProfileSectionBuilder()
        self._wind_frequency_builder = WindFrequencySectionBuilder()

    def _create_analysis_input(
        self,
        time_series: TimeSeriesData,
        meta: SingleMastMeta,
        air_density: float | None = None,
    ) -> SingleMastAnalysisInput:
        """Create SingleMastAnalysisInput from components."""
        parameters = AnalysisParameters(
            heights=[s.height for s in time_series.sensors if s.sensor_type == "WindSpeed"],
            air_density=air_density if air_density is not None else meta.air_density,
        )
        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name=meta.mast_name,
        )

    def _to_reporting_meta(self, meta: SingleMastMeta) -> ReportingMeta:
        """Convert assessment meta to reporting meta."""
        return ReportingMeta(
            mast_name=meta.mast_name,
            air_density=meta.air_density,
            caption=getattr(meta, "caption", ""),
            width=getattr(meta, "width", "80%"),
        )

    def generate_wind_rose_section(
        self,
        time_series: TimeSeriesData,
        meta: SingleMastMeta,
    ) -> WindRoseSection:
        """Generate wind rose section from time series data.

        Args:
            time_series: TimeSeriesData with df and sensors
            meta: SingleMastMeta with mast_name, air_density, and other metadata

        Returns:
            WindRoseSection containing wind frequency and power density roses
        """
        input_data = self._create_analysis_input(time_series, meta)
        result = self._wind_rose_calculator.calculate(input_data)

        builder_result = AnalysisResult.create(
            schema=WindRoseSchema,
            data=result.data,
            metadata=result.metadata,
        )

        atoms = self._wind_rose_builder.build(
            mast_name=meta.mast_name,
            results=[builder_result],
        )
        collection = AtomCollection.from_dict({meta.mast_name: atoms})
        return WindRoseSection(
            atoms=collection,
            title=f"{meta.mast_name} 风向风能分布",
            level=1,
        )

    def generate_monthly_wind_section(
        self,
        time_series: TimeSeriesData,
        meta: SingleMastMeta,
    ) -> RepresentativeWindSpeedSection:
        """Generate monthly wind statistics section.

        Args:
            time_series: TimeSeriesData with df and sensors
            meta: SingleMastMeta with mast_name and other metadata

        Returns:
            RepresentativeWindSpeedSection containing monthly wind statistics
        """
        input_data = self._create_analysis_input(time_series, meta)
        result = self._monthly_stats_calculator.calculate(input_data)
        reporting_meta = self._to_reporting_meta(meta)
        atom = SingleMastMonthlyWindAtom.create(
            schema=ReportingMonthlyWindSchema,
            df=result.data,
            meta=reporting_meta,
        )
        collection = AtomCollection.from_dict({meta.mast_name: [atom]})
        return RepresentativeWindSpeedSection(
            atoms=collection,
            title=f"{meta.mast_name} 代表年各月风速结果",
            level=1,
        )

    def generate_monthly_power_section(
        self,
        time_series: TimeSeriesData,
        meta: SingleMastMeta,
        air_density: float | None = None,
    ) -> RepresentativeWindPowerSection:
        """Generate monthly wind power density section.

        Args:
            time_series: TimeSeriesData with df and sensors
            meta: SingleMastMeta with mast_name and other metadata
            air_density: Optional air density override (kg/m³). Uses meta.air_density if None.

        Returns:
            RepresentativeWindPowerSection containing monthly power density statistics
        """
        density = air_density if air_density is not None else meta.air_density
        input_data = self._create_analysis_input(time_series, meta, density)
        result = self._monthly_power_calculator.calculate(input_data)
        reporting_meta = self._to_reporting_meta(meta)
        atom = SingleMastMonthlyWindPowerAtom.create(
            schema=ReportingMonthlyWindPowerSchema,
            df=result.data,
            meta=reporting_meta,
        )
        collection = AtomCollection.from_dict({meta.mast_name: [atom]})
        return RepresentativeWindPowerSection(
            atoms=collection,
            title=f"{meta.mast_name} 代表年各月风功率结果",
            level=1,
        )

    def generate_weibull_section(
        self,
        input_data: SingleMastAnalysisInput,
        meta: SingleMastMeta,
    ) -> WeibullSubsection:
        """Generate Weibull distribution section.

        Args:
            input_data: SingleMastAnalysisInput containing time series data and parameters
            meta: SingleMastMeta with mast_name and other metadata

        Returns:
            WeibullSubsection containing Weibull distribution analysis
        """
        ws_sensors = [
            s for s in input_data.time_series.sensors
            if s.sensor_type == "WindSpeed"
        ]
        results: list[AnalysisResult[WeibullSchema]] = []
        for sensor in ws_sensors:
            result = self._weibull_fitter.fit_from_input(
                input_data,
                sensor.column_name,
            )
            if result is not None:
                results.append(result)
        atoms = self._weibull_builder.build(
            mast_name=meta.mast_name,
            results=results,
        )
        collection = AtomCollection.from_dict({meta.mast_name: atoms})
        return WeibullSubsection(
            atoms=collection,
            title=f"{meta.mast_name} Weibull分布拟合",
            level=2,
        )

    def generate_vertical_profile_section(
        self,
        input_data: SingleMastAnalysisInput,
        meta: SingleMastMeta,
    ) -> VerticalProfileSubsection:
        """Generate vertical wind profile section.

        Args:
            input_data: SingleMastAnalysisInput containing time series data and parameters
            meta: SingleMastMeta with mast_name and other metadata

        Returns:
            VerticalProfileSubsection containing vertical profile analysis
        """
        profile_result = self._vertical_profile_analyzer.analyze_vertical_profile(
            input_data,
        )
        shear_result = self._vertical_profile_analyzer.calculate_wind_shear_analysis(
            input_data,
        )
        atoms = self._vertical_profile_builder.build(
            mast_name=meta.mast_name,
            profile_results=[profile_result],
            shear_results=[shear_result],
        )
        collection = AtomCollection.from_dict({meta.mast_name: atoms})
        return VerticalProfileSubsection(
            atoms=collection,
            title=f"{meta.mast_name} 垂直风廓线分析",
            level=2,
        )

    def generate_wind_frequency_section(
        self,
        input_data: SingleMastAnalysisInput,
        meta: SingleMastMeta,
    ) -> WindFrequencySubsection:
        """Generate wind frequency distribution section.

        Args:
            input_data: SingleMastAnalysisInput containing time series data and parameters
            meta: SingleMastMeta with mast_name and other metadata

        Returns:
            WindFrequencySubsection containing wind frequency analysis
        """
        result = self._wind_frequency_calculator.analyze_by_height(input_data)
        atoms = self._wind_frequency_builder.build(
            mast_name=meta.mast_name,
            results=[result],
        )
        collection = AtomCollection.from_dict({meta.mast_name: atoms})
        return WindFrequencySubsection(
            atoms=collection,
            title=f"{meta.mast_name} 风速频率分析",
            level=2,
        )

    def generate_turbulence_section(
        self,
        input_data: SingleMastAnalysisInput,
        meta: SingleMastMeta,
    ) -> TurbulenceSubsection:
        """Generate turbulence intensity section.

        Args:
            input_data: SingleMastAnalysisInput containing time series data and parameters
            meta: SingleMastMeta with mast_name and other metadata

        Returns:
            TurbulenceSubsection containing turbulence intensity analysis
        """
        ti_result = self._turbulence_calculator.analyze_by_wind_speed(input_data)
        sector_result = self._turbulence_calculator.analyze_by_sector(input_data)
        atoms = self._turbulence_builder.build(
            mast_name=meta.mast_name,
            ti_results=[ti_result],
            sector_results=[sector_result],
        )
        collection = AtomCollection.from_dict({meta.mast_name: atoms})
        return TurbulenceSubsection(
            atoms=collection,
            title=f"{meta.mast_name} 湍流强度分析",
            level=2,
        )

    def generate_temporal_section(
        self,
        input_data: SingleMastAnalysisInput,
        meta: SingleMastMeta,
    ) -> WindTemporalSubsection:
        """Generate wind temporal analysis section.

        Args:
            input_data: SingleMastAnalysisInput containing time series data and parameters
            meta: SingleMastMeta with mast_name and other metadata

        Returns:
            WindTemporalSubsection containing temporal pattern analysis
        """
        daily_result = self._wind_temporal_analyzer.analyze_daily_pattern(
            input_data,
        )
        monthly_result = self._wind_temporal_analyzer.analyze_monthly_pattern(
            input_data,
        )
        monthly_daily_result = self._wind_temporal_analyzer.analyze_monthly_daily(
            input_data,
        )
        atoms = self._wind_temporal_builder.build(
            mast_name=meta.mast_name,
            time_series_result=daily_result,
            daily_result=daily_result,
            monthly_result=monthly_result,
            monthly_daily_result=monthly_daily_result,
        )
        collection = AtomCollection.from_dict({meta.mast_name: atoms})
        return WindTemporalSubsection(
            atoms=collection,
            title=f"{meta.mast_name} 风速时序分析",
            level=2,
        )


__all__ = ["ReportGenerationService"]
