"""Report generation service for assessment subdomain.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Application Service ✓ | Service Layer ✓
Description: Application service that coordinates calculators and builders for report generation
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from cleanmast.subdomains.assessment.domain.entities.multi_masts.air_density import (
    MultiMastAirDensityAtom,
)
from cleanmast.subdomains.assessment.domain.entities.multi_masts.representative_year_calibration import (
    MultiMastRepYearCalibrationAtom,
)
from cleanmast.subdomains.assessment.domain.entities.no_masts.iec_standards import (
    IEC_STANDARDS_DATA,
    NoMastIECStandardsAtom,
)
from cleanmast.subdomains.assessment.domain.services.builders import (
    TurbulenceSectionBuilder,
    VerticalProfileSectionBuilder,
    WeibullSectionBuilder,
    WindFrequencySectionBuilder,
    WindRoseSectionBuilder,
    WindTemporalSectionBuilder,
)
from cleanmast.subdomains.assessment.domain.services.builders.fifty_year_max_wind_method1_builder import (
    Method1Builder as FiftyYearMethod1Builder,
)
from cleanmast.subdomains.assessment.domain.services.builders.fifty_year_max_wind_method2_builder import (
    Method2Builder as FiftyYearMethod2Builder,
)
from cleanmast.subdomains.assessment.domain.services.builders.fifty_year_max_wind_method3_builder import (
    Method3Builder as FiftyYearMethod3Builder,
)
from cleanmast.subdomains.assessment.domain.services.builders.fifty_year_max_wind_summary_builder import (
    SummaryBuilder as FiftyYearSummaryBuilder,
)
from cleanmast.subdomains.assessment.domain.services.calculators import (
    WeibullFitter,
    WindRoseCalculator,
)
from cleanmast.subdomains.assessment.domain.services.calculators.fifty_year_max_wind_method1_calculator import (
    Method1Calculator as FiftyYearMethod1Calculator,
)
from cleanmast.subdomains.assessment.domain.services.calculators.fifty_year_max_wind_method2_calculator import (
    Method2Calculator as FiftyYearMethod2Calculator,
)
from cleanmast.subdomains.assessment.domain.services.calculators.fifty_year_max_wind_method3_calculator import (
    Method3Calculator as FiftyYearMethod3Calculator,
)
from cleanmast.subdomains.assessment.domain.services.calculators.representative_year_calibration_analyzer import (
    analyze_representative_year_calibration,
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
from cleanmast.subdomains.assessment.domain.services.sections.air_density_subsection import (
    AirDensitySubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_iec_standards_subsection import (
    IECStandardsSubsection as FiftyYearIECStandardsSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_method1_subsection import (
    Method1Subsection as FiftyYearMethod1Subsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_method2_subsection import (
    Method2Subsection as FiftyYearMethod2Subsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_method3_subsection import (
    Method3Subsection as FiftyYearMethod3Subsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_section import (
    FiftyYearMaxWindSection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_summary_subsection import (
    SummarySubsection as FiftyYearSummarySubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.representative_year_calibration import (
    RepresentativeYearCalibrationSubsection,
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
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.report_meta import (
    MultiMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.schemas import (
    MultiMastAirDensitySchema,
    MultiMastRepYearCalibrationSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.no_masts.report_meta import (
    NoMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.no_masts.schemas import (
    IECStandardsSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WeibullSchema,
    WindRoseSchema,
)

if TYPE_CHECKING:
    from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
    from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData


class ReportGenerationService:
    """Service for coordinating report section generation.

    This application service provides a thin orchestration layer between:
    - Domain calculators (process raw data -> AnalysisResult)
    - Domain builders (AnalysisResult -> ReportAtoms)
    - Section assemblers (atoms -> renderable sections)
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        """Initialize the service with all required calculators and builders."""
        self.project_dir = project_dir
        self._wind_rose_calculator = WindRoseCalculator()
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

        self._fifty_year_method1_calculator = FiftyYearMethod1Calculator()
        self._fifty_year_method2_calculator = FiftyYearMethod2Calculator()
        self._fifty_year_method3_calculator = FiftyYearMethod3Calculator()
        self._fifty_year_method1_builder = FiftyYearMethod1Builder()
        self._fifty_year_method2_builder = FiftyYearMethod2Builder()
        self._fifty_year_method3_builder = FiftyYearMethod3Builder()
        self._fifty_year_summary_builder = FiftyYearSummaryBuilder()

    def _create_analysis_input(
        self,
        time_series: TimeSeriesData,
        meta: SingleMastMeta,
        air_density: float | None = None,
    ) -> SingleMastAnalysisInput:
        """Create SingleMastAnalysisInput from components."""
        parameters = AnalysisParameters(
            heights=[s.height for s in time_series.sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"],
            air_density=air_density if air_density is not None else meta.air_density,
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
        collection_dict: dict[str, list[ReportAtom]] = {}
        for time_series, meta in items:
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
            collection_dict[meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return WindRoseSection(
            atoms=collection,
            title="风向风能分布",
        )

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
        method1_dict: dict[str, list[ReportAtom]] = {}
        method2_dict: dict[str, list[ReportAtom]] = {}
        method3_dict: dict[str, list[ReportAtom]] = {}
        summary_dict: dict[str, list[ReportAtom]] = {}

        for input_data, meta in items:
            filtered_heights = self._filter_fifty_year_heights(input_data)
            if not filtered_heights:
                continue

            modified_input = replace(
                input_data,
                parameters=replace(input_data.parameters, heights=filtered_heights),
            )

            method1_result = self._fifty_year_method1_calculator.calculate(modified_input)
            method2_sustained, method2_sustained_params = self._fifty_year_method2_calculator.calculate_sustained(
                modified_input
            )
            method2_extreme, method2_extreme_params = self._fifty_year_method2_calculator.calculate_extreme(
                modified_input, method2_sustained
            )
            method3_sustained = self._fifty_year_method3_calculator.calculate_sustained(modified_input)
            method3_extreme = self._fifty_year_method3_calculator.calculate_extreme(
                modified_input, method3_sustained
            )

            method1_atoms = self._fifty_year_method1_builder.build(
                mast_name=meta.mast_name,
                result=method1_result,
            )
            method2_atoms = self._fifty_year_method2_builder.build(
                mast_name=meta.mast_name,
                sustained_wind=method2_sustained,
                sustained_params=method2_sustained_params,
                extreme_wind=method2_extreme,
                extreme_params=method2_extreme_params,
                qq_output_dir=Path("."),
            )
            method3_atoms = self._fifty_year_method3_builder.build(
                mast_name=meta.mast_name,
                sustained_result=method3_sustained,
                extreme_result=method3_extreme,
            )
            summary_atoms = self._fifty_year_summary_builder.build(
                mast_name=meta.mast_name,
                method1_result=method1_result,
                method2_sustained=method2_sustained,
                method2_extreme=method2_extreme,
                method3_sustained=method3_sustained,
                method3_extreme=method3_extreme,
            )

            method1_dict[meta.mast_name] = method1_atoms
            method2_dict[meta.mast_name] = method2_atoms
            method3_dict[meta.mast_name] = method3_atoms
            summary_dict[meta.mast_name] = summary_atoms

        iec_atom = NoMastIECStandardsAtom.create(
            schema=IECStandardsSchema,
            df=IEC_STANDARDS_DATA,
            meta=NoMastMeta(),
        )

        return FiftyYearMaxWindSection(
            iec_standards=FiftyYearIECStandardsSubsection(
                atoms=AtomCollection.from_dict({"_no_mast": [iec_atom]})
            ),
            method1=FiftyYearMethod1Subsection(
                atoms=AtomCollection.from_dict(method1_dict)
            ),
            method2=FiftyYearMethod2Subsection(
                atoms=AtomCollection.from_dict(method2_dict)
            ),
            method3=FiftyYearMethod3Subsection(
                atoms=AtomCollection.from_dict(method3_dict)
            ),
            summary=FiftyYearSummarySubsection(
                atoms=AtomCollection.from_dict(summary_dict)
            ),
        )

    def _filter_fifty_year_heights(
        self,
        input_data: SingleMastAnalysisInput,
    ) -> list[float]:
        """Filter heights for fifty-year max wind analysis.

        Keeps heights between 120m and 160m (inclusive) where the corresponding
        avg WindSpeed sensor is not marked as interpolated (内插).

        Args:
            input_data: Analysis input with sensors and parameters.

        Returns:
            List of filtered heights.
        """
        filtered: list[float] = []
        for h in input_data.parameters.heights:
            if not (120.0 <= h <= 160.0):
                continue
            sensor = next(
                (
                    s
                    for s in input_data.time_series.sensors
                    if s.sensor_type == "WindSpeed"
                    and s.stat_type == "avg"
                    and s.height == h
                ),
                None,
            )
            if sensor is not None and sensor.detect_interpolation_marker() != "内插":
                filtered.append(h)
        return filtered

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
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            ws_sensors = [
                s for s in input_data.time_series.sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
            ]
            results: list[AnalysisResult[WeibullSchema]] = []
            for sensor in ws_sensors:
                result = self._weibull_fitter.fit_from_input(
                    input_data,
                    sensor.column_name,
                )
                if result is not None:
                    results.append(result)
            if results:
                atoms = self._weibull_builder.build(
                    mast_name=item_meta.mast_name,
                    results=results,
                )
            else:
                atoms = []
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return WeibullSubsection(
            atoms=collection,
            title="Weibull分布拟合",
        )

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
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            profile_result = self._vertical_profile_analyzer.analyze_vertical_profile(
                input_data,
            )
            shear_result = self._vertical_profile_analyzer.calculate_wind_shear_analysis(
                input_data,
            )
            atoms = self._vertical_profile_builder.build(
                mast_name=item_meta.mast_name,
                profile_results=[profile_result],
                shear_results=[shear_result],
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return VerticalProfileSubsection(
            atoms=collection,
            title="垂直风廓线分析",
        )

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
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            result = self._wind_frequency_calculator.analyze_by_height(input_data)
            atoms = self._wind_frequency_builder.build(
                mast_name=item_meta.mast_name,
                results=[result],
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return WindFrequencySubsection(
            atoms=collection,
            title="风速频率分析",
        )

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
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            ti_result = self._turbulence_calculator.analyze_by_wind_speed(input_data)
            atoms = self._turbulence_builder.build(
                mast_name=item_meta.mast_name,
                ti_results=[ti_result],
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return TurbulenceSubsection(
            atoms=collection,
            title="湍流强度分析",
        )

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
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
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
                mast_name=item_meta.mast_name,
                time_series_result=daily_result,
                daily_result=daily_result,
                monthly_result=monthly_result,
                monthly_daily_result=monthly_daily_result,
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return WindTemporalSubsection(
            atoms=collection,
            title="风速时序分析",
        )

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
        rows: list[dict[str, float | str | None]] = []
        mast_names: list[str] = []

        for input_data, meta in analysis_inputs:
            mast_name = meta.mast_name
            ground_air_density = meta.air_density

            sensors = input_data.time_series.sensors
            df = input_data.time_series.df

            temp_sensor = next(
                (s for s in sensors if s.sensor_type == "Temperature" and s.stat_type == "avg"),
                None,
            )
            pressure_sensor = next(
                (s for s in sensors if s.sensor_type == "Pressure" and s.stat_type == "avg"),
                None,
            )

            temp_mean = df[temp_sensor.column_name].mean() if temp_sensor is not None else None
            pressure_mean = df[pressure_sensor.column_name].mean() if pressure_sensor is not None else None

            temperature = float(temp_mean) if temp_mean is not None else None
            pressure = float(pressure_mean) if pressure_mean is not None else None

            heights: list[float] = []
            if temp_sensor is not None:
                heights.append(temp_sensor.height)
            if pressure_sensor is not None:
                heights.append(pressure_sensor.height)
            reference_height = min(heights) if heights else 0.0

            rows.append({
                "mast_name": mast_name,
                "temperature": temperature,
                "pressure": pressure,
                "ground_air_density": ground_air_density,
                "reference_height": reference_height,
            })
            mast_names.append(mast_name)

        air_density_df = pl.DataFrame(rows)
        atom = MultiMastAirDensityAtom.create(
            MultiMastAirDensitySchema,
            air_density_df,
            MultiMastMeta(mast_names=mast_names),
        )
        collection = AtomCollection.from_dict({"_all_masts": [atom]})
        return AirDensitySubsection(atoms=collection)

    def generate_representative_year_calibration_section(
        self,
        analysis_inputs: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> RepresentativeYearCalibrationSubsection:
        """Generate representative year calibration section from analysis inputs.

        Args:
            analysis_inputs: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            RepresentativeYearCalibrationSubsection containing representative year calibration analysis.

        Raises:
            ValueError: If project_dir is None.
        """
        if self.project_dir is None:
            raise ValueError("project_dir is required for representative year calibration section")
        df = analyze_representative_year_calibration(self.project_dir)
        mast_names = df["mast_name"].to_list()
        atom = MultiMastRepYearCalibrationAtom.create(
            MultiMastRepYearCalibrationSchema,
            df,
            MultiMastMeta(mast_names=mast_names),
        )
        collection = AtomCollection.from_dict({"_all_masts": [atom]})
        return RepresentativeYearCalibrationSubsection(atoms=collection)


__all__ = ["ReportGenerationService"]
