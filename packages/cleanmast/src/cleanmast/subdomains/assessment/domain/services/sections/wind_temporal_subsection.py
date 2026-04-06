"""Wind temporal analysis subsection.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_pattern import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_power_pattern import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_power import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_wind import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_pattern import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_power_pattern import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.timeseries import (
    SingleMastWindTimeseriesAtom,
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
class WindTemporalSubsection:
    """Subsection for wind temporal (timeseries) analysis.

    Renders 7 temporal atoms for each mast:
    1. SingleMastWindTimeseriesAtom - Raw time series
    2. SingleMastDailyPatternAtom - Daily (24h) wind pattern
    3. SingleMastDailyPowerPatternAtom - Daily (24h) power density pattern
    4. SingleMastMonthlyPatternAtom - Monthly wind pattern
    5. SingleMastMonthlyPowerPatternAtom - Monthly power density pattern
    6. SingleMastMonthlyDailyWindAtom - Monthly-daily combined wind pattern
    7. SingleMastMonthlyDailyPowerAtom - Monthly-daily combined power pattern
    """

    atoms: AtomCollection
    title: str = "风速时序分析"
    level: int = 2

    def render(self, images_dir: Path) -> str:
        """Render subsection with all temporal atoms.

        Args:
            images_dir: Directory for image output

        Returns:
            Typst-formatted string for the subsection
        """
        lines = [f"{'=' * self.level} {self.title}", ""]

        # Temporal atoms to render in order
        atom_types = [
            SingleMastWindTimeseriesAtom,
            SingleMastDailyPatternAtom,
            SingleMastDailyPowerPatternAtom,
            SingleMastMonthlyPatternAtom,
            SingleMastMonthlyPowerPatternAtom,
            SingleMastMonthlyDailyWindAtom,
            SingleMastMonthlyDailyPowerAtom,
        ]

        # Render each atom type for all masts
        for atom_type in atom_types:
            for mast in self.atoms.masts:
                atom = self.atoms.get(mast, atom_type)
                if atom:
                    # Summary text
                    lines.append(atom.renderSummary())
                    lines.append("")
                    # Table
                    lines.append(atom.renderTable())
                    lines.append("")
                    # Image reference
                    lines.append(atom.renderImageTypst(images_dir))
                    lines.append("")

        return "\n".join(lines)

    def render_ir(self, images_dir: Path) -> list[TypstChild]:
        """Render section to IR nodes."""
        nodes: list[TypstChild] = []

        nodes.append(TypstHeading(text=self.title, level=self.level))

        atom_types = [
            SingleMastWindTimeseriesAtom,
            SingleMastDailyPatternAtom,
            SingleMastDailyPowerPatternAtom,
            SingleMastMonthlyPatternAtom,
            SingleMastMonthlyPowerPatternAtom,
            SingleMastMonthlyDailyWindAtom,
            SingleMastMonthlyDailyPowerAtom,
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
