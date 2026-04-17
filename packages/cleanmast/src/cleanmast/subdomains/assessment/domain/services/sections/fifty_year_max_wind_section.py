"""Fifty-year max wind section implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_iec_standards_subsection import (
    IECStandardsSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_method1_subsection import (
    Method1Subsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_method2_subsection import (
    Method2Subsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_method3_subsection import (
    Method3Subsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.fifty_year_max_wind_summary_subsection import (
    SummarySubsection,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstHeading,
    TypstSection,
)


@dataclass(frozen=True)
class FiftyYearMaxWindSection:
    """Section for fifty-year max wind analysis."""

    iec_standards: IECStandardsSubsection
    method1: Method1Subsection
    method2: Method2Subsection
    method3: Method3Subsection
    summary: SummarySubsection
    title: str = "五十年一遇最大风速"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section as IR nodes for type-safe document assembly.

        Args:
            images_dir: Directory where images should be saved

        Returns:
            TypstSection with heading, body, and nested subsections
        """
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[],
            subsections=[
                self.iec_standards.render_ir(images_dir),
                self.method1.render_ir(images_dir),
                self.method2.render_ir(images_dir),
                self.method3.render_ir(images_dir),
                self.summary.render_ir(images_dir),
            ],
        )
