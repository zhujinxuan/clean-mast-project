"""Fifty-year max wind summary subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.fifty_year_max_wind_summary import (
    SingleMastFiftyYearMaxWindComparisonExtremeAtom,
    SingleMastFiftyYearMaxWindComparisonSustainedAtom,
    SingleMastIECWindClassAtom,
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
class SummarySubsection:
    """Subsection for fifty-year max wind summary (五十年一遇风速总结) analysis."""

    atoms: AtomCollection
    title: str = "五十年一遇风速总结"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (SingleMastFiftyYearMaxWindComparisonSustainedAtom, True),
            (SingleMastFiftyYearMaxWindComparisonExtremeAtom, True),
            (SingleMastIECWindClassAtom, True),
        ]

        heading = TypstHeading(text=self.title)
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(heading=heading, body=body, subsections=[])
