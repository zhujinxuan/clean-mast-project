"""Wind rose section implementation with hardcoded layout.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_grid import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_power_grid import (
    SingleMastMonthlyWindPowerRoseGridAtom,
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
class WindRoseSection:
    """Specialized section for wind rose analysis."""

    atoms: AtomCollection
    title: str = "风向风能分布"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section as IR nodes for type-safe document assembly.

        Args:
            images_dir: Directory where images should be saved

        Returns:
            TypstSection with heading, body, and subsections
        """
        atom_configs = [
            (SingleMastMonthlyWindFrequencyRoseAtom, True),
            (SingleMastWindPowerRoseAtom, True),
            (SingleMastMonthlyWindRoseGridAtom, False),
            (SingleMastMonthlyWindPowerRoseGridAtom, False),
        ]

        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
