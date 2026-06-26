"""Wind rose section implementation with hardcoded layout.
 
ADR-GUARDRAILS: ddd-s-003-subdomain-deepening, structure-001-subdomain-layout
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_atom import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_grid_atom import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_power_grid_atom import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.services._calculator import (
    WindRoseCalculator,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.services._builder import (
    WindRoseSectionBuilder,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.value_objects.schemas import (
    WindRoseSchema,
)
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstHeading,
    TypstSection,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import (
    ReportAtom,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
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
from cleanmast.subdomains.dataingestion.entities.time_series_data import (
    TimeSeriesData,
)


@dataclass(frozen=True)
class WindRoseService:
    """Specialized service for wind rose analysis."""

    atoms: AtomCollection
    title: str = "风向风能分布"

    @classmethod
    def generate(
        cls,
        time_series_data: list[tuple[TimeSeriesData, SingleMastMeta]],
    ) -> "WindRoseService":
        """Generate wind rose section from time series data.

        Args:
            time_series_data: List of (TimeSeriesData, SingleMastMeta) tuples
                for multi-mast aggregation.

        Returns:
            WindRoseService containing wind frequency and power density roses.
        """
        collection_dict: dict[str, list[ReportAtom]] = {}
        calculator = WindRoseCalculator()
        builder = WindRoseSectionBuilder()

        for ts_data, meta in time_series_data:
            # Create SingleMastAnalysisInput from TimeSeriesData
            # (matching orchestrator's _create_analysis_input pattern)
            parameters = AnalysisParameters(
                heights=[
                    s.height
                    for s in ts_data.sensors
                    if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
                ],
                air_density=meta.air_density,
            )
            input_data = SingleMastAnalysisInput(
                time_series=ts_data,
                parameters=parameters,
                mast_name=meta.mast_name,
            )

            # Calculate wind rose statistics
            result = calculator.calculate(input_data)

            # Wrap in AnalysisResult (matching orchestrator pattern)
            builder_result = AnalysisResult.create(
                schema=WindRoseSchema,
                data=result.data,
                metadata=result.metadata,
            )

            # Build atoms for this mast
            atoms = builder.build(
                mast_name=meta.mast_name,
                results=[builder_result],
            )
            collection_dict[meta.mast_name] = atoms

        collection = AtomCollection.from_dict(collection_dict)
        return cls(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section as IR nodes for type-safe document assembly.

        Args:
            images_dir: Directory where images should be saved

        Returns:
            TypstSection with heading, body, and subsections
        """
        atom_configs = [
            (SingleMastMonthlyWindFrequencyRoseAtom, True),
            (SingleMastWindPowerRoseAtom, True),
            (SingleMastMonthlyWindRoseGridAtom, False),
            (SingleMastMonthlyWindPowerRoseGridAtom, False),
        ]

        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )


# Backward compatibility alias
WindRoseSection = WindRoseService
