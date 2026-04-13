"""Tests for fallback hash-based matching in injector.

Tests for find_mapping_by_hash() and match_paragraphs_with_fallback()
functions that provide fallback matching when paragraph indices don't align.
"""

import hashlib
import logging

import pytest
from typst_ir.mapping.injector import (
    find_mapping_by_hash,
    match_paragraphs_with_fallback,
)
from typst_ir.mapping.types import DocxParagraph, MappingEntry, NodeID


def _create_node_id(path: str, doc_content: str) -> NodeID:
    """Helper to create NodeID with consistent hashing."""
    full_hash = hashlib.sha256(doc_content.encode()).hexdigest()
    node_hash = hashlib.sha256(path.encode()).hexdigest()
    return NodeID(path=path, full_hash=full_hash, node_hash=node_hash)


def _create_text_hash(text: str) -> str:
    """Helper to create text hash matching extract_paragraphs format."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestFindMappingByHash:
    """Tests for find_mapping_by_hash() function."""

    def test_find_exact_hash_match(self) -> None:
        """find_mapping_by_hash() returns entry when text hash matches node hash."""
        doc_content = "Test Document"
        node_id = _create_node_id("doc.children.0", doc_content)
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=1)

        # Use the same hash that was computed for the node
        result = find_mapping_by_hash(node_id.node_hash, [entry])

        assert result is entry

    def test_returns_none_when_no_match(self) -> None:
        """find_mapping_by_hash() returns None when no hash matches."""
        doc_content = "Test Document"
        node_id = _create_node_id("doc.children.0", doc_content)
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=1)

        different_hash = hashlib.sha256(b"different content").hexdigest()
        result = find_mapping_by_hash(different_hash, [entry])

        assert result is None

    def test_matches_correct_entry_among_multiple(self) -> None:
        """find_mapping_by_hash() finds correct entry among multiple entries."""
        doc_content = "Test Document"

        # Create multiple entries with different hashes
        node_id1 = _create_node_id("doc.children.0", doc_content)
        entry1 = MappingEntry(node_id=node_id1, source_start=0, source_end=1)

        node_id2 = _create_node_id("doc.children.1", doc_content)
        entry2 = MappingEntry(node_id=node_id2, source_start=1, source_end=2)

        node_id3 = _create_node_id("doc.children.2", doc_content)
        entry3 = MappingEntry(node_id=node_id3, source_start=2, source_end=3)

        entries = [entry1, entry2, entry3]

        # Find the middle one
        result = find_mapping_by_hash(node_id2.node_hash, entries)

        assert result is entry2

    def test_empty_entries_returns_none(self) -> None:
        """find_mapping_by_hash() returns None when entries list is empty."""
        text_hash = hashlib.sha256(b"test").hexdigest()
        result = find_mapping_by_hash(text_hash, [])

        assert result is None


class TestMatchParagraphsWithFallback:
    """Tests for match_paragraphs_with_fallback() function."""

    def _create_simple_setup(self) -> tuple[list[DocxParagraph], list[MappingEntry]]:
        """Create paragraphs and entries for testing."""
        text1 = "First paragraph"
        text2 = "Second paragraph"

        para1 = DocxParagraph(
            index=0,
            text_preview=text1,
            text_hash=_create_text_hash(text1),
            paragraph_type="paragraph",
        )
        para2 = DocxParagraph(
            index=1,
            text_preview=text2,
            text_hash=_create_text_hash(text2),
            paragraph_type="paragraph",
        )

        doc_content = "Test Document"
        node_id1 = NodeID(
            path="doc.children.0",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para1.text_hash,
        )
        node_id2 = NodeID(
            path="doc.children.1",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para2.text_hash,
        )

        entry1 = MappingEntry(node_id=node_id1, source_start=0, source_end=1)
        entry2 = MappingEntry(node_id=node_id2, source_start=1, source_end=2)

        return [para1, para2], [entry1, entry2]

    def test_index_based_matching_works(self) -> None:
        """match_paragraphs_with_fallback() uses index matching when indices align."""
        paragraphs, entries = self._create_simple_setup()

        result = match_paragraphs_with_fallback(paragraphs, entries)

        assert len(result) == 2
        assert len(result[0]) == 1
        assert len(result[1]) == 1
        assert result[0][0].source_start == 0
        assert result[1][0].source_start == 1

    def test_fallback_matching_when_indices_misaligned(self, caplog: pytest.LogCaptureFixture) -> None:
        """match_paragraphs_with_fallback() falls back to hash when indices don't align."""
        paragraphs, entries = self._create_simple_setup()

        # Simulate pandoc adding an extra paragraph at the beginning
        # Shift the entry indices to simulate mismatch
        shifted_entries = []
        for entry in entries:
            shifted_entry = MappingEntry(
                node_id=entry.node_id,
                source_start=entry.source_start + 1,  # Shift by 1
                source_end=entry.source_end + 1,
            )
            shifted_entries.append(shifted_entry)

        with caplog.at_level(logging.WARNING):
            result = match_paragraphs_with_fallback(paragraphs, shifted_entries)

        # Should still find matches via hash fallback
        assert len(result) == 2
        assert len(result[0]) == 1
        assert len(result[1]) == 1

        # Should have logged warnings
        assert "Fallback hash matching" in caplog.text

    def test_no_match_returns_empty_list(self, caplog: pytest.LogCaptureFixture) -> None:
        """match_paragraphs_with_fallback() returns empty list when no match found."""
        paragraphs, _ = self._create_simple_setup()

        # Create entries with completely different hashes
        doc_content = "Different Document"
        node_id = _create_node_id("doc.children.0", doc_content)
        entry = MappingEntry(node_id=node_id, source_start=10, source_end=11)

        with caplog.at_level(logging.WARNING):
            result = match_paragraphs_with_fallback(paragraphs, [entry])

        assert len(result) == 2
        assert result[0] == []
        assert result[1] == []

    def test_mixed_matching_some_indices_some_hash(self, caplog: pytest.LogCaptureFixture) -> None:
        """match_paragraphs_with_fallback() handles mix of index and hash matching."""
        text1 = "First paragraph"
        text2 = "Second paragraph"
        text3 = "Third paragraph"

        para1 = DocxParagraph(
            index=0,
            text_preview=text1,
            text_hash=_create_text_hash(text1),
            paragraph_type="paragraph",
        )
        para2 = DocxParagraph(
            index=1,
            text_preview=text2,
            text_hash=_create_text_hash(text2),
            paragraph_type="paragraph",
        )
        para3 = DocxParagraph(
            index=2,
            text_preview=text3,
            text_hash=_create_text_hash(text3),
            paragraph_type="paragraph",
        )

        doc_content = "Test Document"
        node_id1 = NodeID(
            path="doc.children.0",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para1.text_hash,
        )
        node_id2 = NodeID(
            path="doc.children.1",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para2.text_hash,
        )
        node_id3 = NodeID(
            path="doc.children.2",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para3.text_hash,
        )

        # Entry 1 and 3 align by index, entry 2 is misaligned
        entry1 = MappingEntry(node_id=node_id1, source_start=0, source_end=1)
        entry2 = MappingEntry(node_id=node_id2, source_start=5, source_end=6)  # Misaligned
        entry3 = MappingEntry(node_id=node_id3, source_start=2, source_end=3)

        entries = [entry1, entry2, entry3]
        paragraphs = [para1, para2, para3]

        with caplog.at_level(logging.WARNING):
            result = match_paragraphs_with_fallback(paragraphs, entries)

        assert len(result) == 3
        # Para 0: matched by index
        assert result[0][0].node_id.path == "doc.children.0"
        # Para 1: matched by hash fallback (misaligned)
        assert result[1][0].node_id.path == "doc.children.1"
        # Para 2: matched by index
        assert result[2][0].node_id.path == "doc.children.2"

        # Should have logged only one warning for the misaligned paragraph
        assert caplog.text.count("Fallback hash matching") == 1

    def test_logging_includes_paragraph_info(self, caplog: pytest.LogCaptureFixture) -> None:
        """Fallback warning log includes paragraph index and text preview."""
        text = "Test paragraph content"
        para = DocxParagraph(
            index=42,
            text_preview=text,
            text_hash=_create_text_hash(text),
            paragraph_type="paragraph",
        )

        doc_content = "Test Document"
        node_id = NodeID(
            path="doc.children.0",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para.text_hash,
        )
        # Misaligned entry
        entry = MappingEntry(node_id=node_id, source_start=100, source_end=101)

        with caplog.at_level(logging.WARNING):
            match_paragraphs_with_fallback([para], [entry])

        assert "paragraph 42" in caplog.text
        assert "Test paragraph" in caplog.text


