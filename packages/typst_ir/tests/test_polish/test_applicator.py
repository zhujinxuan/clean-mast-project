"""Tests for the DOCX polish style applicator."""

from __future__ import annotations

import logging

import pytest
from docx import Document
from docx.shared import Pt, RGBColor
from typst_ir.mapping.types import DocxTypstMapping, MappingEntry, NodeID
from typst_ir.polish.applicator import (
    apply_mixed_fonts_to_style,
    apply_renumbering,
    apply_styles,
)
from typst_ir.polish.types import RenumberOp, StyleOp


class TestApplyStyles:
    """Tests for ``apply_styles``."""

    def test_apply_font_properties(self) -> None:
        doc = Document()
        style = doc.styles["Normal"]
        style_op = StyleOp(
            style_name="Normal",
            font_name="Arial",
            font_size=14.0,
            font_style="bold_italic",
            font_color="#FF0000",
            line_spacing_before=6.0,
            line_spacing_after=12.0,
        )

        apply_styles(doc, [style_op])

        assert style.font.name == "Arial"
        assert style.font.size == Pt(14)
        assert style.font.bold is True
        assert style.font.italic is True
        assert style.font.color.rgb == RGBColor.from_string("FF0000")
        assert style.paragraph_format.space_before == Pt(6)
        assert style.paragraph_format.space_after == Pt(12)

    @pytest.mark.parametrize(
        ("font_style", "expected_bold", "expected_italic"),
        [
            ("bold", True, False),
            ("italic", False, True),
            ("bold_italic", True, True),
            ("normal", False, False),
        ],
    )
    def test_apply_font_style_variants(
        self,
        font_style: str,
        expected_bold: bool,
        expected_italic: bool,
    ) -> None:
        doc = Document()
        style = doc.styles["Normal"]
        style_op = StyleOp(
            style_name="Normal",
            font_style=font_style,
        )

        apply_styles(doc, [style_op])

        assert style.font.bold is expected_bold
        assert style.font.italic is expected_italic

    def test_missing_style_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        doc = Document()
        style_op = StyleOp(style_name="NonExistentStyle", font_name="Arial")

        with caplog.at_level(logging.WARNING):
            apply_styles(doc, [style_op])

        assert "Style 'NonExistentStyle' not found in document" in caplog.text

    def test_none_values_are_ignored(self) -> None:
        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(12)
        style.font.bold = True
        style.font.italic = False

        style_op = StyleOp(style_name="Normal")

        apply_styles(doc, [style_op])

        assert style.font.name == "Times New Roman"
        assert style.font.size == Pt(12)
        assert style.font.bold is True
        assert style.font.italic is False

    def test_apply_line_spacing(self) -> None:
        doc = Document()
        style = doc.styles["Normal"]
        style_op = StyleOp(style_name="Normal", line_spacing=10.0)

        apply_styles(doc, [style_op])

        assert style.paragraph_format.line_spacing is not None

    def test_apply_mixed_fonts_triggered_by_style_op(self) -> None:
        doc = Document()
        paragraph = doc.add_paragraph("Hello ")
        paragraph.style = doc.styles["Heading 1"]
        run_chinese = paragraph.add_run("中文")
        run_latin = paragraph.add_run("World")

        style_op = StyleOp(
            style_name="Heading 1",
            font_name="BaseFont",
            font_name_chinese="SimSun",
            font_name_latin="Times New Roman",
        )

        apply_styles(doc, [style_op])

        assert run_chinese.font.name == "SimSun"
        assert run_latin.font.name == "Times New Roman"


