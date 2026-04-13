"""Integration tests using experiment fixtures to verify detection methods.

These tests exercise the real DOCX files generated during the detection
experiments (paragraph, heading, table, figure, equation) and assert that
DocxMatcher and the lower-level detection functions behave as expected.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document
from typst_ir import (
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from typst_ir.mapping import DocxMatcher
from typst_ir.mapping.detection import (
    detect_figures,
    detect_heading_level,
    match_figure,
    match_paragraph_fingerprint,
)
from typst_ir.mapping.types import ConfidenceLevel, DetectionMethod

pytestmark = pytest.mark.skip(reason="Fixture DOCX files missing — directory does not exist")


@pytest.fixture
def fixture_docx_dir() -> Path:
    """Return path to the experiment DOCX fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "docx"


class TestParagraphDetection:
    """Paragraph fingerprint matching against paragraph.docx."""

    def test_paragraph_fingerprint_matching(self, fixture_docx_dir: Path) -> None:
        """All three paragraphs should match via fingerprint with high confidence."""
        doc = Document(str(fixture_docx_dir / "paragraph.docx"))
        ir_nodes = [
            TypstParagraph(text="First paragraph unique hash abc123."),
            TypstParagraph(text="Second paragraph unique hash def456."),
            TypstParagraph(text="Third paragraph unique hash ghi789."),
        ]

        matcher = DocxMatcher()
        mappings = matcher.match(ir_nodes, doc)

        assert len(mappings) == 3
        for mapping in mappings:
            assert mapping.method == DetectionMethod.fingerprint
            assert mapping.confidence == ConfidenceLevel.high


class TestHeadingDetection:
    """Heading style detection against heading.docx."""

    def test_heading_style_detection(self, fixture_docx_dir: Path) -> None:
        """Headings should match by style level; paragraphs by fingerprint."""
        doc = Document(str(fixture_docx_dir / "heading.docx"))
        ir_nodes = [
            TypstHeading(text="Level One Unique Hash X1"),
            TypstParagraph(text="Content under level one unique A1"),
            TypstHeading(text="Level Two Unique Hash Y2"),
            TypstParagraph(text="Content under level two unique B2"),
            TypstHeading(text="Level Three Unique Hash Z3"),
            TypstParagraph(text="Content under level three unique C3"),
        ]

        matcher = DocxMatcher()
        mappings = matcher.match(ir_nodes, doc)

        assert len(mappings) == 6

        heading_mappings = [m for m in mappings if "TypstHeading" in m.node_id.path]
        assert len(heading_mappings) == 3
        for mapping in heading_mappings:
            assert mapping.method in {
                DetectionMethod.style,
                DetectionMethod.fingerprint,
                DetectionMethod.xpath,
            }
            assert mapping.confidence == ConfidenceLevel.high
            assert detect_heading_level(doc.paragraphs[mapping.source_start]) == mapping.details["level"]

        paragraph_mappings = [m for m in mappings if "TypstParagraph" in m.node_id.path]
        assert len(paragraph_mappings) == 3
        for mapping in paragraph_mappings:
            assert mapping.method == DetectionMethod.fingerprint
            assert mapping.confidence == ConfidenceLevel.high


class TestTableDetection:
    """Table structure/caption matching against table.docx."""

    def test_table_structure_and_caption_matching(self, fixture_docx_dir: Path) -> None:
        """Table matches via structure and caption (header row now counted)."""
        doc = Document(str(fixture_docx_dir / "table.docx"))
        ir_nodes = [
            TypstHeading(text="Paragraph before table unique P1"),
            TypstTable(
                headers=["Col A Uniq1", "Col B Uniq2"],
                data=[
                    ["Cell 1-1 Unique X1", "Cell 1-2 Unique Y1"],
                    ["Cell 2-1 Unique X2", "Cell 2-2 Unique Y2"],
                ],
                caption="Table One Caption Unique Q1",
            ),
            TypstHeading(text="Paragraph after table unique P2"),
        ]

        matcher = DocxMatcher()
        mappings = matcher.match(ir_nodes, doc)

        assert len(mappings) == 3

        table_mapping = next(m for m in mappings if "TypstTable" in m.node_id.path)
        assert table_mapping.method == DetectionMethod.fingerprint
        assert table_mapping.confidence == ConfidenceLevel.high
        assert table_mapping.source_start == 1

        heading_mappings = [m for m in mappings if "TypstHeading" in m.node_id.path]
        assert len(heading_mappings) == 2
        for mapping in heading_mappings:
            assert mapping.method == DetectionMethod.fingerprint
            assert mapping.confidence == ConfidenceLevel.high


