"""Extract inner content from DOCX documents."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx.document import Document as _Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph


def extract_inner_content(
    doc_document: _Document,
) -> list[tuple[int, Paragraph | Table]]:
    """Extract top-level paragraph and table elements from a DOCX document.

    Iterates over the document's inner content using
    ``doc_document.iter_inner_content()`` and returns each top-level
    ``Paragraph`` or ``Table`` together with its positional index,
    preserving the original document order.

    Args:
        doc_document: A ``python-docx`` ``Document`` instance.

    Returns:
        A list of ``(index, element)`` tuples where ``element`` is either
        a ``Paragraph`` or a ``Table``.
    """
    result: list[tuple[int, Paragraph | Table]] = []
    for idx, element in enumerate(doc_document.iter_inner_content()):
        result.append((idx, element))
    return result