class TestApplyMixedFontsToStyle:
    """Tests for ``apply_mixed_fonts_to_style``."""

    def test_mixed_chinese_and_latin_fonts(self) -> None:
        doc = Document()
        paragraph = doc.add_paragraph()
        paragraph.style = doc.styles["Heading 1"]
        run_chinese = paragraph.add_run("中文测试")
        run_latin = paragraph.add_run("Latin text")
        run_mixed = paragraph.add_run("中文mixed")

        apply_mixed_fonts_to_style(
            doc,
            style_name="Heading 1",
            chinese_font="SimSun",
            latin_font="Arial",
        )

        assert run_chinese.font.name == "SimSun"
        assert run_latin.font.name == "Arial"
        assert run_mixed.font.name == "SimSun"

    def test_whitespace_runs_unchanged(self) -> None:
        doc = Document()
        paragraph = doc.add_paragraph()
        paragraph.style = doc.styles["Heading 1"]
        run_space = paragraph.add_run("   ")
        run_space.font.name = "OriginalFont"
        run_tab = paragraph.add_run("\t\n")
        run_tab.font.name = "OriginalFont"

        apply_mixed_fonts_to_style(
            doc,
            style_name="Heading 1",
            chinese_font="SimSun",
            latin_font="Arial",
        )

        assert run_space.font.name == "OriginalFont"
        assert run_tab.font.name == "OriginalFont"

    def test_unmatched_style_ignored(self) -> None:
        doc = Document()
        paragraph = doc.add_paragraph("Latin only")
        paragraph.style = doc.styles["Normal"]
        run = paragraph.runs[0]
        run.font.name = "OriginalFont"

        apply_mixed_fonts_to_style(
            doc,
            style_name="Heading 1",
            chinese_font="SimSun",
            latin_font="Arial",
        )

        assert run.font.name == "OriginalFont"

    def test_none_font_skipped(self) -> None:
        doc = Document()
        paragraph = doc.add_paragraph()
        paragraph.style = doc.styles["Heading 1"]
        run_chinese = paragraph.add_run("中文")
        run_chinese.font.name = "OriginalChinese"
        run_latin = paragraph.add_run("Latin")
        run_latin.font.name = "OriginalLatin"

        apply_mixed_fonts_to_style(
            doc,
            style_name="Heading 1",
            chinese_font=None,
            latin_font=None,
        )

        assert run_chinese.font.name == "OriginalChinese"
        assert run_latin.font.name == "OriginalLatin"


def _build_mapping(paths: dict[str, tuple[int, int]]) -> DocxTypstMapping:
    entries: dict[str, MappingEntry] = {}
    path_index: dict[str, str] = {}
    for path, (start, end) in paths.items():
        node_id = NodeID(path=path, full_hash="hash", node_hash="hash")
        entry = MappingEntry(
            node_id=node_id,
            source_start=start,
            source_end=end,
        )
        canonical = node_id.canonical
        entries[canonical] = entry
        path_index[path] = canonical
    return DocxTypstMapping(
        full_hash="hash",
        entries=entries,
        path_index=path_index,
    )


class TestApplyRenumberingHeadings:
    def test_hierarchical_heading_numbering_with_sections(self) -> None:
        doc = Document()
        doc.add_paragraph("Introduction")
        doc.add_paragraph("Background")
        doc.add_paragraph("Methods")
        doc.add_paragraph("Data Collection")

        paths = {
            "doc.children.0[TypstSection].heading[TypstHeading]": (0, 1),
            "doc.children.0[TypstSection].body.0[TypstHeading]": (1, 2),
            "doc.children.1[TypstSection].heading[TypstHeading]": (2, 3),
            "doc.children.1[TypstSection].subsections.0[TypstSection].heading[TypstHeading]": (3, 4),
        }
        mapping = _build_mapping(paths)
        locator = {
            entry.node_id.canonical: entry.source_start
            for entry in mapping.entries.values()
        }

        apply_renumbering(
            doc,
            mapping,
            [RenumberOp(element_type="heading")],
            locator,
        )

        assert doc.paragraphs[0].text == "1 Introduction"
        assert doc.paragraphs[1].text == "1.1 Background"
        assert doc.paragraphs[2].text == "2 Methods"
        assert doc.paragraphs[3].text == "2.1 Data Collection"

    def test_heading_numbering_without_sections(self) -> None:
        doc = Document()
        doc.add_paragraph("Abstract")
        doc.add_paragraph("Overview")

        paths = {
            "doc.children.0[TypstSection].heading[TypstHeading]": (0, 1),
            "doc.children.1[TypstSection].heading[TypstHeading]": (1, 2),
        }
        mapping = _build_mapping(paths)
        locator = {
            entry.node_id.canonical: entry.source_start
            for entry in mapping.entries.values()
        }

        apply_renumbering(
            doc,
            mapping,
            [RenumberOp(element_type="heading")],
            locator,
        )

        assert doc.paragraphs[0].text == "1 Abstract"
        assert doc.paragraphs[1].text == "2 Overview"


