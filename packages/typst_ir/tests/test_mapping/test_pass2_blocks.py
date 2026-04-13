"""TDD Red-phase tests for Pass 2 block matching (figures, tables, equations).

These tests call group_docx_spans() and match_blocks() before they are
implemented, so they are expected to fail with ImportError or AttributeError.
"""

from unittest.mock import MagicMock

from typst_ir import TypstEquation, TypstFigure, TypstTable
from typst_ir.mapping.detection import group_docx_spans
from typst_ir.mapping.matcher import match_blocks
from typst_ir.mapping.types import ConfidenceLevel, DetectionMethod, MappingEntry


def _make_style_mock(style_name: str):
    """Return a minimal style duck-typed object."""
    style = MagicMock()
    style.name = style_name
    return style


def _make_drawing_para(text: str = ""):
    """Create a synthetic DOCX Paragraph containing a w:drawing element."""
    para = MagicMock()
    para.text = text
    para.style = _make_style_mock("Normal")
    element = MagicMock()
    element.findall = MagicMock(return_value=[MagicMock()])
    para._element = element
    return para


def _make_text_para(text: str, style_name: str = "Normal"):
    """Create a synthetic DOCX Paragraph with text but no special elements."""
    para = MagicMock()
    para.text = text
    para.style = _make_style_mock(style_name)
    element = MagicMock()
    element.findall = MagicMock(return_value=[])
    para._element = element
    return para


def _make_caption_para(text: str, caption_style: str = "Caption"):
    """Create a synthetic DOCX Paragraph styled as a caption."""
    return _make_text_para(text, style_name=caption_style)


def _make_table_mock(rows: int = 2, cols: int = 2):
    """Create a synthetic DOCX Table with given dimensions."""
    table = MagicMock()
    table.rows = [MagicMock() for _ in range(rows)]
    table.columns = [MagicMock() for _ in range(cols)]
    return table


def _make_equation_para(math_tag: str = "m:oMathPara"):
    """Create a synthetic DOCX Paragraph containing OMML math."""
    para = MagicMock()
    para.text = ""
    para.style = _make_style_mock("Normal")
    element = MagicMock()

    def _findall(xpath):
        if math_tag.replace("m:", "") in xpath:
            return [MagicMock()]
        return []

    element.findall = MagicMock(side_effect=_findall)
    para._element = element
    return para


class TestGroupDocxSpans:
    """Tests for group_docx_spans() — DOCX content grouping into spans."""

    def test_group_figure_with_caption_after(self) -> None:
        docx_contents = [
            _make_drawing_para(),
            _make_caption_para("Figure 1: Wind rose"),
        ]
        spans = group_docx_spans(docx_contents)

        assert len(spans) == 1
        assert spans[0].label == "figure+caption"
        assert spans[0].start == 0
        assert spans[0].end == 2

    def test_group_figure_without_caption(self) -> None:
        docx_contents = [_make_drawing_para()]
        spans = group_docx_spans(docx_contents)

        assert len(spans) == 1
        assert spans[0].label == "figure"
        assert spans[0].start == 0
        assert spans[0].end == 1

    def test_group_table_with_caption_before(self) -> None:
        docx_contents = [
            _make_caption_para("Table 1: Measurements"),
            _make_table_mock(rows=2, cols=3),
        ]
        spans = group_docx_spans(docx_contents)

        assert len(spans) == 1
        assert spans[0].label == "caption+table"
        assert spans[0].start == 0
        assert spans[0].end == 2

    def test_group_table_without_caption(self) -> None:
        docx_contents = [_make_table_mock(rows=1, cols=2)]
        spans = group_docx_spans(docx_contents)

        assert len(spans) == 1
        assert spans[0].label == "table"
        assert spans[0].start == 0
        assert spans[0].end == 1

    def test_group_equation_display(self) -> None:
        docx_contents = [_make_equation_para("m:oMathPara")]
        spans = group_docx_spans(docx_contents)

        assert len(spans) == 1
        assert spans[0].label == "equation"
        assert spans[0].start == 0
        assert spans[0].end == 1

    def test_group_no_adjacent_captions(self) -> None:
        docx_contents = [
            _make_text_para("First paragraph."),
            _make_text_para("Second paragraph."),
        ]
        spans = group_docx_spans(docx_contents)

        assert len(spans) == 2
        assert spans[0].label == "paragraph"
        assert spans[0].start == 0
        assert spans[0].end == 1
        assert spans[1].label == "paragraph"
        assert spans[1].start == 1
        assert spans[1].end == 2

    def test_caption_before_and_after_figure(self) -> None:
        """Bidirectional caption grouping: image caption after drawing and table caption before table."""
        docx_contents = [
            _make_drawing_para(),
            _make_caption_para("Image Caption", caption_style="Image Caption"),
            _make_caption_para("Table Caption", caption_style="Table Caption"),
            _make_table_mock(rows=2, cols=2),
        ]
        spans = group_docx_spans(docx_contents)

        assert len(spans) == 2
        assert spans[0].label == "figure+caption"
        assert spans[0].start == 0
        assert spans[0].end == 2
        assert spans[1].label == "caption+table"
        assert spans[1].start == 2
        assert spans[1].end == 4


