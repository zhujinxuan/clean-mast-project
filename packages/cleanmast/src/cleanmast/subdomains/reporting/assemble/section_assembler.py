"""Section assembly for the reporting pipeline.

Pure functions only — NO IO, no side effects.
Assembles pre-built capability sections into the hierarchical report tree
produced by tree_builder.
"""

from __future__ import annotations

from dataclasses import dataclass

from cleanmast.subdomains.configuration.model.report_config import FlatReportConfig
from cleanmast.subdomains.reporting.assemble.tree_builder import build_section_tree
from cleanmast.subdomains.reporting.model.section_node import SectionNode
from cleanmast.subdomains.reporting.protocols.section import Section


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
