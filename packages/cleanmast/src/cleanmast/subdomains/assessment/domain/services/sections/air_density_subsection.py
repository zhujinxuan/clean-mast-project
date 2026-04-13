"""Air density subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from typst_ir import TypstEquation

from cleanmast.subdomains.assessment.domain.entities.multi_masts.air_density import (
    MultiMastAirDensityAtom,
)
from cleanmast.subdomains.assessment.domain.services.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstHeading,
    TypstParagraph,
    TypstSection,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class AirDensitySubsection:
    """Subsection for air density calculation."""

    atoms: AtomCollection
    title: str = "空气密度计算"

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (MultiMastAirDensityAtom, False),
        ]

        methodology = TypstParagraph(
            text=(
                "空气密度直接影响风能的大小，是风资源评估中的重要参数。"
                "根据《风电场风能资源评估方法》（GB/T 18710-2002），"
                "空气密度采用理想气体状态方程计算。"
                "不同高度空气密度按气压高度公式进行高度修正，"
                "其中 T = 288.15 - 0.0065 × h₀。"
            )
        )
        equation = TypstEquation(
            latex=r"rho = rho_0 times exp(- frac(g times (h - h_0), R times T))",
            display=True,
        )
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[methodology, equation, *body],
            subsections=[],
        )