class TestMatchBlocks:
    """Tests for match_blocks() — IR nodes to grouped DOCX spans matching."""

    def _make_span(self, label: str, start: int, end: int):
        """Helper to create a span duck-typed object."""
        span = MagicMock()
        span.label = label
        span.start = start
        span.end = end
        return span

    def _make_node_id(self, path: str):
        """Helper to create a minimal NodeID duck-typed object."""
        node_id = MagicMock()
        node_id.path = path
        node_id.canonical = f"{path}:full_hash:node_hash"
        return node_id

    def test_match_figure_by_drawing(self) -> None:
        ir_nodes = [TypstFigure(content="image.png", caption="")]
        docx_spans = [self._make_span("figure", 0, 1)]
        heading_anchors: list[MappingEntry] = []

        entries = match_blocks(ir_nodes, docx_spans, heading_anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 1
        assert entry.method == DetectionMethod.drawing
        assert entry.confidence == ConfidenceLevel.high
        assert "TypstFigure" in entry.node_id.path

    def test_match_figure_by_caption_fingerprint(self) -> None:
        ir_nodes = [TypstFigure(content="image.png", caption="Wind rose diagram")]
        docx_spans = [self._make_span("figure+caption", 0, 2)]
        heading_anchors: list[MappingEntry] = []

        entries = match_blocks(ir_nodes, docx_spans, heading_anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 2
        assert entry.method == DetectionMethod.fingerprint
        assert entry.confidence == ConfidenceLevel.high
        assert "TypstFigure" in entry.node_id.path

    def test_match_table_by_structure(self) -> None:
        ir_nodes = [
            TypstTable(
                headers=["A", "B"],
                data=[["1", "2"]],
                caption=None,
            )
        ]
        docx_spans = [self._make_span("table", 0, 1)]
        heading_anchors: list[MappingEntry] = []

        entries = match_blocks(ir_nodes, docx_spans, heading_anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 1
        assert entry.method == DetectionMethod.structure
        assert entry.confidence == ConfidenceLevel.high
        assert "TypstTable" in entry.node_id.path

    def test_match_table_by_caption(self) -> None:
        ir_nodes = [
            TypstTable(
                headers=["X", "Y", "Z"],
                data=[["1", "2", "3"]],
                caption="Measurements summary",
            )
        ]
        docx_spans = [self._make_span("caption+table", 0, 2)]
        heading_anchors: list[MappingEntry] = []

        entries = match_blocks(ir_nodes, docx_spans, heading_anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 2
        assert entry.method in {DetectionMethod.caption, DetectionMethod.fingerprint}
        assert entry.confidence in {ConfidenceLevel.high, ConfidenceLevel.medium}
        assert "TypstTable" in entry.node_id.path

    def test_match_equation_display(self) -> None:
        ir_nodes = [TypstEquation(latex="E = mc^2", display=True)]
        docx_spans = [self._make_span("equation", 0, 1)]
        heading_anchors: list[MappingEntry] = []

        entries = match_blocks(ir_nodes, docx_spans, heading_anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 1
        assert entry.method == DetectionMethod.xpath
        assert entry.confidence == ConfidenceLevel.high
        assert entry.details.get("type") == "display"
        assert "TypstEquation" in entry.node_id.path

    def test_match_equation_inline(self) -> None:
        ir_nodes = [TypstEquation(latex="a^2 + b^2 = c^2", display=False)]
        docx_spans = [self._make_span("equation", 0, 1)]
        heading_anchors: list[MappingEntry] = []

        entries = match_blocks(ir_nodes, docx_spans, heading_anchors)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, MappingEntry)
        assert entry.source_start == 0
        assert entry.source_end == 1
        assert entry.method == DetectionMethod.xpath
        assert entry.confidence == ConfidenceLevel.high
        assert entry.details.get("type") == "inline"
        assert "TypstEquation" in entry.node_id.path

    def test_no_match_wrong_type(self) -> None:
        ir_nodes = [TypstFigure(content="image.png", caption="A figure")]
        docx_spans = [self._make_span("table", 0, 1)]
        heading_anchors: list[MappingEntry] = []

        entries = match_blocks(ir_nodes, docx_spans, heading_anchors)

        assert entries == []
