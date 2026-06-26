"""Fifty-year max wind IEC standards subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.iec_standards_atom import (
    NoMastIECStandardsAtom,
)
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstHeading,
    TypstSection,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class FiftyYearMaxWindIECStandardsSubsection:
    """Subsection for IEC 61400-1 wind class standards."""

    atoms: AtomCollection
    title: str = "IEC 标准风况等级"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (NoMastIECStandardsAtom, True),
        ]

        heading = TypstHeading(text=self.title)
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(heading=heading, body=body, subsections=[])
