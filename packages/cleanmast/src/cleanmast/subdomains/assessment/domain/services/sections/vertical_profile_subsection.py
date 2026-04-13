"""Vertical profile subsection.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_matrix import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.domain.services.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstHeading,
    TypstParagraph,
    TypstSection,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class VerticalProfileSubsection:
    """Subsection for vertical wind profile analysis."""

    atoms: AtomCollection
    title: str = "垂直风廓线"

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
