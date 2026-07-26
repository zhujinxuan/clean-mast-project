"""Reporting assembly layer.

Exports tree building and section assembly utilities.
"""

from cleanmast.subdomains.reporting.assemble.section_assembler import (
    AssembledSectionNode,
    assemble_section_tree,
)
from cleanmast.subdomains.reporting.assemble.tree_builder import build_section_tree
from cleanmast.subdomains.reporting.model.section_node import (
    SectionNode,
    flatten_tree,
)

__all__ = [
    "AssembledSectionNode",
    "SectionNode",
    "assemble_section_tree",
    "build_section_tree",
    "flatten_tree",
]
