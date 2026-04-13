"""ID injection into DOCX documents."""

from __future__ import annotations

import hashlib
import logging
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from docx import Document

from typst_ir.mapping.types import (
    ConfidenceLevel,
    DocxParagraph,
    DocxTypstMapping,
    MappingEntry,
)

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph


# Configure logger for this module
logger = logging.getLogger(__name__)


def find_mapping_by_hash(
    text_hash: str, sorted_entries: list[MappingEntry]
) -> MappingEntry | None:
    """Find a mapping entry by matching text hash to node hash.

    This function provides fallback matching when index-based matching
    fails (e.g., when pandoc adds extra paragraphs or changes order).

    Args:
        text_hash: SHA-256 hash of the paragraph text content
        sorted_entries: List of mapping entries sorted by source_start

    Returns:
        The matching MappingEntry if found, None otherwise
    """
    for entry in sorted_entries:
        # Compare paragraph text hash with node hash from registry
        if entry.node_id.node_hash == text_hash:
            return entry
    return None


def match_paragraphs_with_fallback(
    paragraphs: list[DocxParagraph],
    sorted_entries: list[MappingEntry],
) -> dict[int, list[MappingEntry]]:
    """Match paragraphs to mapping entries with hash-based fallback.

    First attempts index-based matching. If that fails (no entries match
    the paragraph index), falls back to hash-based matching by comparing
    paragraph text hashes with node content hashes.

    Args:
        paragraphs: List of extracted paragraphs from DOCX
        sorted_entries: List of mapping entries sorted by source_start

    Returns:
        Dictionary mapping paragraph index to list of matching entries
    """
    matches: dict[int, list[MappingEntry]] = {}

    for para in paragraphs:
        index_matches = _find_matching_entries(para.index, sorted_entries)

        confident_matches = [
            entry
            for entry in index_matches
            if entry.confidence is None or entry.confidence != ConfidenceLevel.low
        ]

        if confident_matches:
            matches[para.index] = confident_matches
        else:
            hash_match = find_mapping_by_hash(para.text_hash, sorted_entries)

            if hash_match:
                logger.warning(
                    "Fallback hash matching used for paragraph %d (text preview: %r)",
                    para.index,
                    para.text_preview[:50],
                )
                matches[para.index] = [hash_match]
            else:
                matches[para.index] = []

    return matches


def extract_paragraphs(docx_path: Path) -> list[DocxParagraph]:
    """Extract paragraph metadata from a DOCX file."""
    if not docx_path.exists():
        raise FileNotFoundError(f"Input file not found: {docx_path}")

    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                raise ValueError(f"Invalid DOCX file: {docx_path}")
    except zipfile.BadZipFile as e:
        raise ValueError(f"Invalid DOCX file: {docx_path}") from e

    doc = Document(str(docx_path))
    paragraphs: list[DocxParagraph] = []
    all_paragraphs: list[Paragraph] = []

    for paragraph in doc.paragraphs:
        all_paragraphs.append(paragraph)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    all_paragraphs.append(paragraph)

    for idx, paragraph in enumerate(all_paragraphs):
        text = paragraph.text or ""
        text_preview = text[:100] if text else ""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        paragraph_type = _detect_paragraph_type(paragraph)

        docx_para = DocxParagraph(
            index=idx,
            text_preview=text_preview,
            text_hash=text_hash,
            paragraph_type=paragraph_type,
        )
        paragraphs.append(docx_para)

    return paragraphs


def _detect_paragraph_type(paragraph: Paragraph) -> str:
    style_name = paragraph.style.name if paragraph.style else ""

    if not style_name:
        return "paragraph"

    style_lower = style_name.lower()

    if "heading" in style_lower:
        return "heading"

    if "list" in style_lower:
        return "list_item"

    p_element = paragraph._p
    parent = p_element.getparent()
    while parent is not None:
        if parent.tag.endswith("tc"):
            return "table_cell"
        parent = parent.getparent()

    return "paragraph"


def inject_ids(docx_path: Path, output_path: Path, mapping: DocxTypstMapping) -> None:
    """Inject w:customIRID attributes into DOCX paragraph elements."""
    if not docx_path.exists():
        raise FileNotFoundError(f"Input file not found: {docx_path}")

    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                raise ValueError(f"Invalid DOCX file: {docx_path}")
    except zipfile.BadZipFile as e:
        raise ValueError(f"Invalid DOCX file: {docx_path}") from e

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(docx_path, output_path)

    doc = Document(str(output_path))
    all_paragraphs: list[Paragraph] = []

    for paragraph in doc.paragraphs:
        all_paragraphs.append(paragraph)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    all_paragraphs.append(paragraph)

    sorted_entries = sorted(mapping.entries.values(), key=lambda e: e.source_start)
    paragraphs = extract_paragraphs(docx_path)
    matches = match_paragraphs_with_fallback(paragraphs, sorted_entries)

    for para_idx, paragraph in enumerate(all_paragraphs):
        matching_entries = matches.get(para_idx, [])
        if matching_entries:
            _inject_paragraph_ids(paragraph, matching_entries)

    doc.save(str(output_path))


def _find_matching_entries(para_idx: int, sorted_entries: list[MappingEntry]) -> list[MappingEntry]:
    return [entry for entry in sorted_entries if entry.source_start <= para_idx < entry.source_end]


def _inject_paragraph_ids(paragraph: Paragraph, entries: list[MappingEntry]) -> None:
    p_element = paragraph._p
    pPr = p_element.get_or_add_pPr()
    attrib_name = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}customIRID"

    new_ids = [entry.node_id.canonical for entry in entries]
    new_value = ",".join(new_ids)

    if attrib_name in pPr.attrib:
        existing_value = pPr.attrib[attrib_name]
        if existing_value == new_value:
            return
        existing_ids = set(existing_value.split(","))
        if all(id in existing_ids for id in new_ids):
            return
    pPr.attrib[attrib_name] = new_value
