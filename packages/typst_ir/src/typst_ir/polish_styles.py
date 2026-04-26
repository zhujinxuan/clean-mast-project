"""Style definitions for DOCX polish system.

Defines Pydantic models for style properties and a registry of default style
definitions used by the CreateStyle IR operation.

All models use frozen Pydantic BaseModels for safety and hashability.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .polish_ir import TableFormat

TYPST_IR_PARAGRAPH = "typst-ir-Paragraph"
TYPST_IR_TABLE_CONTENT = "typst-ir-TableContent"
TYPST_IR_TABLE_CAPTION = "typst-ir-TableCaption"
TYPST_IR_FIGURE_CAPTION = "typst-ir-FigureCaption"

TYPST_IR_HEADING1 = "typst-ir-Heading1"
TYPST_IR_HEADING2 = "typst-ir-Heading2"
TYPST_IR_HEADING3 = "typst-ir-Heading3"
TYPST_IR_HEADING4 = "typst-ir-Heading4"
TYPST_IR_HEADING5 = "typst-ir-Heading5"

DEFAULT_TABLE_FORMAT: TableFormat = TableFormat()


class LineSpacing(BaseModel):
    """Line spacing specification for paragraph styles.

    Supports absolute point values or relative multipliers.

    Attributes:
        value: Numeric value of the spacing
        unit: Unit type — "pt" for absolute points or "multiplier" for relative
    """

    model_config = ConfigDict(frozen=True)

    value: float
    unit: Literal["pt", "multiplier"]


class StyleProperties(BaseModel):
    """Properties that can be applied to a paragraph or character style.

    All fields are optional — omitting a field means the property is
    inherited from the base style or left at the default.

    Attributes:
        font_name: Western font name (e.g., "Times New Roman")
        font_name_east_asia: East Asian font name (e.g., "宋体").
            Applied at the XML level via ``w:eastAsia``.
        font_size: Font size in points
        bold: Whether text is bold
        alignment: Paragraph alignment ("left", "center", "right", "justify")
        first_line_indent_chars: First-line indent in characters.
            Applied at the XML level via ``w:firstLineChars``.
        space_before: Space before paragraph in points
        space_after: Space after paragraph in points
        line_spacing: Line spacing as points or multiplier (e.g., LineSpacing(value=23, unit="pt"))
        font_color: Font color name (e.g., "black", "red") or hex RGB (e.g., "#000000")
    """

    model_config = ConfigDict(frozen=True)

    font_name: str | None = None
    font_name_east_asia: str | None = None
    font_size: int | None = None
    bold: bool | None = None
    alignment: str | None = None
    first_line_indent_chars: int | None = None
    space_before: int | None = None
    space_after: int | None = None
    line_spacing: LineSpacing | None = None
    font_color: str | None = None


class StyleDef(BaseModel):
    """Definition of a named style for DOCX generation.

    A style definition references a base style (e.g., "Normal") and
    overrides specific properties.

    Attributes:
        base_style: Name of the base style to inherit from, or None
        properties: Style property overrides
    """

    model_config = ConfigDict(frozen=True)

    base_style: str | None = None
    properties: StyleProperties


DEFAULT_STYLE_DEFS: dict[str, StyleDef] = {
    "typst-ir-Paragraph": StyleDef(
        base_style="Normal",
        properties=StyleProperties(
            font_name="Times New Roman",
            font_name_east_asia="宋体",
            font_size=12,
            first_line_indent_chars=2,
            line_spacing=LineSpacing(value=23, unit="pt"),
            space_before=0,
            space_after=0,
        ),
    ),
    "typst-ir-Heading1": StyleDef(
        base_style="Heading 1",
        properties=StyleProperties(
            font_size=12,
            bold=True,
            font_color="black",
        ),
    ),
    "typst-ir-Heading2": StyleDef(
        base_style="Heading 2",
        properties=StyleProperties(
            font_size=12,
            bold=True,
            font_color="black",
        ),
    ),
    "typst-ir-Heading3": StyleDef(
        base_style="Heading 3",
        properties=StyleProperties(
            font_size=12,
            bold=True,
            font_color="black",
        ),
    ),
    "typst-ir-Heading4": StyleDef(
        base_style="Heading 4",
        properties=StyleProperties(
            font_size=12,
            bold=False,
            font_color="black",
        ),
    ),
    "typst-ir-Heading5": StyleDef(
        base_style="Heading 5",
        properties=StyleProperties(
            font_size=12,
            bold=True,
            font_color="black",
        ),
    ),
    "typst-ir-TableCaption": StyleDef(
        base_style="Normal",
        properties=StyleProperties(
            font_name="Times New Roman",
            font_name_east_asia="宋体",
            font_size=12,
            alignment="center",
            space_before=5,
            space_after=0,
        ),
    ),
    "typst-ir-FigureCaption": StyleDef(
        base_style="Normal",
        properties=StyleProperties(
            font_name="Times New Roman",
            font_name_east_asia="宋体",
            font_size=12,
            alignment="center",
            space_before=0,
            space_after=5,
        ),
    ),
    "typst-ir-TableContent": StyleDef(
        base_style="Normal",
        properties=StyleProperties(
            font_name="Times New Roman",
            font_name_east_asia="宋体",
            font_size=9,
            space_before=0,
            space_after=0,
        ),
    ),
}
