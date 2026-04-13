"""MappingBuilder for orchestrating DOCX to Typst IR mapping creation.

Provides the MappingBuilder class that coordinates the complete mapping
workflow between DOCX source documents and Typst IR representations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from typst_ir.mapping.injector import extract_paragraphs
from typst_ir.mapping.matcher import DocxMatcher
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.mapping.types import DocxTypstMapping, MappingEntry
from typst_ir.mapping.visitor import MappingVisitor
from typst_ir.nodes import TypstDocument

if TYPE_CHECKING:
    pass


class MappingBuilder:
    """Orchestrates the complete mapping workflow.

    Coordinates NodeRegistry, MappingVisitor, and paragraph extraction
to create a complete DocxTypstMapping that links IR nodes to their
    source document locations.

    Attributes:
        registry: NodeRegistry for getting NodeIDs
        mappings: Dictionary of canonical node ID to MappingEntry
    """

    def __init__(self, registry: NodeRegistry) -> None:
        """Initialize builder with NodeRegistry.

        Args:
            registry: NodeRegistry instance for node identification
        """
        self.registry = registry
        self.mappings: dict[str, MappingEntry] = {}

    def build(self, document: TypstDocument, docx_path: str) -> DocxTypstMapping:
        """Build complete mapping between Typst IR and DOCX source.

        Orchestrates the mapping process:
        1. Initialize NodeRegistry with the document
        2. Use MappingVisitor to traverse IR and create mappings
        3. Extract paragraphs from DOCX file
        4. Match IR nodes to paragraphs (index-based)
        5. Build and return DocxTypstMapping

        Args:
            document: TypstDocument IR to map
            docx_path: Path to the source DOCX file

        Returns:
            Complete DocxTypstMapping with all entries and path_index
        """
        self.registry.initialize(document)

        docx_path_obj = Path(docx_path)
        detection_lookup: dict[str, MappingEntry] = {}
        source_end = 0

        try:
            from docx import Document as DocxDocument

            docx_doc = DocxDocument(str(docx_path_obj))
            matcher = DocxMatcher(self.registry)
            detected_entries = matcher.match(document.children, docx_doc)
            for entry in detected_entries:
                detection_lookup[entry.node_id.canonical] = entry
            paragraphs = extract_paragraphs(docx_path_obj)
            source_end = len(paragraphs)
        except Exception:
            source_end = 0

        visitor = MappingVisitor(self.registry, detection_lookup=detection_lookup)
        mapping_entries = visitor.visit_document(document, 0, source_end)

        entries: dict[str, MappingEntry] = {}
        for entry in mapping_entries:
            canonical_id = entry.node_id.canonical
            entries[canonical_id] = entry

        path_index: dict[str, str] = {}
        for entry in entries.values():
            path_index[entry.node_id.path] = entry.node_id.canonical

        return DocxTypstMapping(
            version="1.0.0",
            full_hash=self.registry.full_hash,
            entries=entries,
            path_index=path_index,
        )
