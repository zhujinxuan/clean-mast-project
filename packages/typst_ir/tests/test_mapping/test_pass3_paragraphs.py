"""TDD Red-phase tests for Pass 3 paragraph matcher.

These tests call match_paragraphs() before it is implemented,
so they are expected to fail with ImportError or AttributeError.
"""

from unittest.mock import MagicMock

from typst_ir import TypstParagraph
from typst_ir.mapping.matcher import match_paragraphs
from typst_ir.mapping.types import ConfidenceLevel, DetectionMethod, MappingEntry, NodeID


def _make_node_id(path: str) -> NodeID:
    return NodeID(path=path, full_hash="hash1", node_hash="hash2")


def _make_anchor(path: str, source_start: int, source_end: int) -> MappingEntry:
    return MappingEntry(
        node_id=_make_node_id(path),
        source_start=source_start,
        source_end=source_end,
        method=DetectionMethod.style,
        confidence=ConfidenceLevel.high,
        details={},
    )


def _make_docx_para(text: str) -> MagicMock:
    para = MagicMock()
    para.text = text
    para.style = MagicMock()
    para.style.name = "Normal"
    para._element = MagicMock()
    return para


class TestMatchParagraphs:
    def test_match_by_fingerprint(self) -> None:
        ir_paragraphs = [
            TypstParagraph(text="Wind speed measurements at 80 meters height."),
        ]
        docx_spans = [
            _make_docx_para("Wind speed measurements at 80 meters height."),
        ]
        anchors = [
            _make_anchor("doc.children.0[TypstHeading]", 0, 1),
            _make_anchor("doc.children.2[TypstHeading]", 2, 3),
        ]

        entries = match_paragraphs(ir_paragraphs, docx_spans, anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 1
        assert entry.source_end == 2
        assert entry.method == DetectionMethod.fingerprint
        assert entry.confidence == ConfidenceLevel.high
        assert "TypstParagraph" in entry.node_id.path

    def test_match_by_positional_fallback(self) -> None:
        ir_paragraphs = [TypstParagraph(text="Completely different IR text content.")]
        docx_spans = [_make_docx_para("Unrelated DOCX paragraph text here.")]
        anchors = [
            _make_anchor("doc.children.0[TypstHeading]", 0, 1),
            _make_anchor("doc.children.2[TypstHeading]", 2, 3),
        ]

        entries = match_paragraphs(ir_paragraphs, docx_spans, anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 1
        assert entry.source_end == 2
        assert entry.method == DetectionMethod.positional
        assert entry.confidence == ConfidenceLevel.low
        assert "TypstParagraph" in entry.node_id.path

    def test_match_within_segment(self) -> None:
        ir_paragraphs = [TypstParagraph(text="Target paragraph in the middle.")]
        docx_spans = [
            _make_docx_para("Before segment heading"),
            _make_docx_para("Target paragraph in the middle."),
            _make_docx_para("After segment heading"),
        ]
        anchors = [
            _make_anchor("doc.children.0[TypstHeading]", 0, 1),
            _make_anchor("doc.children.2[TypstHeading]", 2, 3),
        ]

        entries = match_paragraphs(ir_paragraphs, docx_spans, anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 1
        assert entry.source_end == 2
        assert entry.method == DetectionMethod.fingerprint
        assert entry.confidence == ConfidenceLevel.high

    def test_no_match_empty_paragraph(self) -> None:
        ir_paragraphs = [TypstParagraph(text="Some paragraph text here.")]
        docx_spans = [_make_docx_para("")]
        anchors = [
            _make_anchor("doc.children.0[TypstHeading]", 0, 1),
            _make_anchor("doc.children.2[TypstHeading]", 2, 3),
        ]

        entries = match_paragraphs(ir_paragraphs, docx_spans, anchors)

        assert entries == []

    def test_multiple_paragraphs_in_segment(self) -> None:
        ir_paragraphs = [
            TypstParagraph(text="First paragraph of the section."),
            TypstParagraph(text="Second paragraph of the section."),
            TypstParagraph(text="Third paragraph of the section."),
        ]
        docx_spans = [
            _make_docx_para("First paragraph of the section."),
            _make_docx_para("Second paragraph of the section."),
            _make_docx_para("Third paragraph of the section."),
        ]
        anchors = [
            _make_anchor("doc.children.0[TypstHeading]", 0, 1),
            _make_anchor("doc.children.4[TypstHeading]", 4, 5),
        ]

        entries = match_paragraphs(ir_paragraphs, docx_spans, anchors)

        assert len(entries) == 3
        for i, entry in enumerate(entries):
            assert isinstance(entry, MappingEntry)
            assert entry.source_start == i + 1
            assert entry.source_end == i + 2
            assert entry.confidence in {ConfidenceLevel.high, ConfidenceLevel.low}
            assert "TypstParagraph" in entry.node_id.path

    def test_fingerprint_with_partial_overlap(self) -> None:
        ir_paragraphs = [TypstParagraph(text="Wind speed at 80 m height")]
        # DOCX is a superset of IR text: coverage on IR side = 1.0, DOCX side >= 0.8
        docx_spans = [_make_docx_para("The Wind speed at 80 m height today")]
        anchors = [
            _make_anchor("doc.children.0[TypstHeading]", 0, 1),
            _make_anchor("doc.children.2[TypstHeading]", 2, 3),
        ]

        entries = match_paragraphs(ir_paragraphs, docx_spans, anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.method == DetectionMethod.fingerprint
        assert entry.confidence == ConfidenceLevel.high

    def test_fingerprint_below_threshold(self) -> None:
        ir_paragraphs = [TypstParagraph(text="abcdefghijklmnopqrstuvwxyz0123456789")]
        # Only 26 of 36 chars overlap (coverage ~0.72 on both sides), below 0.8 threshold
        docx_spans = [_make_docx_para("abcdefghijklmnopqrstuvwxyz9876543210")]
        anchors = [
            _make_anchor("doc.children.0[TypstHeading]", 0, 1),
            _make_anchor("doc.children.2[TypstHeading]", 2, 3),
        ]

        entries = match_paragraphs(ir_paragraphs, docx_spans, anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.method == DetectionMethod.positional
        assert entry.confidence == ConfidenceLevel.low
