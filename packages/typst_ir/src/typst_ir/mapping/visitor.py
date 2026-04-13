"""MappingVisitor for traversing Typst IR and building source mappings.

Provides the MappingVisitor class to traverse a TypstDocument IR tree and
create MappingEntry records that link IR nodes to their source document locations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from typst_ir.mapping.registry import NodeRegistry
from typst_ir.mapping.types import ConfidenceLevel, DetectionMethod, MappingEntry
from typst_ir.nodes import (
    TypstBlock,
    TypstBulletList,
    TypstCodeBlock,
    TypstDocument,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstRawBlock,
    TypstSection,
    TypstTable,
)


@dataclass(frozen=True)
class SourceRange:
    """Source range for constraining child mappings."""

    start: int
    end: int

    def contains(self, child_start: int, child_end: int) -> bool:
        """Check if child range is within this range."""
        return child_start >= self.start and child_end <= self.end


class MappingVisitor:
    """Visitor for traversing Typst IR and building source mappings.

    Traverses the IR tree depth-first and creates MappingEntry records
    for each node, linking IR nodes to their source document locations.
    Ensures child ranges are properly constrained within parent ranges.

    Attributes:
        registry: NodeRegistry for getting NodeIDs
        mappings: List of MappingEntry records accumulated during traversal
    """

    def __init__(
        self,
        registry: NodeRegistry,
        detection_lookup: dict[str, MappingEntry] | None = None,
    ) -> None:
        """Initialize visitor with NodeRegistry.

        Args:
            registry: Initialized NodeRegistry for looking up NodeIDs
            detection_lookup: Optional lookup from node canonical ID to
                pre-detected MappingEntry from DocxMatcher
        """
        self.registry = registry
        self.mappings: list[MappingEntry] = []
        self.detection_lookup = detection_lookup or {}

    def visit_document(
        self, document: TypstDocument, source_start: int = 0, source_end: int = 0
    ) -> list[MappingEntry]:
        """Visit document root and all children.

        Creates mapping for the document itself (if it has children),
        then traverses all children.

        Args:
            document: Root document to visit
            source_start: Start index in source document
            source_end: End index in source document

        Returns:
            List of all MappingEntry records
        """
        self.mappings = []

        has_children = (
            hasattr(document, "children") and len(document.children) > 0
        )

        if has_children:
            doc_range = self._create_mapping(document, source_start, source_end)
            self._visit_children(document.children, doc_range)
        else:
            doc_range = SourceRange(source_start, source_end)

        return self.mappings

    def _visit_children(
        self, children: Sequence[TypstBlock], parent_range: SourceRange
    ) -> None:
        """Visit a list of children, distributing the parent range.

        Divides the parent range evenly among children to ensure each child
        gets a valid sub-range within the parent.

        Args:
            children: List of child blocks to visit
            parent_range: Source range that constrains all children
        """
        if not children:
            return

        # Divide parent range among children
        total_range = parent_range.end - parent_range.start
        child_range_size = total_range // len(children)

        for idx, child in enumerate(children):
            child_start = parent_range.start + (idx * child_range_size)
            # Last child gets remainder to ensure full coverage
            if idx == len(children) - 1:
                child_end = parent_range.end
            else:
                child_end = child_start + child_range_size

            self._visit_block(child, SourceRange(child_start, child_end))

    def _visit_block(self, block: TypstBlock, parent_range: SourceRange) -> None:
        """Visit a single block, dispatching to appropriate handler.

        Uses duck typing to determine block type and route to the
        appropriate visit method.

        Args:
            block: Block to visit
            parent_range: Source range that constrains this block
        """
        # Dispatch based on duck typing (same pattern as serializer.py)
        # 1. TypstTable - has data and headers
        if hasattr(block, "data") and hasattr(block, "headers"):
            self._visit_table(cast(TypstTable, block), parent_range)
        # 2. TypstFigure - has content, caption, kind
        elif (
            hasattr(block, "content")
            and hasattr(block, "caption")
            and hasattr(block, "kind")
        ):
            self._visit_figure(cast(TypstFigure, block), parent_range)
        # 3. TypstEquation - has latex and display
        elif hasattr(block, "latex") and hasattr(block, "display"):
            self._visit_equation(cast(TypstEquation, block), parent_range)
        # 4. TypstCodeBlock - has text and language (not just text)
        elif hasattr(block, "text") and hasattr(block, "language"):
            self._visit_code_block(cast(TypstCodeBlock, block), parent_range)
        # 5. TypstRawBlock - has format and text
        elif hasattr(block, "format") and hasattr(block, "text"):
            self._visit_raw_block(cast(TypstRawBlock, block), parent_range)
        # 6. TypstHeading - identified by typst_type (must check before paragraph)
        elif getattr(block, 'typst_type', None) == 'TypstHeading':
            self._visit_heading(cast(TypstHeading, block), parent_range)
        # 7. TypstParagraph - has text (and no level, format, or language)
        elif hasattr(block, "text"):
            self._visit_paragraph(cast(TypstParagraph, block), parent_range)
        # 8. TypstSection - has heading, body, and subsections
        elif hasattr(block, "heading") and hasattr(block, "body") and hasattr(block, "subsections"):
            self._visit_section(cast(TypstSection, block), parent_range)
        # 9. TypstOrderedList - has items and start
        elif hasattr(block, "items") and hasattr(block, "start"):
            self._visit_ordered_list(cast(TypstOrderedList, block), parent_range)
        # 10. TypstBulletList - has items (but no start)
        elif hasattr(block, "items"):
            self._visit_bullet_list(cast(TypstBulletList, block), parent_range)
        else:
            raise TypeError(f"Unknown block type: {type(block).__name__}")

    def _create_mapping(
        self, node: TypstDocument | TypstBlock, source_start: int, source_end: int
    ) -> SourceRange:
        """Create a mapping entry for a node.

        Gets the NodeID from the registry and creates a MappingEntry.
        If a detection result exists for this node, its values are used
        instead of the provided positional range.

        Args:
            node: Node to create mapping for
            source_start: Start index in source document
            source_end: End index in source document

        Returns:
            SourceRange for the created mapping
        """
        node_id = self.registry.get_id(node)
        detected = self.detection_lookup.get(node_id.canonical)
        if detected is not None:
            entry = MappingEntry(
                node_id=node_id,
                source_start=detected.source_start,
                source_end=detected.source_end,
                method=detected.method,
                confidence=detected.confidence,
                details=detected.details,
            )
            self.mappings.append(entry)
            return SourceRange(detected.source_start, detected.source_end)

        entry = MappingEntry(
            node_id=node_id,
            source_start=source_start,
            source_end=source_end,
            method=DetectionMethod.positional,
            confidence=ConfidenceLevel.low,
        )
        self.mappings.append(entry)
        return SourceRange(source_start, source_end)

    def _visit_paragraph(
        self, paragraph: TypstParagraph, parent_range: SourceRange
    ) -> None:
        """Visit paragraph node.

        Creates a mapping entry for the paragraph within the parent range.

        Args:
            paragraph: Paragraph to visit
            parent_range: Source range that constrains this paragraph
        """
        self._create_mapping(paragraph, parent_range.start, parent_range.end)

    def _visit_heading(self, heading: TypstHeading, parent_range: SourceRange) -> None:
        """Visit heading node.

        Creates a mapping entry for the heading within the parent range.

        Args:
            heading: Heading to visit
            parent_range: Source range that constrains this heading
        """
        self._create_mapping(heading, parent_range.start, parent_range.end)

    def _visit_section(self, section: TypstSection, parent_range: SourceRange) -> None:
        """Visit section node with heading, body, and subsections.

        Creates mappings for the section itself, its heading, body items,
        and all subsections. The section establishes a range that constrains
        all its children.

        Args:
            section: Section to visit
            parent_range: Source range that constrains this section
        """
        section_range = self._create_mapping(section, parent_range.start, parent_range.end)
        heading_size = min(1, (section_range.end - section_range.start) // 10)
        heading_end = section_range.start + heading_size
        self._visit_heading(section.heading, SourceRange(section_range.start, heading_end))
        items_to_visit = list(section.body) + list(section.subsections)
        if items_to_visit:
            children_range = SourceRange(heading_end, section_range.end)
            self._visit_children(items_to_visit, children_range)

    def _visit_table(self, table: TypstTable, parent_range: SourceRange) -> None:
        """Visit table node.

        Creates a mapping entry for the table within the parent range.

        Args:
            table: Table to visit
            parent_range: Source range that constrains this table
        """
        self._create_mapping(table, parent_range.start, parent_range.end)

    def _visit_figure(self, figure: TypstFigure, parent_range: SourceRange) -> None:
        """Visit figure node.

        Creates a mapping entry for the figure within the parent range.

        Args:
            figure: Figure to visit
            parent_range: Source range that constrains this figure
        """
        self._create_mapping(figure, parent_range.start, parent_range.end)

    def _visit_equation(self, equation: TypstEquation, parent_range: SourceRange) -> None:
        """Visit equation node.

        Creates a mapping entry for the equation within the parent range.

        Args:
            equation: Equation to visit
            parent_range: Source range that constrains this equation
        """
        self._create_mapping(equation, parent_range.start, parent_range.end)

    def _visit_code_block(
        self, code_block: TypstCodeBlock, parent_range: SourceRange
    ) -> None:
        """Visit code block node.

        Creates a mapping entry for the code block within the parent range.

        Args:
            code_block: Code block to visit
            parent_range: Source range that constrains this code block
        """
        self._create_mapping(code_block, parent_range.start, parent_range.end)

    def _visit_raw_block(self, raw_block: TypstRawBlock, parent_range: SourceRange) -> None:
        """Visit raw block node.

        Creates a mapping entry for the raw block within the parent range.

        Args:
            raw_block: Raw block to visit
            parent_range: Source range that constrains this raw block
        """
        self._create_mapping(raw_block, parent_range.start, parent_range.end)

    def _visit_bullet_list(
        self, bullet_list: TypstBulletList, parent_range: SourceRange
    ) -> None:
        """Visit bullet list node.

        Creates a mapping for the list itself and all items within.

        Args:
            bullet_list: Bullet list to visit
            parent_range: Source range that constrains this list
        """
        # Create mapping for the list itself
        list_range = self._create_mapping(
            bullet_list, parent_range.start, parent_range.end
        )

        # Visit all items (each item is a list of blocks)
        if bullet_list.items:
            self._visit_list_items(bullet_list.items, list_range)

    def _visit_ordered_list(
        self, ordered_list: TypstOrderedList, parent_range: SourceRange
    ) -> None:
        """Visit ordered list node.

        Creates a mapping for the list itself and all items within.

        Args:
            ordered_list: Ordered list to visit
            parent_range: Source range that constrains this list
        """
        # Create mapping for the list itself
        list_range = self._create_mapping(
            ordered_list, parent_range.start, parent_range.end
        )

        # Visit all items (each item is a list of blocks)
        if ordered_list.items:
            self._visit_list_items(ordered_list.items, list_range)

    def _visit_list_items(
        self, items: list[list[TypstBlock]], parent_range: SourceRange
    ) -> None:
        """Visit list items, distributing the parent range among them.

        Args:
            items: List of items, where each item is a list of blocks
            parent_range: Source range that constrains all items
        """
        if not items:
            return

        # Divide parent range among items
        total_range = parent_range.end - parent_range.start
        item_range_size = total_range // len(items)

        for idx, item in enumerate(items):
            item_start = parent_range.start + (idx * item_range_size)
            # Last item gets remainder
            if idx == len(items) - 1:
                item_end = parent_range.end
            else:
                item_end = item_start + item_range_size

            item_range = SourceRange(item_start, item_end)

            # Each item is a list of blocks - visit them
            if item:
                self._visit_children(item, item_range)
