"""Polish IR types for docx style and numbering operations.

Defines frozen Pydantic models representing style polish instructions
and renumbering operations for DOCX documents.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StyleOp(BaseModel):
    """Style operation for applying formatting to a named style.

    Represents a single style modification instruction, such as changing
    font properties, colors, or paragraph spacing for a DOCX style.

    Attributes:
        style_name: Name of the target style (e.g., "Heading 1")
        font_name: Global font name override
        font_name_chinese: Chinese-specific font name
        font_name_latin: Latin-specific font name
        font_size: Font size in points
        font_style: Font style - "bold", "italic", "normal", or None
        font_color: Hex color string (e.g., "#FF0000")
        line_spacing_before: Space before paragraph in points
        line_spacing_after: Space after paragraph in points
        line_spacing: Line spacing multiplier (e.g., 1.15)
    """

    model_config = ConfigDict(frozen=True)

    style_name: str
    font_name: str | None = None
    font_name_chinese: str | None = None
    font_name_latin: str | None = None
    font_size: float | None = None
    font_style: str | None = None
    font_color: str | None = None
    line_spacing_before: float | None = None
    line_spacing_after: float | None = None
    line_spacing: float | None = None


class RenumberOp(BaseModel):
    """Renumber operation for resetting element numbering.

    Represents an instruction to renumber a specific element type
    in the document, such as headings, figures, or tables.

    Attributes:
        element_type: Type of element to renumber ("heading", "figure", "table")
    """

    model_config = ConfigDict(frozen=True)

    element_type: str


class PolishIR(BaseModel):
    """Root container for polish intermediate representation.

    Holds all style operations and renumbering operations that define
    how a DOCX document should be polished.

    Attributes:
        version: Schema version for migration support (default: "1.0.0")
        styles: List of style operations to apply
        renumber: List of renumber operations to apply
    """

    model_config = ConfigDict(frozen=True)

    version: str = "1.0.0"
    styles: list[StyleOp] = []
    renumber: list[RenumberOp] = []
