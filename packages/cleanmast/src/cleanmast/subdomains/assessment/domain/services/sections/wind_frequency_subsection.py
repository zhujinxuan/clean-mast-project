"""Wind frequency subsection.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_distribution_subgrid import (
    SingleMastWindDistributionSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_hours import (
    SingleMastWindFrequencyHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_power_hours import (
    SingleMastWindPowerHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_productive_range import (
    SingleMastWindProductiveRangeAtom,
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
class WindFrequencySubsection:
    """Subsection for wind frequency analysis."""

    atoms: AtomCollection
    title: str = "风速频率分析"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (SingleMastWindFrequencyHoursAtom, True),
            (SingleMastWindPowerHoursAtom, True),
            (SingleMastWindDistributionSubgridAtom, True),
            (SingleMastWindProductiveRangeAtom, True),
        ]
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
