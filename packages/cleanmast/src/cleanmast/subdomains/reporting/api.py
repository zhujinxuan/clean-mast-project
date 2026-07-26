"""Public API for the reporting domain.

api.py exposes ReportGenerationService — the sole public interface for
orchestrating report generation. Thin — no domain logic. All real work
happens in subdomains.
"""

from __future__ import annotations

from pathlib import Path

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.model.analysis_parameters import AnalysisParameters
from cleanmast.subdomains.reporting.model.extreme_wind_gust_factor import (
    ExtremeWindGustFactor,
)
from cleanmast.subdomains.reporting.protocols.section import Section
from cleanmast.subdomains.reporting.subdomains.air_density import AirDensitySection
from cleanmast.subdomains.reporting.subdomains.extreme_wind.section import (
    ExtremeWindSection,
)
from cleanmast.subdomains.reporting.subdomains.representative_year import (
    RepresentativeYearSection,
)
from cleanmast.subdomains.reporting.subdomains.turbulence import TurbulenceSection
from cleanmast.subdomains.reporting.subdomains.vertical_profile import (
    VerticalProfileSection,
)
from cleanmast.subdomains.reporting.subdomains.weibull import WeibullSection
from cleanmast.subdomains.reporting.subdomains.wind_frequency import (
    WindFrequencySection,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose import WindRoseSection
from cleanmast.subdomains.reporting.subdomains.wind_temporal import (
    WindTemporalSection,
)


class ReportGenerationService:
    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = project_dir

    def _create_analysis_input(
        self,
        time_series: TimeSeriesData,
        mast_name: str,
        air_density: float,
        extreme_wind_10min_heights: list[float],
        extreme_wind_3s_heights: list[float],
        extreme_wind_gust_factors: list[ExtremeWindGustFactor],
        turbulence_heights: list[float] | None = None,
        analysis_heights: list[float] | None = None,
        temporal_heights: list[float] | None = None,
    ) -> SingleMastAnalysisInput:
        return _build_analysis_input(
            time_series, mast_name, air_density,
            turbulence_heights=turbulence_heights,
            analysis_heights=analysis_heights,
            temporal_heights=temporal_heights,
            extreme_wind_10min_heights=extreme_wind_10min_heights,
            extreme_wind_3s_heights=extreme_wind_3s_heights,
            extreme_wind_gust_factors=extreme_wind_gust_factors,
        )

    def generate_air_density_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return AirDensitySection.from_inputs(items)

    def generate_representative_year_calibration_section(
        self,
        items: list[SingleMastAnalysisInput],
    ) -> RepresentativeYearSection:
        """Dispatch — items carry calibration payloads from load_datasets()."""
        return RepresentativeYearSection.from_inputs(items)

    def generate_wind_rose_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return WindRoseSection.from_inputs(items)

    def generate_vertical_profile_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return VerticalProfileSection.from_inputs(items)

    def generate_wind_frequency_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return WindFrequencySection.from_inputs(items)

    def generate_weibull_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return WeibullSection.from_inputs(items)

    def generate_turbulence_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return TurbulenceSection.from_inputs(items)

    def generate_temporal_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return WindTemporalSection.from_inputs(items)

    def generate_fifty_year_max_wind_section(
        self,
        items: list[SingleMastAnalysisInput],
    ) -> Section:
        """Generate fifty-year max wind section from analysis inputs.

        Thin adapter: delegates all compute + assemble to
        ExtremeWindSection.from_inputs.
        """
        return ExtremeWindSection.from_inputs(items)


# ── internal helpers ──────────────────────────────────────────────────────


def _build_analysis_input(
    time_series: TimeSeriesData,
    mast_name: str,
    air_density: float,
    extreme_wind_10min_heights: list[float],
    extreme_wind_3s_heights: list[float],
    extreme_wind_gust_factors: list[ExtremeWindGustFactor],
    turbulence_heights: list[float] | None = None,
    analysis_heights: list[float] | None = None,
    temporal_heights: list[float] | None = None,
) -> SingleMastAnalysisInput:
    """Build SingleMastAnalysisInput from time_series sensors."""
    params = AnalysisParameters(
        air_density=air_density,
        turbulence_heights=turbulence_heights or [],
        analysis_heights=analysis_heights or [],
        temporal_heights=temporal_heights or [],
        extreme_wind_10min_heights=extreme_wind_10min_heights,
        extreme_wind_3s_heights=extreme_wind_3s_heights,
        extreme_wind_gust_factors=extreme_wind_gust_factors,
    )
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=params,
        mast_name=mast_name,
    )
