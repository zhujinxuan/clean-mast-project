"""TDD Red-phase tests for Pass 1 heading matcher.

These tests call match_headings() before it is implemented,
so they are expected to fail with ImportError or AttributeError.
"""

from unittest.mock import MagicMock

from typst_ir import TypstHeading
from typst_ir.mapping.matcher import match_headings
from typst_ir.mapping.types import ConfidenceLevel, DetectionMethod, MappingEntry


def _make_style_mock(style_name: str):
    """Return a minimal style duck-typed object."""
    style = MagicMock()
    style.name = style_name
    return style


def _make_outline_xml_mock(level_val: str):
    """Build minimal XML mock for w:outlineLvl detection."""
    # qn("w:val") expands to something like:
    #   {http://schemas.openxmlformats.org/wordprocessingml/2006/main}val
    outline_lvl = MagicMock()
    outline_lvl.get = MagicMock(return_value=level_val)

    pPr_ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr"
    outline_ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}outlineLvl"

    pPr = MagicMock()
    pPr.find = MagicMock(return_value=outline_lvl)

    element = MagicMock()

    def _find(tag):
        if tag == pPr_ns:
            return pPr
        if tag == outline_ns:
            return outline_lvl
        return None

    element.find = MagicMock(side_effect=_find)
    return element


def _make_docx_para(text: str, style_name: str = "Normal", outline_level: str | None = None):
    """Create a synthetic DOCX Paragraph stand-in."""
    para = MagicMock()
    para.text = text
    para.style = _make_style_mock(style_name)
    if outline_level is not None:
        para._element = _make_outline_xml_mock(outline_level)
    else:
        para._element = MagicMock()
        para._element.find = MagicMock(return_value=None)
    return para


class TestMatchHeadingByStyle:
    def test_match_heading_by_style(self) -> None:
        docx_spans = [_make_docx_para("Introduction", style_name="Heading 1")]
        ir_nodes = [TypstHeading(text="Introduction")]

        entries = match_headings(ir_nodes, docx_spans)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 1
        assert entry.method == DetectionMethod.style
        assert entry.confidence == ConfidenceLevel.high
        assert entry.details.get("level") == 1
        assert "TypstHeading" in entry.node_id.path

    def test_match_heading_by_outline_level(self) -> None:
        docx_spans = [_make_docx_para("Methods", style_name="Normal", outline_level="1")]
        ir_nodes = [TypstHeading(text="Methods")]

        entries = match_headings(ir_nodes, docx_spans)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 1
        assert entry.method == DetectionMethod.xpath
        assert entry.confidence == ConfidenceLevel.high
        assert entry.details.get("level") == 1
        assert "TypstHeading" in entry.node_id.path

    def test_match_heading_level_mismatch(self) -> None:
        docx_spans = [_make_docx_para("Introduction", style_name="Heading 2")]
        ir_nodes = [TypstHeading(text="Introduction")]

        entries = match_headings(ir_nodes, docx_spans)

        assert entries == []

    def test_match_heading_text_fingerprint(self) -> None:
        docx_spans = [_make_docx_para("Results and Discussion", style_name="Heading 1")]
        ir_nodes = [TypstHeading(text="Results and Discussion")]

        entries = match_headings(ir_nodes, docx_spans)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 1
        assert entry.method == DetectionMethod.fingerprint
        assert entry.confidence == ConfidenceLevel.high
        assert "TypstHeading" in entry.node_id.path

    def test_match_multiple_headings_in_sequence(self) -> None:
        docx_spans = [
            _make_docx_para("First", style_name="Heading 1"),
            _make_docx_para("Second", style_name="Heading 1"),
            _make_docx_para("Third", style_name="Heading 1"),
        ]
        ir_nodes = [
            TypstHeading(text="First"),
            TypstHeading(text="Second"),
            TypstHeading(text="Third"),
        ]

        entries = match_headings(ir_nodes, docx_spans)

        assert len(entries) == 3
        for i, entry in enumerate(entries):
            assert isinstance(entry, MappingEntry)
            assert entry.source_start == i
            assert entry.source_end == i + 1
            assert "TypstHeading" in entry.node_id.path
            assert entry.confidence in {ConfidenceLevel.high, ConfidenceLevel.medium}

    def test_heading_with_no_ir_heading(self) -> None:
        docx_spans = [_make_docx_para("Extra Heading", style_name="Heading 1")]
        ir_nodes: list[TypstHeading] = []

        entries = match_headings(ir_nodes, docx_spans)

        assert entries == []
