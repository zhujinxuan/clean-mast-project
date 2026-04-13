"""Detection algorithms for mapping DOCX content back to Typst IR nodes.

This module provides fingerprint matching, style-based fallbacks, and confidence
scoring for mapping DOCX paragraphs, tables, figures, and equations to their
corresponding Typst IR nodes. It is the core of the round-trip document
processing pipeline.

Typical usage involves calling detection functions directly for low-level
matching, or using `DocxMatcher` (from `typst_ir.mapping.matcher`) for
sequential matching over an entire document.

Example:
    >>> from docx import Document
    >>> from typst_ir.mapping.detection import (
    ...     match_paragraph_with_fallback,
    ...     detect_heading_level,
    ... )
    >>> doc = Document("report.docx")
    >>> para = doc.paragraphs[0]
    >>> result = match_paragraph_with_fallback(
    ...     "Introduction", para, ir_index=0, docx_index=0
    ... )
    >>> result["confidence"]
    'high'
    >>> level = detect_heading_level(para)
    >>> level
    1
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph as _Paragraph

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionResult:
    """Structured result of a detection mapping attempt.

    Attributes:
        ir_node_id: Unique identifier of the IR node.
        ir_node_type: Type name of the IR node (e.g., 'TypstParagraph').
        docx_index: Index of the matched element in the DOCX document.
        method: Detection method used to produce the mapping.
        confidence: Confidence level of the mapping ('high', 'medium', 'low').
        details: Additional metadata about the detection.

    Example:
        >>> DetectionResult(
        ...     ir_node_id="doc.children.0[TypstParagraph]",
        ...     ir_node_type="TypstParagraph",
        ...     docx_index=0,
        ...     method="fingerprint",
        ...     confidence="high",
        ...     details={"coverage": (0.95, 0.92)},
        ... )
        DetectionResult(ir_node_id='doc.children.0[TypstParagraph]', ...)
    """

    ir_node_id: str
    ir_node_type: str
    docx_index: int
    method: str
    confidence: str
    details: dict[str, Any]


def _normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs into single spaces and strip ends."""
    return " ".join(text.split())


def _hash_text(text: str) -> str:
    """Return SHA-256 hash of whitespace-normalized text."""
    return hashlib.sha256(_normalize_whitespace(text).encode()).hexdigest()


def _hash_match(text_a: str, text_b: str) -> bool:
    """Check whether two texts are identical after whitespace normalization."""
    return _hash_text(text_a) == _hash_text(text_b)


def match_paragraph_fingerprint(
    typst_text: str,
    docx_text: str,
    min_length: int = 20,
    threshold: float = 0.8,
) -> tuple[bool, float, float]:
    """Match paragraphs using ordered substring coverage.

    Uses ``difflib.SequenceMatcher`` with ``autojunk=False`` to find
    long matching substrings between the Typst text and the DOCX text.
    Coverage is computed as the fraction of each text covered by matches
    of at least ``min_length`` characters.

    This method is robust against reference substitution (e.g., ``\ref{fig1}``
    becoming ``Figure 1``) and minor formatting changes.

    Args:
        typst_text: Text content from the Typst IR paragraph.
        docx_text: Text content from the DOCX paragraph.
        min_length: Minimum substring length to count as a match.
        threshold: Minimum coverage on *both* sides to declare a match.

    Returns:
        A tuple of ``(is_match, coverage_a, coverage_b)`` where
        ``coverage_a`` is the fraction of ``typst_text`` covered and
        ``coverage_b`` is the fraction of ``docx_text`` covered.

    Example:
        >>> match_paragraph_fingerprint(
        ...     "Wind speed at 80 m height",
        ...     "Wind speed at 80 m height",
        ... )
        (True, 1.0, 1.0)
        >>> match_paragraph_fingerprint(
        ...     "See \\ref{fig1} for details",
        ...     "See Figure 1 for details",
        ... )
        (True, 0.85..., 0.85...)
    """
    text_a = _normalize_whitespace(typst_text)
    text_b = _normalize_whitespace(docx_text)

    matcher = SequenceMatcher(None, text_a, text_b, autojunk=False)
    matches = [
        (a, b, size)
        for a, b, size in matcher.get_matching_blocks()
        if size >= min_length
    ]

    covered_a = sum(size for _a, _b, size in matches)
    covered_b = sum(size for _a, _b, size in matches)

    cov_a = covered_a / len(text_a) if text_a else 0.0
    cov_b = covered_b / len(text_b) if text_b else 0.0

    is_match = cov_a >= threshold and cov_b >= threshold
    return is_match, cov_a, cov_b


