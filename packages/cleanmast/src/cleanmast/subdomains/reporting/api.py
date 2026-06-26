"""Public API for the reporting domain.

api.py exposes ReportGenerationService — the sole public interface for
orchestrating report generation. Thin — no domain logic. All real work
happens in subdomains.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import tomli

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure import load_timeseries
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.reporting.model.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.model.section_input import (
    MesoSectionInput,
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
    ) -> SingleMastAnalysisInput:
        return _build_analysis_input(time_series, mast_name, air_density)

    def generate_air_density_section(
        self, items: list[SingleMastAnalysisInput],
    ) -> Section:
        return AirDensitySection.from_inputs(items)

    def generate_representative_year_calibration_section(
        self,
        items: list[SingleMastAnalysisInput],
    ) -> RepresentativeYearSection:
        meso_map: dict[str, TimeSeriesData] = {}
        meso_inputs: list[MesoSectionInput] = []

        if self.project_dir is not None:
            config_path = self.project_dir / "representative-year.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomli.load(f)

                for meso_cfg in config.get("mesos", []):
                    meso_name = meso_cfg["name"]
                    meso_input = meso_cfg.get("input", {})
                    if "data" in meso_input:
                        source = TimeSeriesSource(data=meso_input["data"])
                        meso_ts = load_timeseries(source, str(self.project_dir))
                        meso_map[meso_name] = meso_ts

                for mast_cfg in config.get("masts", []):
                    mast_name = mast_cfg["name"]
                    meso_model = mast_cfg.get("meso_model", {})
                    meso_name = meso_model.get("meso_name", "")
                    time_range = mast_cfg.get("time_range", {})

                    if meso_name in meso_map and time_range:
                        rep_min = time_range["min"]
                        rep_max = time_range["max"]
                        if isinstance(rep_min, str):
                            rep_min = datetime.fromisoformat(rep_min)
                        if isinstance(rep_max, str):
                            rep_max = datetime.fromisoformat(rep_max)
                        meso_inputs.append(
                            MesoSectionInput(
                                meso_time_series=meso_map[meso_name],
                                mast_name=mast_name,
                                meso_name=meso_name,
                                rep_year_min=rep_min,
                                rep_year_max=rep_max,
                            )
                        )

        return RepresentativeYearSection.from_inputs(meso_inputs)

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
) -> SingleMastAnalysisInput:
    """Build SingleMastAnalysisInput from time_series sensors."""
    ws_heights = [
        s.height
        for s in time_series.sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    ]
    params = AnalysisParameters(
        heights=ws_heights,
        air_density=air_density,
    )
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=params,
        mast_name=mast_name,
    )