class TestApplyRenumberingFiguresAndTables:
    def test_per_section_figure_and_table_numbering(self) -> None:
        doc = Document()
        doc.add_paragraph("Chart One")
        doc.add_paragraph("Table One")
        doc.add_paragraph("Chart Two")
        doc.add_paragraph("Table Two")

        paths = {
            "doc.children.0[TypstSection].body.0[TypstFigure]": (0, 1),
            "doc.children.0[TypstSection].body.1[TypstTable]": (1, 2),
            "doc.children.1[TypstSection].body.0[TypstFigure]": (2, 3),
            "doc.children.1[TypstSection].body.1[TypstTable]": (3, 4),
        }
        mapping = _build_mapping(paths)
        locator = {
            entry.node_id.canonical: entry.source_start
            for entry in mapping.entries.values()
        }

        apply_renumbering(
            doc,
            mapping,
            [
                RenumberOp(element_type="figure"),
                RenumberOp(element_type="table"),
            ],
            locator,
        )

        assert doc.paragraphs[0].text == "Figure 1.1: Chart One"
        assert doc.paragraphs[1].text == "Table 1.1: Table One"
        assert doc.paragraphs[2].text == "Figure 2.1: Chart Two"
        assert doc.paragraphs[3].text == "Table 2.1: Table Two"

    def test_global_numbering_without_sections(self) -> None:
        doc = Document()
        doc.add_paragraph("A figure")
        doc.add_paragraph("A table")
        doc.add_paragraph("Another figure")

        paths = {
            "doc.children.0[TypstSection].body.0[TypstFigure]": (0, 1),
            "doc.children.1[TypstSection].body.0[TypstTable]": (1, 2),
            "doc.children.2[TypstSection].body.0[TypstFigure]": (2, 3),
        }
        mapping = _build_mapping(paths)
        locator = {
            entry.node_id.canonical: entry.source_start
            for entry in mapping.entries.values()
        }

        apply_renumbering(
            doc,
            mapping,
            [
                RenumberOp(element_type="figure"),
                RenumberOp(element_type="table"),
            ],
            locator,
        )

        assert doc.paragraphs[0].text == "Figure 1.1: A figure"
        assert doc.paragraphs[1].text == "Table 2.1: A table"
        assert doc.paragraphs[2].text == "Figure 3.1: Another figure"

    def test_figure_and_table_counters_are_independent(self) -> None:
        doc = Document()
        doc.add_paragraph("First figure")
        doc.add_paragraph("First table")
        doc.add_paragraph("Second figure")
        doc.add_paragraph("Second table")

        paths = {
            "doc.children.0[TypstSection].body.0[TypstFigure]": (0, 1),
            "doc.children.0[TypstSection].body.1[TypstTable]": (1, 2),
            "doc.children.0[TypstSection].body.2[TypstFigure]": (2, 3),
            "doc.children.0[TypstSection].body.3[TypstTable]": (3, 4),
        }
        mapping = _build_mapping(paths)
        locator = {
            entry.node_id.canonical: entry.source_start
            for entry in mapping.entries.values()
        }

        apply_renumbering(
            doc,
            mapping,
            [
                RenumberOp(element_type="figure"),
                RenumberOp(element_type="table"),
            ],
            locator,
        )

        assert doc.paragraphs[0].text == "Figure 1.1: First figure"
        assert doc.paragraphs[1].text == "Table 1.1: First table"
        assert doc.paragraphs[2].text == "Figure 1.2: Second figure"
        assert doc.paragraphs[3].text == "Table 1.2: Second table"


class TestApplyRenumberingEdgeCases:
    def test_empty_renumber_ops_is_noop(self) -> None:
        doc = Document()
        doc.add_paragraph("Unchanged")

        paths = {"doc.children.0[TypstSection].heading[TypstHeading]": (0, 1)}
        mapping = _build_mapping(paths)
        locator = {
            entry.node_id.canonical: entry.source_start
            for entry in mapping.entries.values()
        }

        apply_renumbering(doc, mapping, [], locator)

        assert doc.paragraphs[0].text == "Unchanged"

    def test_mixed_headings_figures_tables(self) -> None:
        doc = Document()
        doc.add_paragraph("Intro")
        doc.add_paragraph("Fig caption")
        doc.add_paragraph("Tab caption")

        paths = {
            "doc.children.0[TypstSection].heading[TypstHeading]": (0, 1),
            "doc.children.0[TypstSection].body.0[TypstFigure]": (1, 2),
            "doc.children.0[TypstSection].body.1[TypstTable]": (2, 3),
        }
        mapping = _build_mapping(paths)
        locator = {
            entry.node_id.canonical: entry.source_start
            for entry in mapping.entries.values()
        }

        apply_renumbering(
            doc,
            mapping,
            [
                RenumberOp(element_type="heading"),
                RenumberOp(element_type="figure"),
                RenumberOp(element_type="table"),
            ],
            locator,
        )

        assert doc.paragraphs[0].text == "1 Intro"
        assert doc.paragraphs[1].text == "Figure 1.1: Fig caption"
        assert doc.paragraphs[2].text == "Table 1.1: Tab caption"
