"""Reporting assembly layer.

Exports tree building and section assembly utilities.
"""

from cleanmast.subdomains.reporting.assemble.section_assembler import (
    SECTION_REGISTRY,
    AssembledSectionNode,
    assemble_section_tree,
)
from cleanmast.subdomains.reporting.assemble.tree_builder import (
    SectionNode,
    build_section_tree,
    flatten_tree,
)

__all__ = [
    "SECTION_REGISTRY",
    "AssembledSectionNode",
    "SectionNode",
    "assemble_section_tree",
    "build_section_tree",
    "flatten_tree",
]
