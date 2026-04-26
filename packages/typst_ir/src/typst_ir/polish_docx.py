"""Two-pass DOCX polishing pipeline.

Provides `polish_docx` which orchestrates the full pipeline:
extract paragraph ranges from DOCX markers, build block type map from IR,
join them to create ChangeStyle operations, create styles, apply operations,
remove markers, save.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

from typst_ir.docx_paragraph_map import extract_paragraph_ranges
from typst_ir.marker_removal import remove_markers
from typst_ir.nodes import TypstDocument
from typst_ir.polish_executor import (
    apply_change_style,
    apply_create_style,
    apply_table_format,
)
from typst_ir.polish_ir import (
    ApplyTableFormat,
    ChangeStyle,
    CreateStyle,
)
from typst_ir.polish_styles import (
    DEFAULT_STYLE_DEFS,
    DEFAULT_TABLE_FORMAT,
    TYPST_IR_FIGURE_CAPTION,
    TYPST_IR_HEADING1,
    TYPST_IR_HEADING2,
    TYPST_IR_HEADING3,
    TYPST_IR_HEADING4,
    TYPST_IR_HEADING5,
    TYPST_IR_PARAGRAPH,
    TYPST_IR_TABLE_CAPTION,
    TYPST_IR_TABLE_CONTENT,
)
from typst_ir.typst_block_type import TypstBlockType, build_block_type_map

_HEADING_STYLES = {
    1: TYPST_IR_HEADING1,
    2: TYPST_IR_HEADING2,
    3: TYPST_IR_HEADING3,
    4: TYPST_IR_HEADING4,
    5: TYPST_IR_HEADING5,
}


def _style_for_block(block_type: TypstBlockType) -> str | None:
    """Determine the style name for a given block type."""
    from typst_ir.nodes import (
        TypstBulletList,
        TypstFigure,
        TypstHeading,
        TypstOrderedList,
        TypstParagraph,
        TypstTable,
    )

    if block_type.block_type == TypstHeading:
        level = block_type.heading_level or 1
        return _HEADING_STYLES.get(min(level, 5), TYPST_IR_HEADING5)

    if block_type.block_type == TypstParagraph:
        return TYPST_IR_PARAGRAPH

    if block_type.block_type == TypstTable:
        return TYPST_IR_TABLE_CONTENT

    if block_type.block_type == TypstFigure:
        return TYPST_IR_FIGURE_CAPTION

    if block_type.block_type in (TypstBulletList, TypstOrderedList):
        return TYPST_IR_PARAGRAPH

    return None


def _build_change_styles(
    docx_ranges: list,
    block_type_map: dict[str, TypstBlockType],
    doc: Any,
) -> list[ChangeStyle]:
    """Join DocxBlockRanges with TypstBlockTypes to create ChangeStyle operations."""
    from typst_ir.nodes import TypstTable

    result: list[ChangeStyle] = []

    for docx_range in docx_ranges:
        path = docx_range.path
        if path not in block_type_map:
            continue

        block_type = block_type_map[path]
        target_style = _style_for_block(block_type)
        if target_style is None:
            continue

        # Build paragraph indices (exclude end marker)
        paragraph_indices = tuple(range(docx_range.begin, docx_range.end))

        cell_indices: tuple[tuple[int, int, int], ...] = ()
        if block_type.block_type == TypstTable and docx_range.table_indices:
            cells: list[tuple[int, int, int]] = []
            for table_idx in docx_range.table_indices:
                table = doc.tables[table_idx]
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, _cell in enumerate(row.cells):
                        cells.append((table_idx, row_idx, cell_idx))
            cell_indices = tuple(cells)

        if block_type.block_type == TypstTable and block_type.has_caption:
            if paragraph_indices:
                result.append(
                    ChangeStyle(
                        path=path,
                        target_style=TYPST_IR_TABLE_CAPTION,
                        paragraph_indices=paragraph_indices,
                        cell_table_indices=(),
                    )
                )
            if cell_indices:
                result.append(
                    ChangeStyle(
                        path=path,
                        target_style=TYPST_IR_TABLE_CONTENT,
                        paragraph_indices=(),
                        cell_table_indices=cell_indices,
                    )
                )
        elif paragraph_indices or cell_indices:
            result.append(
                ChangeStyle(
                    path=path,
                    target_style=target_style,
                    paragraph_indices=paragraph_indices,
                    cell_table_indices=cell_indices,
                )
            )

    return result


def _build_table_formats(
    docx_ranges: list,
    block_type_map: dict[str, Any],
) -> list[ApplyTableFormat]:
    from typst_ir.nodes import TypstTable

    result: list[ApplyTableFormat] = []
    for docx_range in docx_ranges:
        path = docx_range.path
        if path not in block_type_map:
            continue
        block_type = block_type_map[path]
        if block_type.block_type == TypstTable and docx_range.table_indices:
            result.append(
                ApplyTableFormat(
                    path=path,
                    table_indices=docx_range.table_indices,
                    format=DEFAULT_TABLE_FORMAT,
                )
            )
    return result


def polish_docx(
    docx_path: Path,
    ir_json_path: Path,
    output_path: Path,
) -> None:
    """Polish a DOCX using Typst IR instructions.

    Two-pass pipeline:
    1. Extract paragraph ranges from DOCX markers.
    2. Parse IR JSON and build block type map.
    3. Join ranges with block types to create ChangeStyle operations.
    4. Create any referenced styles from ``DEFAULT_STYLE_DEFS``.
    5. Apply IRs in order: CreateStyle → ChangeStyle → EditStyle.
    6. Remove IR marker paragraphs.
    7. Save the polished document.

    Args:
        docx_path: Path to input DOCX with IR markers.
        ir_json_path: Path to JSON file containing ``TypstDocument`` IR.
        output_path: Path to write the polished DOCX.
    """
    # Extract DOCX paragraph ranges from markers
    docx_ranges = extract_paragraph_ranges(docx_path)

    ir_json = ir_json_path.read_text(encoding="utf-8")
    typst_doc = TypstDocument.model_validate_json(ir_json)
    block_type_map = build_block_type_map(typst_doc)

    doc = Document(str(docx_path))

    change_styles = _build_change_styles(docx_ranges, block_type_map, doc)
    table_formats = _build_table_formats(docx_ranges, block_type_map)

    referenced_styles: set[str] = set()
    for ir in change_styles:
        referenced_styles.add(ir.target_style)

    create_irs: list[CreateStyle] = []
    seen_styles: set[str] = set()
    for style_name in referenced_styles:
        if style_name in DEFAULT_STYLE_DEFS and style_name not in seen_styles:
            style_def = DEFAULT_STYLE_DEFS[style_name]
            create_irs.append(
                CreateStyle(
                    style_name=style_name,
                    base_style=style_def.base_style,
                    properties=style_def.properties.model_dump(),
                )
            )
            seen_styles.add(style_name)

    for ir in create_irs:
        apply_create_style(doc, ir)

    for ir in change_styles:
        apply_change_style(doc, ir)

    for ir in table_formats:
        apply_table_format(doc, ir)

    remove_markers(doc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