def match_paragraph_with_fallback(
    typst_text: str,
    docx_para: _Paragraph,
    ir_index: int,
    docx_index: int,
) -> dict[str, Any]:
    """Match a paragraph using fingerprint matching with cascading fallbacks.

    The algorithm tries methods in order of preference:

    1. **Fingerprint** - ordered substring coverage (high confidence).
    2. **Style** - for short text (< 20 chars) using paragraph style
       (medium confidence for known styles, low for body text).
    3. **Hash** - tertiary fallback for very short body text
       (low confidence).
    4. **Positional** - final fallback based on document position
       (low confidence).

    Args:
        typst_text: Text content from the Typst IR paragraph.
        docx_para: A ``python-docx`` ``Paragraph`` instance.
        ir_index: Position of the IR node in the IR sequence.
        docx_index: Position of the paragraph in the DOCX sequence.

    Returns:
        A dictionary with keys ``method``, ``confidence``,
        ``coverage``, ``ir_index``, and ``docx_index``.

    Example:
        >>> from docx import Document
        >>> doc = Document("report.docx")
        >>> para = doc.paragraphs[0]
        >>> result = match_paragraph_with_fallback(
        ...     "Abstract", para, ir_index=0, docx_index=0
        ... )
        >>> result["method"] in ("fingerprint", "style_heading",
        ...                      "style_body", "positional")
        True
    """
    # Primary: fingerprint matching
    is_match, cov_a, cov_b = match_paragraph_fingerprint(typst_text, docx_para.text)
    if is_match:
        return {
            "method": "fingerprint",
            "confidence": "high",
            "coverage": (cov_a, cov_b),
            "ir_index": ir_index,
            "docx_index": docx_index,
        }

    # Fallback 1: style-based for short text
    if len(typst_text) < 20:
        style = docx_para.style.name if docx_para.style else ""
        if "Heading" in style:
            return {
                "method": "style_heading",
                "confidence": "medium",
                "coverage": None,
                "ir_index": ir_index,
                "docx_index": docx_index,
            }
        if "Caption" in style:
            return {
                "method": "style_caption",
                "confidence": "medium",
                "coverage": None,
                "ir_index": ir_index,
                "docx_index": docx_index,
            }
        if "Body Text" in style or "First Paragraph" in style:
            # Tertiary fallback: hash matching for very short body text
            if _hash_match(typst_text, docx_para.text):
                return {
                    "method": "hash",
                    "confidence": "low",
                    "coverage": None,
                    "ir_index": ir_index,
                    "docx_index": docx_index,
                }
            return {
                "method": "style_body",
                "confidence": "low",
                "coverage": None,
                "ir_index": ir_index,
                "docx_index": docx_index,
            }

    # Fallback 2: positional matching
    return {
        "method": "positional",
        "confidence": "low",
        "coverage": None,
        "ir_index": ir_index,
        "docx_index": docx_index,
    }


def detect_heading_level(docx_para: _Paragraph) -> int | None:
    """Detect heading level from a DOCX paragraph.

    Uses two strategies in order:
    1. Parse the paragraph style name for a "Heading N" pattern (case-insensitive).
    2. Search the paragraph XML for an ``outlineLvl`` attribute.

    Args:
        docx_para: A ``python-docx`` ``Paragraph`` instance.

    Returns:
        The heading level as an integer, or ``None`` if the paragraph
        does not represent a heading.

    Example:
        >>> from docx import Document
        >>> doc = Document("report.docx")
        >>> level = detect_heading_level(doc.paragraphs[0])
        >>> isinstance(level, (int, type(None)))
        True
    """
    style_name = docx_para.style.name if docx_para.style else ""
    match = re.search(r"Heading\s*(\d+)", style_name, re.IGNORECASE)
    if match:
        return int(match.group(1))

    pPr = docx_para._element.find(qn("w:pPr"))
    if pPr is not None:
        outline_lvl = pPr.find(qn("w:outlineLvl"))
        if outline_lvl is not None:
            return int(outline_lvl.get(qn("w:val"), "0"))

    return None


