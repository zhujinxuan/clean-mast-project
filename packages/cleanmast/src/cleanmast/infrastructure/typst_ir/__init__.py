"""Typst IR (Intermediate Representation) for document generation.

Provides type-safe, immutable nodes for constructing Typst documents.
All nodes are frozen dataclasses that can be serialized to valid Typst markup.

Example:
    >>> from cleanmast.infrastructure.typst_ir import (
    ...     TypstDocument, TypstHeading, TypstParagraph, TypstTable, serialize
    ... )
    >>> doc = TypstDocument(children=[
    ...     TypstHeading(text="Report", level=1),
    ...     TypstParagraph(text="Summary here."),
    ...     TypstTable(
    ...         data=[["a", "b"]],
    ...         headers=["Col1", "Col2"],
    ...         caption="Table 1",
    ...     ),
    ... ])
    >>> typst_code = serialize(doc)
"""

from cleanmast.infrastructure.typst_ir.nodes import (
    TypstChild,
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)
from cleanmast.infrastructure.typst_ir.serializer import serialize

__all__ = [
    "TypstTable",
    "TypstFigure",
    "TypstHeading",
    "TypstParagraph",
    "TypstDocument",
    "TypstChild",
    "serialize",
]
