"""Weibull distribution subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_distribution import (
    SingleMastWeibullDistributionAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_multi import (
    SingleMastWeibullMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_parameters import (
    SingleMastWeibullParametersAtom,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstChild,
    TypstFigure,
    TypstHeading,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class WeibullSubsection:
    """Specialized subsection for Weibull distribution analysis."""

    atoms: AtomCollection
    title: str = "Weibull分布拟合"
    level: int = 2

    def render(self, images_dir: Path) -> str:
        """Render Weibull distribution subsection with all atoms."""
        lines = [self.title, ""]

        # Render summaries from all Weibull atoms
        summaries = []
        for mast in self.atoms.masts:
            dist = self.atoms.get(mast, SingleMastWeibullDistributionAtom)
            multi = self.atoms.get(mast, SingleMastWeibullMultiHeightAtom)
            params = self.atoms.get(mast, SingleMastWeibullParametersAtom)

            if dist:
                summaries.append(dist.renderSummary())
            if multi:
                summaries.append(multi.renderSummary())
            if params:
                summaries.append(params.renderSummary())

        if summaries:
            lines.append(" ".join(summaries))
            lines.append("")

        # Render images from all Weibull atoms
        for mast in self.atoms.masts:
            dist = self.atoms.get(mast, SingleMastWeibullDistributionAtom)
            multi = self.atoms.get(mast, SingleMastWeibullMultiHeightAtom)

            if dist:
                lines.append(dist.renderImageTypst(images_dir))
            if multi:
                lines.append(multi.renderImageTypst(images_dir))

        # Render tables from all Weibull atoms
        for mast in self.atoms.masts:
            dist = self.atoms.get(mast, SingleMastWeibullDistributionAtom)
            params = self.atoms.get(mast, SingleMastWeibullParametersAtom)

            if dist:
                lines.append(dist.renderTable())
            if params:
                lines.append(params.renderTable())

        return "\n".join(lines)

    def render_ir(self, images_dir: Path) -> list[TypstChild]:
        """Render section to IR nodes."""
        nodes: list[TypstChild] = []

        nodes.append(TypstHeading(text=self.title, level=self.level))

        atom_types = [
            SingleMastWeibullDistributionAtom,
            SingleMastWeibullMultiHeightAtom,
        ]

        for atom_type in atom_types:
            for mast in self.atoms.masts:
                atom = self.atoms.get(mast, atom_type)
                if atom:
                    image_path = atom.renderImage(images_dir)
                    if image_path and image_path.name and image_path != images_dir:
                        try:
                            rel_path = image_path.relative_to(images_dir.parent)
                            caption = getattr(atom.meta, "caption", "Figure")
                            nodes.append(TypstFigure(content=rel_path.as_posix(), caption=caption))
                        except ValueError:
                            pass

        return nodes
