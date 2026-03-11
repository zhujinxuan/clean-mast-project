"""Representative year wind power section.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.reporting.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.reporting.value_objects.single_mast.monthly_wind_power import (
    SingleMastMonthlyWindPowerAtom as MonthlyWindPowerAtom,
)


@dataclass(frozen=True)
class RepresentativeWindPowerSection:
    """Section for representative year wind power analysis."""

    atoms: AtomCollection
    title: str = "代表年各月风功率结果"
    level: int = 1

    def render(self, images_dir: Path) -> str:
        """Render section with narrative, tables, and figures."""
        lines = [f"{'=' * self.level} {self.title}", ""]
        
        # Narrative for each mast
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, MonthlyWindPowerAtom)
            if atom:
                lines.append(atom.renderSummary())
                lines.append("")
        
        # All tables
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, MonthlyWindPowerAtom)
            if atom:
                lines.append(atom.renderTable())
                lines.append("")
        
        # All figures
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, MonthlyWindPowerAtom)
            if atom:
                lines.append(atom.renderImageTypst(images_dir))
                lines.append("")
        
        return "\n".join(lines)