class TestFallbackIntegration:
    """Integration tests for fallback scenarios."""

    def test_pandoc_extra_paragraph_scenario(self, caplog: pytest.LogCaptureFixture) -> None:
        """Simulate pandoc adding extra paragraph (e.g., title page) at start."""
        text1 = "Introduction"
        text2 = "Main content"

        para1 = DocxParagraph(
            index=0,
            text_preview=text1,
            text_hash=_create_text_hash(text1),
            paragraph_type="paragraph",
        )
        para2 = DocxParagraph(
            index=1,
            text_preview=text2,
            text_hash=_create_text_hash(text2),
            paragraph_type="paragraph",
        )

        # After pandoc conversion, an extra paragraph is added at index 2
        # (pandoc might add content at the end)
        extra_para = DocxParagraph(
            index=2,
            text_preview="Title Page",
            text_hash=_create_text_hash("Title Page"),
            paragraph_type="paragraph",
        )

        # Original mappings cover indices 0-1, but extra paragraph is at index 2
        doc_content = "Original Document"
        node_id1 = NodeID(
            path="doc.children.0",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para1.text_hash,
        )
        node_id2 = NodeID(
            path="doc.children.1",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para2.text_hash,
        )

        entry1 = MappingEntry(node_id=node_id1, source_start=0, source_end=1)
        entry2 = MappingEntry(node_id=node_id2, source_start=1, source_end=2)

        paragraphs = [para1, para2, extra_para]
        entries = [entry1, entry2]

        with caplog.at_level(logging.WARNING):
            result = match_paragraphs_with_fallback(paragraphs, entries)

        # First two paragraphs match by index
        assert len(result[0]) == 1
        assert result[0][0].node_id.path == "doc.children.0"
        assert len(result[1]) == 1
        assert result[1][0].node_id.path == "doc.children.1"

        # Extra paragraph has no index match (index 2 is outside 0-2 range)
        # and no hash match (different text), so empty
        assert result[2] == []

        # No fallback warnings because the first two matched by index
        assert "Fallback hash matching" not in caplog.text

    def test_paragraph_shifted_by_pandoc_with_hash_match(self, caplog: pytest.LogCaptureFixture) -> None:
        """Paragraph moved to different index but content matches via hash."""
        text1 = "Introduction"
        text2 = "Main content"

        # Original order: Introduction (idx 0), Main content (idx 1)
        # After pandoc: shifted, Introduction at idx 5, Main content at idx 6
        para1 = DocxParagraph(
            index=5,
            text_preview=text1,
            text_hash=_create_text_hash(text1),
            paragraph_type="paragraph",
        )
        para2 = DocxParagraph(
            index=6,
            text_preview=text2,
            text_hash=_create_text_hash(text2),
            paragraph_type="paragraph",
        )

        # Original mappings have different indices (0 and 1)
        doc_content = "Original Document"
        node_id1 = NodeID(
            path="doc.children.0",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para1.text_hash,
        )
        node_id2 = NodeID(
            path="doc.children.1",
            full_hash=hashlib.sha256(doc_content.encode()).hexdigest(),
            node_hash=para2.text_hash,
        )

        entry1 = MappingEntry(node_id=node_id1, source_start=0, source_end=1)
        entry2 = MappingEntry(node_id=node_id2, source_start=1, source_end=2)

        paragraphs = [para1, para2]
        entries = [entry1, entry2]

        with caplog.at_level(logging.WARNING):
            result = match_paragraphs_with_fallback(paragraphs, entries)

        # Both should match via hash fallback (indices 5,6 don't match entry ranges 0-1,1-2)
        assert result[5][0].node_id.path == "doc.children.0"
        assert result[6][0].node_id.path == "doc.children.1"

        # Both triggered fallback
        assert caplog.text.count("Fallback hash matching") == 2
