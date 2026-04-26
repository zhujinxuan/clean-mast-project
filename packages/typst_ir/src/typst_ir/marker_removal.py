"""IR marker removal from DOCX documents.

Provides paragraph-level removal of IR boundary markers after all polish
operations have been applied.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from typst_ir.marker_detection import is_marker_paragraph

if TYPE_CHECKING:
    from docx.document import Document


def remove_markers(doc: Document) -> int:
    """Remove all IR marker paragraphs from a DOCX document.

    Collects all paragraphs first to avoid iterator invalidation during
    removal, then deletes each marker paragraph at the XML level.

    Args:
        doc: A python-docx Document object.

    Returns:
        The number of marker paragraphs removed.
    """
    paragraphs = list(doc.paragraphs)
    removed = 0
    for p in paragraphs:
        if is_marker_paragraph(p):
            p._element.getparent().remove(p._element)
            removed += 1
    return removed
