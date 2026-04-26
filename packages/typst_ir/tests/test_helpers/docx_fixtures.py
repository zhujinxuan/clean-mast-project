"""Helper functions to create synthetic DOCX files with IR markers for testing."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE


def _ensure_style(doc: Document, style_name: str, style_type: WD_STYLE_TYPE) -> object:
    """Return an existing style or create it if missing."""
    try:
        return doc.styles[style_name]
    except KeyError:
        return doc.styles.add_style(style_name, style_type)


def create_docx_with_markers(
    marker_pairs: list[tuple[str, str, int]], output_path: Path
) -> Path:
    """Create a synthetic DOCX with IR markers and content between them.

    Each tuple in *marker_pairs* is ``(block_id, content_type, num_content_paragraphs)``.
    For every tuple the document receives:

    1. A start-marker paragraph ``irstart:block_id`` with ``FirstParagraph`` style
       and ``VerbatimChar`` run style.
    2. *num_content_paragraphs* sample paragraphs with ``BodyText`` style.
    3. An end-marker paragraph ``irend:block_id`` with ``BodyText`` style and
       ``VerbatimChar`` run style.

    Args:
        marker_pairs: List of ``(block_id, content_type, num_content_paragraphs)``
            tuples describing each block.
        output_path: Path where the DOCX will be saved.

    Returns:
        The *output_path*.
    """
    doc = Document()
    _ensure_style(doc, "VerbatimChar", WD_STYLE_TYPE.CHARACTER)
    _ensure_style(doc, "FirstParagraph", WD_STYLE_TYPE.PARAGRAPH)
    _ensure_style(doc, "BodyText", WD_STYLE_TYPE.PARAGRAPH)

    first_para = _ensure_style(doc, "FirstParagraph", WD_STYLE_TYPE.PARAGRAPH)
    body_text = doc.styles["Body Text"]
    verbatim = _ensure_style(doc, "VerbatimChar", WD_STYLE_TYPE.CHARACTER)

    for block_id, content_type, num_content_paragraphs in marker_pairs:
        start_p = doc.add_paragraph(f"irstart:{block_id}")
        start_p.style = first_para
        for run in start_p.runs:
            run.style = verbatim

        for i in range(num_content_paragraphs):
            content_p = doc.add_paragraph(
                f"Sample {content_type} content paragraph {i + 1} for block {block_id}."
            )
            content_p.style = body_text

        end_p = doc.add_paragraph(f"irend:{block_id}")
        end_p.style = body_text
        for run in end_p.runs:
            run.style = verbatim

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def create_docx_with_sections(
    num_sections: int, blocks_per_section: int, output_path: Path
) -> Path:
    """Create a synthetic DOCX with a nested section structure.

    The document contains *num_sections* top-level sections. Each section has a
    heading and *blocks_per_section* body blocks. Every body block is wrapped in
    IR markers (``irstart:section{idx}body{blk}`` / ``irend:section{idx}body{blk}``).

    Args:
        num_sections: Number of sections to create.
        blocks_per_section: Number of body blocks per section.
        output_path: Path where the DOCX will be saved.

    Returns:
        The *output_path*.
    """
    doc = Document()
    first_para = _ensure_style(doc, "FirstParagraph", WD_STYLE_TYPE.PARAGRAPH)
    body_text = doc.styles["Body Text"]
    verbatim = _ensure_style(doc, "VerbatimChar", WD_STYLE_TYPE.CHARACTER)

    for sec_idx in range(num_sections):
        heading_p = doc.add_paragraph(f"Section {sec_idx + 1}")
        heading_p.style = doc.styles["Heading 1"]

        for block_idx in range(blocks_per_section):
            block_id = f"section{sec_idx}body{block_idx}"

            start_p = doc.add_paragraph(f"irstart:{block_id}")
            start_p.style = first_para
            for run in start_p.runs:
                run.style = verbatim

            content_p = doc.add_paragraph(
                f"Content for section {sec_idx}, block {block_idx}."
            )
            content_p.style = body_text

            end_p = doc.add_paragraph(f"irend:{block_id}")
            end_p.style = body_text
            for run in end_p.runs:
                run.style = verbatim

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