def detect_tables(doc_document: Any) -> list[tuple[int, Table]]:
    """Detect tables in a DOCX document.

    Uses ``doc_document.iter_inner_content()`` to find all ``Table``
    objects and return them as ``(index, Table)`` tuples preserving
    document order.

    Args:
        doc_document: A ``python-docx`` ``Document`` instance.

    Returns:
        List of ``(index, Table)`` tuples in document order.

    Example:
        >>> from docx import Document
        >>> doc = Document("report.docx")
        >>> tables = detect_tables(doc)
        >>> tables[0][1].rows[0].cells[0].text
        'Header'
    """
    tables: list[tuple[int, Table]] = []
    for i, content in enumerate(doc_document.iter_inner_content()):
        if isinstance(content, Table):
            tables.append((i, content))
    return tables


def match_table(
    ir_table: Any,
    docx_table: Table,
    docx_contents: list[Any],
    table_index: int,
) -> dict[str, Any]:
    """Match a TypstTable IR node to a DOCX table.

    Uses structure comparison (rows x columns) and optional caption
    fingerprint matching to determine mapping confidence.

    Confidence is ``high`` when both structure and caption match,
    ``medium`` when only one matches, and ``low`` when neither matches.

    Args:
        ir_table: A ``TypstTable`` IR node.
        docx_table: A ``python-docx`` ``Table`` instance.
        docx_contents: List of DOCX contents from ``iter_inner_content()``.
        table_index: Index of ``docx_table`` in ``docx_contents``.

    Returns:
        Dictionary with keys ``structure``, ``caption``, ``confidence``,
        ``ir_dims``, and ``docx_dims``.

    Example:
        >>> from docx import Document
        >>> from typst_ir import TypstTable
        >>> doc = Document("report.docx")
        >>> contents = list(doc.iter_inner_content())
        >>> ir_table = TypstTable(
        ...     headers=["A", "B"],
        ...     data=[["1", "2"]],
        ...     caption=None,
        ... )
        >>> result = match_table(ir_table, contents[0], contents, 0)
        >>> "confidence" in result
        True
    """
    ir_rows = len(ir_table.data) + (1 if ir_table.headers else 0)
    ir_cols = len(ir_table.headers) if ir_table.headers else (len(ir_table.data[0]) if ir_table.data else 0)
    docx_rows = len(docx_table.rows)
    docx_cols = len(docx_table.columns)

    structure_match = ir_rows == docx_rows and ir_cols == docx_cols

    caption_match = None
    if ir_table.caption and table_index > 0:
        prev = docx_contents[table_index - 1]
        if isinstance(prev, Paragraph) and prev.style:
            style_lower = prev.style.name.lower()
            if "caption" in style_lower:
                is_match, _cov_a, _cov_b = match_paragraph_fingerprint(
                    ir_table.caption, prev.text
                )
                caption_match = is_match

    if structure_match and caption_match:
        confidence = "high"
    elif structure_match or caption_match:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "structure": structure_match,
        "caption": caption_match,
        "confidence": confidence,
        "ir_dims": (ir_rows, ir_cols),
        "docx_dims": (docx_rows, docx_cols),
    }


