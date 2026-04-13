"""Weibull distribution subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_subgrid import (
    SingleMastWeibullSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.services.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstHeading,
    TypstSection,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class WeibullSubsection:
    """Specialized subsection for Weibull distribution analysis."""

    atoms: AtomCollection
    title: str = "Weibull分布拟合"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        heading = TypstHeading(text=self.title)
        atom_configs = [
            (SingleMastWeibullSubgridAtom, True),
        ]
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(heading=heading, body=body, subsections=[])
