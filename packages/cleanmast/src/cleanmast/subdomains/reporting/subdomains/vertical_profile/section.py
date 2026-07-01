from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Sequence

from typst_ir import TypstHeading, TypstParagraph, TypstSection
from typst_ir.nodes import TypstBodyBlock

from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.protocols.section import Section
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.assemble import (
    build_vertical_profile_atoms,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.compute import (
    analyze_vertical_profile,
    calculate_wind_shear_analysis,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.report_meta import (
    VerticalProfileAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.wind_shear_exponent_atom import (
    SingleMastWindShearExponentAtom,
)


@dataclass(frozen=True)
class VerticalProfileSection(Section):
    _atoms: Sequence[ReportAtom]
    title: str = "垂直风廓线分析"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (SingleMastWindShearExponentAtom, True),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "VerticalProfileSection":
        """Build section from analysis inputs."""
        analysis_items: list[tuple[SingleMastAnalysisInput, VerticalProfileAtomMeta]] = [
            (item, VerticalProfileAtomMeta(mast_name=item.mast_name)) for item in items
        ]
        return cls.from_analysis_inputs(analysis_items)

    @classmethod
    def from_analysis_inputs(
        cls,
        items: list[tuple[SingleMastAnalysisInput, VerticalProfileAtomMeta]],
    ) -> "VerticalProfileSection":
        """Build vertical profile section from analysis inputs and metadata."""
        atoms: list[ReportAtom] = []
        for input_data, item_meta in items:
            profile_result = analyze_vertical_profile(input_data)
            shear_result = calculate_wind_shear_analysis(input_data)
            atoms.extend(
                build_vertical_profile_atoms(
                    mast_name=item_meta.mast_name,
                    profile_results=[profile_result],
                    shear_results=[shear_result],
                )
            )
        return cls(_atoms=atoms)

    def render_ir(self, images_dir: Path) -> TypstSection:
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        if body:
            illustration = TypstParagraph(
                text="近地层风速的垂直分布主要取决于地表粗糙度和低层大气的层结状态。使用幂指数方程可以较好地描述风速的垂直廓线，其表达式为："
            )
            equation = TypstParagraph(text="$ V_2 = V_1 (Z_2 / Z_1)^alpha $")
            content: list[TypstBodyBlock] = [illustration, equation] + body
        else:
            content = []

        return TypstSection(
            heading=TypstHeading(text=self.title.replace("## ", "")),
            body=content,
            subsections=[],
        )


VerticalProfileSubsection = VerticalProfileSection

__all__ = ["VerticalProfileSection", "VerticalProfileSubsection"]