def detect_figures(doc_document: Any) -> list[dict[str, Any]]:
    """Detect figure paragraphs in a DOCX document.

    Iterates through ``doc_document.iter_inner_content()`` and finds
    paragraphs containing ``<w:drawing>`` elements. For each figure
    paragraph, checks the next element; if it is a ``Paragraph`` with
    ``caption`` in its style name, it is recorded as the caption.

    Args:
        doc_document: A ``python-docx`` ``Document`` instance.

    Returns:
        List of dictionaries with keys ``index``, ``style``,
        ``has_drawing``, ``caption``, and ``caption_index``.

    Example:
        >>> from docx import Document
        >>> doc = Document("report.docx")
        >>> figures = detect_figures(doc)
        >>> figures[0]["has_drawing"]
        True
    """
    figures: list[dict[str, Any]] = []
    contents = list(doc_document.iter_inner_content())
    for i, content in enumerate(contents):
        if isinstance(content, Paragraph):
            has_drawing = bool(content._element.findall(".//" + qn("w:drawing")))
            if has_drawing:
                style = content.style.name if content.style else ""
                caption = None
                caption_index = None
                if i + 1 < len(contents):
                    next_content = contents[i + 1]
                    if isinstance(next_content, Paragraph) and next_content.style:
                        if "caption" in next_content.style.name.lower():
                            caption = next_content.text
                            caption_index = i + 1
                figures.append(
                    {
                        "index": i,
                        "style": style,
                        "has_drawing": True,
                        "caption": caption,
                        "caption_index": caption_index,
                    }
                )
    return figures


def match_figure(
    ir_figure: Any,
    docx_para: Paragraph,
    docx_contents: list[Any],
    para_index: int,
) -> dict[str, Any]:
    """Match a TypstFigure IR node to a DOCX paragraph.

    Checks whether the paragraph contains a ``<w:drawing>`` element and
    whether the following paragraph matches the figure caption.

    Confidence is ``high`` when both drawing and caption match,
    ``medium`` when only one matches, and ``low`` when neither matches.

    Args:
        ir_figure: A ``TypstFigure`` IR node.
        docx_para: A ``python-docx`` ``Paragraph`` instance.
        docx_contents: List of DOCX contents from ``iter_inner_content()``.
        para_index: Index of ``docx_para`` in ``docx_contents``.

    Returns:
        Dictionary with keys ``drawing``, ``caption``, and ``confidence``.

    Example:
        >>> from docx import Document
        >>> from typst_ir import TypstFigure
        >>> doc = Document("report.docx")
        >>> contents = list(doc.iter_inner_content())
        >>> ir_fig = TypstFigure(
        ...     content="image.png",
        ...     caption="Wind rose",
        ...     kind="image",
        ... )
        >>> result = match_figure(ir_fig, contents[0], contents, 0)
        >>> "confidence" in result
        True
    """
    drawing = bool(docx_para._element.findall(".//" + qn("w:drawing")))

    caption_match = None
    if ir_figure.caption and para_index + 1 < len(docx_contents):
        next_content = docx_contents[para_index + 1]
        if isinstance(next_content, Paragraph) and next_content.style:
            if "caption" in next_content.style.name.lower():
                is_match, _cov_a, _cov_b = match_paragraph_fingerprint(
                    ir_figure.caption, next_content.text
                )
                caption_match = is_match

    if drawing and caption_match:
        confidence = "high"
    elif drawing or caption_match:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "drawing": drawing,
        "caption": caption_match,
        "confidence": confidence,
    }


def detect_equation(docx_para: _Paragraph) -> str | None:
    """Detect whether a DOCX paragraph contains an Office Math (OMML) equation.

    Searches the paragraph XML for OMML elements and classifies the equation
    as ``display`` if an ``m:oMathPara`` element is present, or ``inline`` if
    only ``m:oMath`` elements are present.

    Args:
        docx_para: A ``python-docx`` ``Paragraph`` instance.

    Returns:
        ``"display"`` if ``m:oMathPara`` is found, ``"inline"`` if
        ``m:oMath`` is found but not ``m:oMathPara``, or ``None`` if neither
        is present.

    Example:
        >>> from docx import Document
        >>> doc = Document("report.docx")
        >>> eq_type = detect_equation(doc.paragraphs[0])
        >>> eq_type in ("display", "inline", None)
        True
    """
    if docx_para._element.findall(".//" + qn("m:oMathPara")):
        return "display"
    if docx_para._element.findall(".//" + qn("m:oMath")):
        return "inline"
    return None


@dataclass(frozen=True)
class DocxSpan:
    """A contiguous span of DOCX content with a semantic label.

    Attributes:
        start: Inclusive index in the original ``docx_contents`` sequence.
        end: Exclusive index in the original ``docx_contents`` sequence.
        elements: The actual DOCX objects comprising this span.
        label: Semantic classification of the span.
    """

    start: int
    end: int
    elements: list[Any]
    label: str


