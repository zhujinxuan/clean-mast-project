"""Vertical profile subsection.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from ..entities.wind_shear_matrix_atom import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from ....shared.ir_types import (
    TypstHeading,
    TypstParagraph,
    TypstSection,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import (
    ReportAtom,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from ._calculator import VerticalProfileAnalyzer
from ._builder import VerticalProfileSectionBuilder


@dataclass(frozen=True)
class VerticalProfileService:
    """Specialized service for vertical wind profile analysis."""

    atoms: AtomCollection
    title: str = "垂直风廓线"

    @classmethod
    def generate(
        cls,
        items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> "VerticalProfileService":
        """Generate vertical profile section from analysis items.

        Runs both vertical profile analysis and wind shear analysis,
        then builds report atoms for each mast.

        Args:
            items: List of (input_data, meta) tuples

        Returns:
            VerticalProfileService with generated atoms
        """
        collection_dict: dict[str, list[ReportAtom]] = {}
        analyzer = VerticalProfileAnalyzer()
        builder = VerticalProfileSectionBuilder()
        for input_data, item_meta in items:
            profile_result = analyzer.analyze_vertical_profile(input_data)
            shear_result = analyzer.calculate_wind_shear_analysis(input_data)
            atoms = builder.build(
                mast_name=item_meta.mast_name,
                profile_results=[profile_result],
                shear_results=[shear_result],
            )
            collection_dict[item_meta.mast_name] = atoms
        collection = AtomCollection.from_dict(collection_dict)
        return cls(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render subsection to IR nodes.

        Returns a TypstSection representing this section's content.

        Args:
            images_dir: Directory for generated images.

        Returns:
            TypstSection with heading, body, and subsections
        """
        atom_configs = [
            (SingleMastWindShearExponentAtom, True),
        ]

        heading = TypstHeading(text=self.title.replace("## ", ""))
        content = render_subsection_content(self.atoms, atom_configs, images_dir)
        body = []
        if content:
            illustration = TypstParagraph(
                text="近地层风速的垂直分布主要取决于地表粗糙度和低层大气的层结状态。使用幂指数方程可以较好地描述风速的垂直廓线，其表达式为："
            )
            equation = TypstParagraph(text="$ V_2 = V_1 (Z_2 / Z_1)^alpha $")
            body = [illustration, equation]
            body.extend(content)
        return TypstSection(heading=heading, body=body, subsections=[])


# Backward compatibility alias
VerticalProfileSubsection = VerticalProfileService

__all__ = ["VerticalProfileService", "VerticalProfileSubsection"]
