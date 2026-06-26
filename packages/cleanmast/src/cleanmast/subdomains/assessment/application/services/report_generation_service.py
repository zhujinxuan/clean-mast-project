"""Report generation service for assessment subdomain.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Application Service ✓ | Service Layer ✓
Description: Application service that coordinates calculators and builders for report generation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from cleanmast.subdomains.assessment.subdomains.air_density.services.air_density_section import (
    AirDensityService,
    AirDensitySubsection,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services.fifty_year_max_wind_section import (
    ExtremeWindService,
    FiftyYearMaxWindSection,
)
from cleanmast.subdomains.assessment.subdomains.representative_year.services.representative_year_section import (
    RepresentativeYearCalibrationSubsection,
    RepresentativeYearService,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.services.turbulence_section import (
    TurbulenceService,
    TurbulenceSubsection,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.services.vertical_profile_section import (
    VerticalProfileService,
    VerticalProfileSubsection,
)
from cleanmast.subdomains.assessment.subdomains.weibull.services.weibull_section import (
    WeibullService,
    WeibullSubsection,
)
from cleanmast.subdomains.assessment.subdomains.wind_frequency.services.wind_frequency_section import (
    WindFrequencyService,
    WindFrequencySubsection,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.services.wind_rose_section import (
    WindRoseService,
    WindRoseSection,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.services.wind_temporal_section import (
    WindTemporalService,
    WindTemporalSubsection,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
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

    def __init__(self, project_dir: Path | None = None) -> None:
        """Initialize the service."""
        self.project_dir = project_dir

    def _create_analysis_input(
        self,
        time_series: TimeSeriesData,
        meta: SingleMastMeta,
        air_density: float,
    ) -> SingleMastAnalysisInput:
        """Create SingleMastAnalysisInput from components."""
        parameters = AnalysisParameters(
            heights=[s.height for s in time_series.sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"],
            air_density=air_density,
        )
        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name=meta.mast_name,
        )

    def generate_wind_rose_section(
        self,
        items: list[tuple[TimeSeriesData, SingleMastMeta]],
    ) -> WindRoseSection:
        """Generate wind rose section from time series data.

        Args:
            items: List of (time_series, meta) tuples for multi-mast aggregation.

        Returns:
            WindRoseSection containing wind frequency and power density roses
        """
        return WindRoseService.generate(items)

    def generate_fifty_year_max_wind_section(
        self,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> FiftyYearMaxWindSection:
        """Generate fifty-year max wind section from time series data.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            FiftyYearMaxWindSection containing Method 1/2/3 and summary subsections
        """
        return ExtremeWindService.generate(items)

    def generate_weibull_section(
        self,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> WeibullSubsection:
        """Generate Weibull distribution section.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            WeibullSubsection containing Weibull distribution analysis
        """
        return WeibullService.generate(items)

    def generate_vertical_profile_section(
        self,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> VerticalProfileSubsection:
        """Generate vertical wind profile section.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            VerticalProfileSubsection containing vertical profile analysis
        """
        return VerticalProfileService.generate(items)

    def generate_wind_frequency_section(
        self,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> WindFrequencySubsection:
        """Generate wind frequency distribution section.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            WindFrequencySubsection containing wind frequency analysis
        """
        return WindFrequencyService.generate(items)

    def generate_turbulence_section(
        self,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> TurbulenceSubsection:
        """Generate turbulence intensity section.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            TurbulenceSubsection containing turbulence intensity analysis
        """
        return TurbulenceService.generate(items)

    def generate_temporal_section(
        self,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> WindTemporalSubsection:
        """Generate wind temporal analysis section.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            WindTemporalSubsection containing temporal pattern analysis
        """
        return WindTemporalService.generate(items)

    def generate_air_density_section(
        self,
        analysis_inputs: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> AirDensitySubsection:
        """Generate air density section from analysis inputs.

        Args:
            analysis_inputs: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            AirDensitySubsection containing air density analysis
        """
        return AirDensityService.generate(analysis_inputs)

    def generate_representative_year_calibration_section(
        self,
        analysis_inputs: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> RepresentativeYearCalibrationSubsection:
        """Generate representative year calibration section from analysis inputs.

        Args:
            analysis_inputs: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            RepresentativeYearCalibrationSubsection containing representative year calibration analysis.
        """
        if self.project_dir is None:
            raise ValueError("project_dir is required for representative year calibration section")
        return RepresentativeYearService.generate(analysis_inputs, self.project_dir)


__all__ = ["ReportGenerationService"]
