"""Turbulence subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_intensity import (
    SingleMastTurbulenceIntensityAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_multi import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_sector import (
    SingleMastTurbulenceSectorAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_summary import (
    SingleMastTurbulenceSummaryAtom,
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
class TurbulenceSubsection:
    """Subsection for turbulence intensity analysis."""

    atoms: AtomCollection
    title: str = "湍流强度分析"
    level: int = 2

    def render(self, images_dir: Path) -> str:
        """Render turbulence subsection with all turbulence atoms."""
        lines = [f"{'=' * (self.level + 1)} {self.title}", ""]

        summaries = []
        for mast in self.atoms.masts:
            summary = self.atoms.get(mast, SingleMastTurbulenceSummaryAtom)
            if summary:
                summaries.append(summary.renderSummary())

        if summaries:
            lines.append(" ".join(summaries))
            lines.append("")

        for mast in self.atoms.masts:
            intensity = self.atoms.get(mast, SingleMastTurbulenceIntensityAtom)
            if intensity:
                lines.append(intensity.renderImageTypst(images_dir))

        for mast in self.atoms.masts:
            multi = self.atoms.get(mast, SingleMastTurbulenceMultiHeightAtom)
            if multi:
                lines.append(multi.renderImageTypst(images_dir))

        for mast in self.atoms.masts:
            sector = self.atoms.get(mast, SingleMastTurbulenceSectorAtom)
            if sector:
                lines.append(sector.renderImageTypst(images_dir))

        for mast in self.atoms.masts:
            summary = self.atoms.get(mast, SingleMastTurbulenceSummaryAtom)
            if summary:
                lines.append(summary.renderTable())

        for mast in self.atoms.masts:
            intensity = self.atoms.get(mast, SingleMastTurbulenceIntensityAtom)
            if intensity:
                lines.append(intensity.renderTable())

        for mast in self.atoms.masts:
            sector = self.atoms.get(mast, SingleMastTurbulenceSectorAtom)
            if sector:
                lines.append(sector.renderTable())

        return "\n".join(lines)

    def render_ir(self, images_dir: Path) -> list[TypstChild]:
        """Render section to IR nodes."""
        nodes: list[TypstChild] = []

        nodes.append(TypstHeading(text=self.title, level=self.level))

        atom_types = [
            SingleMastTurbulenceIntensityAtom,
            SingleMastTurbulenceMultiHeightAtom,
            SingleMastTurbulenceSectorAtom,
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
