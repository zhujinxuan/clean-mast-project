"""Domain-level Typst IR types - frozen dataclasses for document elements.

Defines core IR nodes for representing Typst documents at the domain layer.
These types are pure data structures with no dependencies on infrastructure.

All nodes are frozen (immutable) dataclasses for safety and hashability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class TypstTable:
    """Table node for tabular data.

    Represents a table with headers, data rows, and optional caption.

    Attributes:
        data: 2D list of strings representing table cells
        headers: List of column header strings
        caption: Optional table caption
    """

    data: list[list[str]]
    headers: list[str]
    caption: str | None = None


@dataclass(frozen=True)
class TypstFigure:
    """Figure node for images and diagrams.

    Represents a figure with content reference and caption.

    Attributes:
        content: Path to image file or figure content
        caption: Figure caption text
        kind: Figure kind/type (default: "image")
    """

    content: str
    caption: str
    kind: str = "image"


@dataclass(frozen=True)
class TypstHeading:
    """Heading node for section titles.

    Represents a heading with text and level.

    Attributes:
        text: Heading text content
        level: Heading level (1=top level, 2=subsection, etc.)
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
