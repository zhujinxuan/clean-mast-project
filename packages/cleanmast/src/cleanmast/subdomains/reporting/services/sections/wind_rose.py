"""Wind rose section implementation with hardcoded layout.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.reporting.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.reporting.value_objects.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)


@dataclass(frozen=True)
class WindRoseSection:
    """Specialized section for wind rose analysis."""

    atoms: AtomCollection
    title: str = "风向风能分布"
    level: int = 1

    def render(self, images_dir: Path) -> str:
        """Hardcoded optimal layout for wind roses."""
        lines = [f"== {self.title}", ""]

        # Combined summary
        summaries = []
        for mast in self.atoms.masts:
            freq = self.atoms.get(mast, SingleMastMonthlyWindFrequencyRoseAtom)
            power = self.atoms.get(mast, SingleMastWindPowerRoseAtom)
            if freq:
                summaries.append(freq.renderSummary())
            if power:
                summaries.append(power.renderSummary())

        if summaries:
            lines.append(" ".join(summaries))
            lines.append("")

        # All figures
        for mast in self.atoms.masts:
            freq = self.atoms.get(mast, SingleMastMonthlyWindFrequencyRoseAtom)
            power = self.atoms.get(mast, SingleMastWindPowerRoseAtom)
            if freq:
                lines.append(freq.renderImageTypst(images_dir))
            if power:
                lines.append(power.renderImageTypst(images_dir))

        # All tables
        for mast in self.atoms.masts:
            freq = self.atoms.get(mast, SingleMastMonthlyWindFrequencyRoseAtom)
            power = self.atoms.get(mast, SingleMastWindPowerRoseAtom)
            if freq:
                lines.append(freq.renderTable())
            if power:
                lines.append(power.renderTable())

        return "\n".join(lines)
