"""Weibull distribution subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import AnalysisResult
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import SingleMastMeta
from cleanmast.subdomains.assessment.subdomains.weibull.value_objects.schemas import WeibullSchema
from cleanmast.subdomains.assessment.subdomains.weibull.services._calculator import WeibullFitter
from cleanmast.subdomains.assessment.subdomains.weibull.services._builder import WeibullSectionBuilder
from cleanmast.subdomains.assessment.subdomains.weibull.entities.weibull_subgrid_atom import (
    SingleMastWeibullSubgridAtom,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
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


@dataclass(frozen=True)
class WeibullService:
    """Specialized service for Weibull distribution analysis."""

    atoms: AtomCollection
    title: str = "Weibull分布拟合"

    @classmethod
    def generate(
        cls,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> "WeibullService":
        """Generate Weibull distribution section."""
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            ws_sensors = [
                s for s in input_data.time_series.sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
            ]
            results: list[AnalysisResult[WeibullSchema]] = []
            fitter = WeibullFitter()
            for sensor in ws_sensors:
                result = fitter.fit_from_input(input_data, sensor.column_name)
                if result is not None:
                    results.append(result)
            if results:
                builder = WeibullSectionBuilder()
                atoms = builder.build(mast_name=item_meta.mast_name, results=results)
            else:
                atoms = []
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return WeibullService(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        heading = TypstHeading(text=self.title)
        atom_configs = [
            (SingleMastWeibullSubgridAtom, True),
        ]
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(heading=heading, body=body, subsections=[])


# Backward compatibility alias
WeibullSubsection = WeibullService
