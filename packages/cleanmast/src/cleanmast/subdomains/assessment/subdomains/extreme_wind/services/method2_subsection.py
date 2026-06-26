"""Fifty-year max wind Method 2 subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_method2_atom import (
    SingleMastFiftyYearMaxWindMethod2ParamsAtom,
    SingleMastFiftyYearMaxWindMethod2QQExtremeAtom,
    SingleMastFiftyYearMaxWindMethod2QQSustainedAtom,
    SingleMastFiftyYearMaxWindMethod2ResultAtom,
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
class Method2Subsection:
    """Subsection for fifty-year max wind Method 2 (五日最大法) analysis."""

    atoms: AtomCollection
    title: str = "五日最大法"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (SingleMastFiftyYearMaxWindMethod2ResultAtom, True),
            (SingleMastFiftyYearMaxWindMethod2ParamsAtom, False),
            (SingleMastFiftyYearMaxWindMethod2QQSustainedAtom, False),
            (SingleMastFiftyYearMaxWindMethod2QQExtremeAtom, False),
        ]

        heading = TypstHeading(text=self.title)
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(heading=heading, body=body, subsections=[])
