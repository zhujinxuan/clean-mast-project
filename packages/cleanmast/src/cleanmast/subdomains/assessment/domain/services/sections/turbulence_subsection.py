"""Turbulence subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_multi import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_per_height import (
    SingleMastTurbulencePerHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_summary import (
    SingleMastTurbulenceSummaryAtom,
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
class TurbulenceSubsection:
    """Subsection for turbulence intensity analysis."""

    atoms: AtomCollection
    title: str = "湍流强度分析"

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
