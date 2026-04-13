"""DOCX style applicator for Polish IR operations.

Applies ``StyleOp`` instructions to a ``python-docx`` ``Document``,
including font properties, paragraph spacing, and mixed CJK/Latin fonts.
Also applies ``RenumberOp`` instructions to renumber headings, figures,
and tables based on the Typst IR tree structure.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

from docx.shared import Pt, RGBColor

from typst_ir.mapping.types import DocxTypstMapping
from typst_ir.polish.types import RenumberOp, StyleOp

logger = logging.getLogger(__name__)

_SECTION_RE = re.compile(r"(?:children|subsections)\.(\d+)\[TypstSection\]")


def apply_styles(doc: Any, style_ops: list[StyleOp]) -> None:
    """Apply a list of ``StyleOp`` transformations to a DOCX document.

    For each ``StyleOp``:
      - Looks up the named style in ``doc.styles``
      - Applies font name, size, style, color, and paragraph spacing
      - If both ``font_name_chinese`` and ``font_name_latin`` are set,
        additionally calls ``apply_mixed_fonts_to_style``

    Missing styles are logged as warnings and skipped.

    Args:
        doc: The ``python-docx`` ``Document`` to modify in place.
        style_ops: List of style operations to apply.
    """
    for style_op in style_ops:
        try:
            style = doc.styles[style_op.style_name]
        except KeyError:
            logger.warning("Style '%s' not found in document", style_op.style_name)
            continue

        if style_op.font_name is not None:
            style.font.name = style_op.font_name

        if style_op.font_size is not None:
            style.font.size = Pt(style_op.font_size)

        if style_op.font_style is not None:
            bold, italic = _parse_font_style(style_op.font_style)
            style.font.bold = bold
            style.font.italic = italic

        if style_op.font_color is not None:
            hex_value = style_op.font_color.lstrip("#")
            style.font.color.rgb = RGBColor.from_string(hex_value)

        if style_op.line_spacing_before is not None:
            style.paragraph_format.space_before = Pt(style_op.line_spacing_before)

        if style_op.line_spacing_after is not None:
            style.paragraph_format.space_after = Pt(style_op.line_spacing_after)

        if style_op.line_spacing is not None:
            style.paragraph_format.line_spacing = Pt(style_op.line_spacing)

        if style_op.font_name_chinese is not None and style_op.font_name_latin is not None:
            apply_mixed_fonts_to_style(
                doc,
                style_op.style_name,
                style_op.font_name_chinese,
                style_op.font_name_latin,
            )


def apply_mixed_fonts_to_style(
    doc: Any,
    style_name: str,
    chinese_font: str | None,
    latin_font: str | None,
) -> None:
    """Apply CJK- or Latin-specific fonts to all runs of a given style.

    Iterates over every paragraph that uses ``style_name`` and examines each
    run.  Runs containing any CJK character receive ``chinese_font``; all
    other non-whitespace runs receive ``latin_font``.

    Args:
        doc: The ``python-docx`` ``Document`` to modify in place.
        style_name: Name of the style whose paragraphs should be updated.
        chinese_font: Font name for CJK runs, or ``None`` to skip.
        latin_font: Font name for Latin runs, or ``None`` to skip.
    """
    for paragraph in doc.paragraphs:
        if paragraph.style.name != style_name:
            continue

        for run in paragraph.runs:
            text = run.text
            if not text or text.strip() == "":
                continue

            if _has_cjk(text):
                if chinese_font is not None:
                    run.font.name = chinese_font
            else:
                if latin_font is not None:
                    run.font.name = latin_font


def _parse_font_style(font_style: str) -> tuple[bool, bool]:
    """Map a font style string to (bold, italic) booleans."""
    mapping = {
        "bold": (True, False),
        "italic": (False, True),
        "bold_italic": (True, True),
        "normal": (False, False),
    }
    return mapping.get(font_style, (False, False))


def apply_renumbering(
    doc: Any,
    mapping: DocxTypstMapping,
    renumber_ops: list[RenumberOp],
    locator: dict[str, int],
) -> None:
    """Apply renumbering operations to a DOCX document.

    For each ``RenumberOp``:
      - Traverses the IR tree via ``mapping.path_index``
      - Computes hierarchical numbering for headings, figures, and tables
      - Updates the corresponding DOCX paragraph text via ``locator``

    Headings:
      - Section headings get ``section_number`` as dot-separated indices
      - Standalone headings get ``{section_path}-{counter}`` (or plain
        ``{counter}`` when no ancestor sections exist)

    Figures and tables:
      - Numbered independently within each section scope
      - Format: ``Figure {section_path}-{counter}: {caption}`` or
        ``Figure {counter}: {caption}`` when there are no sections

    Args:
        doc: The ``python-docx`` ``Document`` to modify in place.
        mapping: DOCX-to-Typst IR mapping with ``path_index`` and entries.
        renumber_ops: List of renumber operations to apply.
        locator: Dictionary mapping NodeID canonical strings to paragraph
            indices in the extracted all-paragraphs list.
    """
    if not renumber_ops:
        return

    types_to_renumber = {op.element_type for op in renumber_ops}
    all_paras = _get_all_paragraphs(doc)

    nodes: list[dict[str, Any]] = []
    for path, canonical_id in mapping.path_index.items():
        info = _parse_path_info(path)
        node_type = info["type"]
        if node_type == "other":
            continue
        if not _is_node_type_requested(node_type, types_to_renumber):
            continue

        para_idx = locator.get(canonical_id)
        if para_idx is None:
            continue
        if para_idx >= len(all_paras):
            logger.warning(
                "Paragraph index %d exceeds document paragraph count %d for node %s",
                para_idx,
                len(all_paras),
                canonical_id,
            )
            continue

        nodes.append(
            {
                "type": node_type,
                "para_idx": para_idx,
                "scope": info.get("scope", ()),
                "section_number": info.get("section_number"),
                "path": path,
            }
        )

    nodes.sort(key=lambda n: n["para_idx"])

    heading_counters: dict[tuple[int, ...], int] = defaultdict(int)
    figure_counters: dict[tuple[int, ...], int] = defaultdict(int)
    table_counters: dict[tuple[int, ...], int] = defaultdict(int)

    for node in nodes:
        para = all_paras[node["para_idx"]]
        original_text = para.text

        node_type = node["type"]
        if node_type == "section_heading":
            number = node["section_number"]
            para.text = f"{number} {original_text}"
        elif node_type == "standalone_heading":
            heading_counters[node["scope"]] += 1
            counter = heading_counters[node["scope"]]
            number = _format_scope_number(node["scope"], counter)
            para.text = f"{number} {original_text}"
        elif node_type == "figure":
            figure_counters[node["scope"]] += 1
            counter = figure_counters[node["scope"]]
            number = _format_scope_number(node["scope"], counter)
            para.text = f"Figure {number}: {original_text}"
        elif node_type == "table":
            table_counters[node["scope"]] += 1
            counter = table_counters[node["scope"]]
            number = _format_scope_number(node["scope"], counter)
            para.text = f"Table {number}: {original_text}"


def _get_all_paragraphs(doc: Any) -> list[Any]:
    paragraphs: list[Any] = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraphs.append(paragraph)
    return paragraphs


def _parse_path_info(path: str) -> dict[str, Any]:
    matches = list(_SECTION_RE.finditer(path))
    all_section_indices = [int(m.group(1)) for m in matches]

    if path.endswith(".heading[TypstHeading]"):
        section_number_parts = [s + 1 for s in all_section_indices]
        return {
            "type": "section_heading",
            "section_number": ".".join(str(p) for p in section_number_parts),
            "scope": tuple(all_section_indices[:-1]) if len(all_section_indices) > 1 else tuple(),
        }
    if path.endswith("[TypstHeading]"):
        return {"type": "standalone_heading", "scope": tuple(all_section_indices)}
    if path.endswith("[TypstFigure]"):
        return {"type": "figure", "scope": tuple(all_section_indices)}
    if path.endswith("[TypstTable]"):
        return {"type": "table", "scope": tuple(all_section_indices)}
    return {"type": "other"}


def _is_node_type_requested(node_type: str, types_to_renumber: set[str]) -> bool:
    if node_type in types_to_renumber:
        return True
    if node_type == "section_heading" and "heading" in types_to_renumber:
        return True
    if node_type == "standalone_heading" and "heading" in types_to_renumber:
        return True
    return False


def _format_scope_number(scope: tuple[int, ...], counter: int) -> str:
    if not scope:
        return str(counter)
    section_path = ".".join(str(s + 1) for s in scope)
    return f"{section_path}.{counter}"


def _has_cjk(text: str) -> bool:
    """Return True if *text* contains any CJK character."""
    for char in text:
        code = ord(char)
        if (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0xF900 <= code <= 0xFAFF
            or 0x20000 <= code <= 0x2EBEF
        ):
            return True
    return False