class TestFigureDetection:
    """Figure drawing/caption detection against figure.docx."""

    def test_figure_detection_in_pandoc_docx(self, fixture_docx_dir: Path) -> None:
        """Pandoc-generated figure.docx stores the image as a 1x1 table placeholder
        and an ``Image Caption`` paragraph without ``<w:drawing>`` elements.

        This test verifies that:
        - The surrounding paragraphs still map with high confidence.
        - ``detect_figures`` returns an empty list (no drawings).
        - The caption paragraph is present and its text fingerprints to the IR caption.
        - ``match_figure`` returns low confidence because the drawing element is absent,
            which is the expected behaviour for this pandoc-generated fixture.
        """
        doc = Document(str(fixture_docx_dir / "figure.docx"))
        ir_figure = TypstFigure(
            content="figure1.png",
            caption="Figure One Caption Unique F1",
        )
        ir_nodes = [
            TypstParagraph(text="Paragraph before figure unique P1"),
            ir_figure,
            TypstParagraph(text="Paragraph after figure unique P2"),
        ]

        matcher = DocxMatcher()
        mappings = matcher.match(ir_nodes, doc)

        paragraph_mappings = [m for m in mappings if "TypstParagraph" in m.node_id.path]
        assert len(paragraph_mappings) == 2
        assert paragraph_mappings[0].method == DetectionMethod.fingerprint
        assert paragraph_mappings[0].confidence == ConfidenceLevel.high

        figure_mappings = [m for m in mappings if "TypstFigure" in m.node_id.path]
        assert len(figure_mappings) == 0

        assert detect_figures(doc) == []

        caption_paras = [
            p for p in doc.paragraphs
            if p.style and "caption" in p.style.name.lower()
        ]
        assert len(caption_paras) == 1
        is_match, _cov_a, _cov_b = match_paragraph_fingerprint(
            ir_figure.caption, caption_paras[0].text
        )
        assert is_match is True

        contents = list(doc.iter_inner_content())
        caption_idx = next(
            i for i, c in enumerate(contents)
            if getattr(c, "style", None) and "caption" in c.style.name.lower()
        )
        result = match_figure(ir_figure, contents[caption_idx], contents, caption_idx)
        assert result["drawing"] is False
        assert result["confidence"] == "low"


class TestEquationDetection:
    """Equation OMML detection against equation.docx."""

    def test_equation_omml_detection(self, fixture_docx_dir: Path) -> None:
        """Both display equations should map via OMML xpath with high confidence.

        The inline equation embedded in the paragraph text is represented as a
        plain-text paragraph in the IR (pandoc stripped the inline math), so it
        matches via fingerprint like a regular paragraph.
        """
        doc = Document(str(fixture_docx_dir / "equation.docx"))
        ir_nodes = [
            TypstParagraph(text="Text before equation unique P1"),
            TypstEquation(latex="E = m c^2", display=True),
            TypstParagraph(text="Text with inline equation "),
            TypstEquation(latex="sum_(i=1)^n x_i", display=True),
            TypstParagraph(text="Text after equation unique P2"),
        ]

        matcher = DocxMatcher()
        mappings = matcher.match(ir_nodes, doc)

        assert len(mappings) == 5

        equation_mappings = [m for m in mappings if "TypstEquation" in m.node_id.path]
        assert len(equation_mappings) == 2
        for mapping in equation_mappings:
            assert mapping.method == DetectionMethod.xpath
            assert mapping.confidence == ConfidenceLevel.high
            assert mapping.details["type"] == "display"

        paragraph_mappings = [m for m in mappings if "TypstParagraph" in m.node_id.path]
        assert len(paragraph_mappings) == 3
        for mapping in paragraph_mappings:
            assert mapping.method == DetectionMethod.fingerprint
            assert mapping.confidence == ConfidenceLevel.high


class TestEdgeCases:
    """Regression tests for edge cases."""

    def test_empty_document_unmatched_node(self) -> None:
        """An empty DOCX should produce zero mappings for any IR node."""
        doc = Document()
        ir_nodes = [
            TypstSection(
                heading=TypstHeading(text=""),
                body=[TypstParagraph(text="This paragraph does not exist.")],
                subsections=[],
            )
        ]

        matcher = DocxMatcher()
        mappings = matcher.match(ir_nodes, doc)

        assert len(mappings) == 0

    def test_unmatched_heading_logs_and_skips(self, fixture_docx_dir: Path, caplog) -> None:
        """A heading IR node with a mismatched level should remain unmatched."""
        doc = Document(str(fixture_docx_dir / "paragraph.docx"))
        ir_nodes = [TypstHeading(text="First paragraph unique hash abc123.")]

        matcher = DocxMatcher()
        with caplog.at_level("WARNING"):
            mappings = matcher.match(ir_nodes, doc)

        assert len(mappings) == 0
        assert "Unmatched" in caplog.text or "unmatched" in caplog.text.lower()