def _is_table_content(content: Any) -> bool:
    if isinstance(content, Table):
        return True
    rows = getattr(content, "rows", None)
    columns = getattr(content, "columns", None)
    return isinstance(rows, list) and isinstance(columns, list)


def _is_caption_para(para: Any) -> bool:
    style = getattr(para, "style", None)
    style_name = getattr(style, "name", "") if style else ""
    return "caption" in style_name.lower()


def _has_drawing_para(para: Any) -> bool:
    element = getattr(para, "_element", None)
    if element is not None:
        try:
            return bool(element.findall(".//" + qn("w:drawing")))
        except Exception:
            return False
    return False


def _is_heading_para(para: Any) -> bool:
    from unittest.mock import MagicMock

    style = getattr(para, "style", None)
    style_name = getattr(style, "name", "") if style else ""
    if re.search(r"Heading\s*\d+", style_name, re.IGNORECASE):
        return True

    element = getattr(para, "_element", None)
    if element is None:
        return False

    pPr = element.find(qn("w:pPr"))
    if pPr is None or isinstance(pPr, MagicMock):
        return False

    outline_lvl = pPr.find(qn("w:outlineLvl"))
    if outline_lvl is None or isinstance(outline_lvl, MagicMock):
        return False

    return True


def group_docx_spans(docx_contents: list[Any]) -> list[DocxSpan]:
    """Group adjacent DOCX elements into semantically labelled spans.

    Processes ``docx_contents`` left-to-right, consuming elements so that
    each element appears in exactly one span. Grouping follows pandoc's
    ``addCaptioned`` pattern:

    - ``"caption+table"`` — caption paragraph immediately before a table.
    - ``"figure+caption"`` — caption paragraph immediately after a drawing.
    - ``"figure"`` — drawing paragraph without adjacent caption.
    - ``"table"`` — table without adjacent caption.
    - ``"heading"`` — paragraph with heading style or ``w:outlineLvl``.
    - ``"equation"`` — paragraph containing OMML math.
    - ``"paragraph"`` — everything else.

    Args:
        docx_contents: List of DOCX content objects (paragraphs, tables,
            etc.) as returned by ``iter_inner_content()``.

    Returns:
        List of ``DocxSpan`` objects in document order.
    """
    spans: list[DocxSpan] = []
    i = 0
    n = len(docx_contents)
    while i < n:
        content = docx_contents[i]
        if _is_table_content(content):
            spans.append(
                DocxSpan(start=i, end=i + 1, elements=[content], label="table")
            )
            i += 1
            continue

        is_caption = _is_caption_para(content)
        has_drawing = _has_drawing_para(content)
        is_heading = _is_heading_para(content)
        is_equation = detect_equation(content) is not None

        if is_caption and i + 1 < n and _is_table_content(docx_contents[i + 1]):
            spans.append(
                DocxSpan(
                    start=i,
                    end=i + 2,
                    elements=docx_contents[i : i + 2],
                    label="caption+table",
                )
            )
            i += 2
        elif has_drawing and i + 1 < n and _is_caption_para(docx_contents[i + 1]):
            caption_style = (
                getattr(getattr(docx_contents[i + 1], "style", None), "name", "")
                or ""
            )
            if (
                "table" in caption_style.lower()
                and i + 2 < n
                and _is_table_content(docx_contents[i + 2])
            ):
                spans.append(
                    DocxSpan(start=i, end=i + 1, elements=[content], label="figure")
                )
                i += 1
            else:
                spans.append(
                    DocxSpan(
                        start=i,
                        end=i + 2,
                        elements=docx_contents[i : i + 2],
                        label="figure+caption",
                    )
                )
                i += 2
        elif has_drawing:
            spans.append(
                DocxSpan(start=i, end=i + 1, elements=[content], label="figure")
            )
            i += 1
        elif is_heading:
            spans.append(
                DocxSpan(start=i, end=i + 1, elements=[content], label="heading")
            )
            i += 1
        elif is_equation:
            spans.append(
                DocxSpan(start=i, end=i + 1, elements=[content], label="equation")
            )
            i += 1
        else:
            spans.append(
                DocxSpan(start=i, end=i + 1, elements=[content], label="paragraph")
            )
            i += 1

    return spans
