"""Representative year wind speed section.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.types import (
    TypstChild,
    TypstFigure,
    TypstHeading,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.monthly_wind import (
    SingleMastMonthlyWindAtom as MonthlyWindSpeedAtom,
)


@dataclass(frozen=True)
class RepresentativeWindSpeedSection:
    """Section for representative year wind speed analysis."""

    atoms: AtomCollection
    title: str = "代表年各月风速结果"
    level: int = 1

    def render(self, images_dir: Path) -> str:
        """Render section with narrative, tables, and figures."""
        lines = [f"{'=' * self.level} {self.title}", ""]
        
        # Narrative for each mast
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, MonthlyWindSpeedAtom)
            if atom:
                lines.append(atom.renderSummary())
                lines.append("")
        
        # All tables
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, MonthlyWindSpeedAtom)
            if atom:
                lines.append(atom.renderTable())
                lines.append("")
        
        # All figures
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, MonthlyWindSpeedAtom)
            if atom:
                lines.append(atom.renderImageTypst(images_dir))
                lines.append("")
        
        return "\n".join(lines)

    def render_ir(self, images_dir: Path) -> list[TypstChild]:
        """Render section to IR nodes."""
        nodes: list[TypstChild] = []

        nodes.append(TypstHeading(text=self.title, level=self.level))

        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, MonthlyWindSpeedAtom)
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
