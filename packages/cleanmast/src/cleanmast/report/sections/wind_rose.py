"""Wind rose section implementation with hardcoded layout."""

from dataclasses import dataclass
from pathlib import Path

from ..protocols import Section
from ..collection import AtomCollection
from ..atoms.single_mast.wind_rose import (
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
