"""Typst IR node definitions - frozen dataclasses for document elements.

Defines 5 core IR nodes for representing Typst documents:
- TypstTable: Tabular data with headers and optional caption
- TypstFigure: Images/diagrams with captions
- TypstHeading: Section headings with level normalization
- TypstParagraph: Text paragraphs
- TypstDocument: Container for all other nodes

All nodes are frozen (immutable) dataclasses for safety and hashability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class TypstTable:
    """Table node for tabular data.

    Represents a Typst table with headers, data rows, and optional caption.
    When serialized with a caption, wraps the table in a #figure().

    Attributes:
        data: 2D list of strings representing table cells
        headers: List of column header strings
        caption: Optional table caption (wraps in figure if present)
    """

    data: list[list[str]]
    headers: list[str]
    caption: str | None = None


@dataclass(frozen=True)
class TypstFigure:
    """Figure node for images and diagrams.

    Represents a Typst figure with an image reference and caption.

    Attributes:
        content: Path to image file (relative to document)
        caption: Figure caption text
        kind: Figure kind/type (default: "image")
    """

    content: str
    caption: str
    kind: str = "image"


@dataclass(frozen=True)
class TypstHeading:
    """Heading node for section titles.

    Represents a Typst heading with text and level.
    Levels 1-3 produce =, ==, === respectively.
    Levels outside 1-3 are normalized to valid range.

    Attributes:
        text: Heading text content
        level: Heading level (1-3, normalized)
    """

    text: str
    level: int = 1


@dataclass(frozen=True)
class TypstParagraph:
    """Paragraph node for text content.

    Represents a plain text paragraph in the document.

    Attributes:
        text: Paragraph text content
    """

    text: str


# Type alias for all valid document child types
TypstChild = Union[TypstTable, TypstFigure, TypstHeading, TypstParagraph]


@dataclass(frozen=True)
class TypstDocument:
    """Document node - root container for all content.

    Represents a complete Typst document containing a sequence
    of child nodes (tables, figures, headings, paragraphs).

    Attributes:
        children: Ordered list of child nodes
    """

    children: list[TypstChild]
