"""Style collector for extracting style information from DOCX files.

Provides utilities to read font properties, colors, and paragraph spacing
from paragraph and character styles in a DOCX document.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class StyleInfo(BaseModel):
    """Extracted style information from a DOCX style.

    Attributes:
        font_name: Name of the font family.
        font_size: Font size in points.
        font_style: Font style - "bold", "italic", "bold_italic", "normal", or None.
        font_color: Hex color string (e.g., "#FF0000").
        line_spacing_before: Space before paragraph in points.
        line_spacing_after: Space after paragraph in points.
    """

    model_config = ConfigDict(frozen=True)

    font_name: str | None = None
    font_size: float | None = None
    font_style: str | None = None
    font_color: str | None = None
    line_spacing_before: float | None = None
    line_spacing_after: float | None = None


def _derive_font_style(bold: bool | None, italic: bool | None) -> str | None:
    """Derive font_style string from bold and italic flags."""
    if bold is None and italic is None:
        return None
    if bold is True and italic is True:
        return "bold_italic"
    if bold is True:
        return "bold"
    if italic is True:
        return "italic"
    return "normal"


def _extract_style_info(style: Any) -> StyleInfo:
    """Extract StyleInfo from a python-docx style object."""
    font = style.font

    font_name = font.name

    font_size = None
    if font.size is not None:
        font_size = font.size.pt

    font_style = _derive_font_style(font.bold, font.italic)

    font_color = None
    if font.color is not None and font.color.rgb is not None:
        font_color = str(font.color.rgb)

    line_spacing_before = None
    line_spacing_after = None
    try:
        paragraph_format = style.paragraph_format
    except AttributeError:
        paragraph_format = None

    if paragraph_format is not None:
        if paragraph_format.space_before is not None:
            line_spacing_before = paragraph_format.space_before.pt
        if paragraph_format.space_after is not None:
            line_spacing_after = paragraph_format.space_after.pt

    return StyleInfo(
        font_name=font_name,
        font_size=font_size,
        font_style=font_style,
        font_color=font_color,
        line_spacing_before=line_spacing_before,
        line_spacing_after=line_spacing_after,
    )


def collect_styles(docx_path: Path) -> dict[str, StyleInfo]:
    """Extract style information from all styles in a DOCX file.

    Args:
        docx_path: Path to the ``.docx`` file.

    Returns:
        Dictionary mapping style name to ``StyleInfo``.
    """
    from docx import Document

    document = Document(str(docx_path))
    result: dict[str, StyleInfo] = {}

    for style in document.styles:
        if not hasattr(style, "font"):
            continue
        result[style.name] = _extract_style_info(style)

    return result


def collect_styles_for_names(
    docx_path: Path, style_names: list[str]
) -> dict[str, StyleInfo]:
    """Extract style information for specific named styles from a DOCX file.

    Args:
        docx_path: Path to the ``.docx`` file.
        style_names: List of style names to collect.

    Returns:
        Dictionary mapping requested style name to ``StyleInfo``.
        Missing styles are omitted and a warning is logged.
    """
    all_styles = collect_styles(docx_path)
    result: dict[str, StyleInfo] = {}

    for name in style_names:
        if name in all_styles:
            result[name] = all_styles[name]
        else:
            logger.warning("Style %r not found in %s", name, docx_path)

    return result
