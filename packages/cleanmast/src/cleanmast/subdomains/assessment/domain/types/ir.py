"""Domain-level Typst IR types - re-exported from typst_ir package.

These types are imported from typst_ir to ensure compatibility across packages.
All nodes are frozen Pydantic BaseModels for safety, hashability, and validation.
"""

from typst_ir import (
    TypstChild,
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)

__all__ = [
    "TypstDocument",
    "TypstHeading",
    "TypstParagraph",
    "TypstTable",
    "TypstFigure",
    "TypstChild",
    "TypstSection",
]
