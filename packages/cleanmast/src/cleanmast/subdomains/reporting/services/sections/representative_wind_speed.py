"""Representative year wind speed section.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.reporting.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.reporting.value_objects.single_mast.monthly_wind import (
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
