"""IR marker detection in DOCX documents.

Provides regex-based detection of IR boundary markers embedded in DOCX
paragraphs with the VerbatimChar run style.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph

MARKER_PATTERN = re.compile(r"^(irstart|irend):(.+)$")


def parse_marker(text: str) -> tuple[str, str] | None:
    """Parse a marker string into (kind, block_id) or None.

    Args:
        text: The raw text to parse.

    Returns:
        A tuple of (marker_kind, block_id) if the text matches the marker
        pattern, otherwise None.

    Examples:
        >>> parse_marker("irstart:section0body0")
        ('irstart', 'section0body0')
        >>> parse_marker("irend:section0body2table0")
        ('irend', 'section0body2table0')
        >>> parse_marker("not a marker")
        None
    """
    match = MARKER_PATTERN.match(text)
    if match is None:
        return None
    return match.group(1), match.group(2)


def is_marker_paragraph(paragraph: Paragraph) -> bool:
    """Check whether a DOCX paragraph is an IR marker paragraph.

    A marker paragraph must have:
    1. Exactly one run.
    2. That run uses the ``VerbatimChar`` style.
    3. The run text matches ``MARKER_PATTERN``.

    Args:
        paragraph: A python-docx Paragraph object.

    Returns:
        True if the paragraph is a marker paragraph, False otherwise.
    """
    if len(paragraph.runs) != 1:
        return False
    run = paragraph.runs[0]
    if run.style is None or run.style.name not in ("VerbatimChar", "Verbatim Char"):
        return False
    return parse_marker(run.text) is not None
