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
class WindTemporalSubsection:
    """Subsection for wind temporal (timeseries) analysis.

    Renders 6 temporal atoms for each mast:
    1. SingleMastMonthlyPatternAtom - Monthly wind pattern
    2. SingleMastMonthlyPowerPatternAtom - Monthly power density pattern
    3. SingleMastDailyPatternAtom - Daily (24h) wind pattern
    4. SingleMastDailyPowerPatternAtom - Daily (24h) power density pattern
    5. SingleMastMonthlyDailyWindAtom - Monthly-daily combined wind pattern
    6. SingleMastMonthlyDailyPowerAtom - Monthly-daily combined power pattern
    """

    atoms: AtomCollection
    title: str = "风速时序分析"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (SingleMastMonthlyPatternAtom, True),
            (SingleMastMonthlyPowerPatternAtom, True),
            (SingleMastDailyPatternAtom, True),
            (SingleMastDailyPowerPatternAtom, True),
            (SingleMastMonthlyDailyWindAtom, False),
            (SingleMastMonthlyDailyPowerAtom, False),
        ]

        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
