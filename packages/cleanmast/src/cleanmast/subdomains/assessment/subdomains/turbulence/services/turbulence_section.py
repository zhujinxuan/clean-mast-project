"""Turbulence subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_per_height_atom import (
    SingleMastTurbulencePerHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_summary_atom import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.services._builder import (
    TurbulenceSectionBuilder,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.services._calculator import (
    TurbulenceCalculator,
)
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstHeading,
    TypstParagraph,
    TypstSection,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class TurbulenceService:
    """Specialized service for turbulence intensity analysis."""

    atoms: AtomCollection
    title: str = "湍流强度分析"

    @classmethod
    def generate(
        cls,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> "TurbulenceService":
        """Generate turbulence intensity section.

        Args:
            items: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            TurbulenceService instance with generated atoms.
        """
        collection_dict: dict[str, list[ReportAtom]] = {}
        for input_data, item_meta in items:
            ti_result = TurbulenceCalculator().analyze_by_wind_speed(input_data)
            atoms = TurbulenceSectionBuilder().build(
                mast_name=item_meta.mast_name,
                ti_results=[ti_result],
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return cls(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (SingleMastTurbulenceSummaryAtom, True),
            (SingleMastTurbulencePerHeightAtom, False),
            (SingleMastTurbulenceMultiHeightAtom, False),
        ]

        heading = TypstHeading(text=self.title)
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=heading,
            body=[TypstParagraph(text="#pagebreak()")] + body,
            subsections=[],
        )


# Backward compatibility alias
TurbulenceSubsection = TurbulenceService
