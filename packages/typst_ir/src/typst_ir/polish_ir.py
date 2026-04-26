"""Polish IR types - frozen Pydantic models for style operations.

Defines style-manipulation operations used by the document polishing layer.
All models are frozen for immutability and hashability.
"""

from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict


class ChangeStyle(BaseModel):
    """Apply an existing style to specific paragraphs and/or table cells.

    Attributes:
        path: IR path to the target block (e.g. ``section0body2table0``)
        target_style: Name of the style to apply
        paragraph_indices: Indices into doc.paragraphs to style
        cell_table_indices: List of (table_idx, row_idx, cell_idx) tuples for table cells
    """

    model_config = ConfigDict(frozen=True)

    path: str
    target_style: str
    paragraph_indices: tuple[int, ...] = ()
    cell_table_indices: tuple[tuple[int, int, int], ...] = ()


class CreateStyle(BaseModel):
    """Define a new named style, optionally based on an existing one.

    Attributes:
        style_name: Unique name for the new style
        base_style: Existing style to inherit from, or ``None``
        properties: Arbitrary style properties (will be refined later)
    """

    model_config = ConfigDict(frozen=True)

    style_name: str
    base_style: str | None
    properties: dict


class EditStyle(BaseModel):
    """Modify properties of an existing named style.

    Attributes:
        style_name: Name of the style to edit
        properties: Updated properties to merge into the style
    """

    model_config = ConfigDict(frozen=True)

    style_name: str
    properties: dict


class TableBorderEdge(BaseModel):
    """A single border edge specification."""

    model_config = ConfigDict(frozen=True)

    val: str = "single"
    sz: int = 4
    color: str = "000000"
    space: int = 0


class TableFormat(BaseModel):
    """Table-level formatting: borders + alignment."""

    model_config = ConfigDict(frozen=True)

    alignment: str | None = "center"
    borders: TableBorderEdge | None = TableBorderEdge()


class ApplyTableFormat(BaseModel):
    """Apply table-level formatting (borders, alignment) to specific tables."""

    model_config = ConfigDict(frozen=True)

    path: str
    table_indices: tuple[int, ...]
    format: TableFormat


PolishIR: TypeAlias = ChangeStyle | CreateStyle | EditStyle | ApplyTableFormat
