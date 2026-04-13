"""Domain-level Typst IR types.

Exports frozen dataclass types for representing Typst documents
at the domain layer with no infrastructure dependencies.
"""

from cleanmast.subdomains.assessment.domain.types.ir import (
    TypstChild,
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.types.section import Section

__all__ = [
    "Section",
    "TypstChild",
    "TypstDocument",
    "TypstFigure",
    "TypstHeading",
    "TypstParagraph",
    "TypstSection",
    "TypstTable",
]
