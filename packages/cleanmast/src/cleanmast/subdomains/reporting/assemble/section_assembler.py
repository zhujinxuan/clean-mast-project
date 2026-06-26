"""Section assembly for the reporting pipeline.

Pure functions only — NO IO, no side effects.
Maps the nine reporting capability sections into the hierarchical report tree
produced by tree_builder.
"""

from __future__ import annotations

from dataclasses import dataclass

from cleanmast.subdomains.reporting.assemble.tree_builder import (
    SectionNode,
    build_section_tree,
)
from cleanmast.subdomains.reporting.model.report_config import FlatReportConfig
from cleanmast.subdomains.reporting.protocols.section import Section
from cleanmast.subdomains.reporting.subdomains.air_density import AirDensitySection
from cleanmast.subdomains.reporting.subdomains.extreme_wind import ExtremeWindSection
from cleanmast.subdomains.reporting.subdomains.representative_year import (
    RepresentativeYearSection,
)
from cleanmast.subdomains.reporting.subdomains.turbulence import TurbulenceSection
from cleanmast.subdomains.reporting.subdomains.vertical_profile import (
    VerticalProfileSection,
)
from cleanmast.subdomains.reporting.subdomains.weibull import WeibullSection
from cleanmast.subdomains.reporting.subdomains.wind_frequency import (
    WindFrequencySection,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose import WindRoseSection
from cleanmast.subdomains.reporting.subdomains.wind_temporal import (
    WindTemporalSection,
)

SECTION_REGISTRY: dict[str, type[Section]] = {
    "air_density": AirDensitySection,
    "extreme_wind": ExtremeWindSection,
    "fifty_year_max_wind": ExtremeWindSection,
    "fifty_year_method1": ExtremeWindSection,
    "fifty_year_method2": ExtremeWindSection,
    "fifty_year_method3": ExtremeWindSection,
    "fifty_year_summary": ExtremeWindSection,
    "iec_standards": ExtremeWindSection,
    "representative_year_calibration": RepresentativeYearSection,
    "temporal": WindTemporalSection,
    "turbulence": TurbulenceSection,
    "vertical_profile": VerticalProfileSection,
    "weibull": WeibullSection,
    "wind_frequency": WindFrequencySection,
    "wind_rose": WindRoseSection,
}


@dataclass(frozen=True)
class AssembledSectionNode:
    """Node in a hierarchical tree of instantiated report sections."""

    index: str
    type: str
    title: str | None
    section: Section | None
    children: tuple["AssembledSectionNode", ...] = ()


def assemble_section_tree(
    config: FlatReportConfig,
    sections: dict[str, Section],
) -> list[AssembledSectionNode]:
    """Assemble pre-built capability sections into the report tree.

    Args:
        config: Flat report configuration defining subsection indices.
        sections: Mapping from subsection index to instantiated Section.
            Placeholder indices are ignored.

    Returns:
        Hierarchical tree of assembled sections matching the config tree.
    """
    config_tree = build_section_tree(config.subsections)

    def _convert(node: SectionNode) -> AssembledSectionNode:
        section = None if node.is_placeholder else sections.get(node.index)
        children = tuple(_convert(c) for c in node.children)
        return AssembledSectionNode(
            index=node.index,
            type=node.type,
            title=node.title,
            section=section,
            children=children,
        )

    return [_convert(root) for root in config_tree]
