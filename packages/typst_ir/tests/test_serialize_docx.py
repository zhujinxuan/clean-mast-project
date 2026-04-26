"""Tests for DOCX-specific enriched section serializer.

Verifies that ``serialize_docx_algebra``, ``serialize_table_with_index``,
and ``serialize_figure_with_index`` produce correct Typst markup with
cross-reference markers and indexed captions.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from typst_ir import (
    TypstBulletList,
    TypstCodeBlock,
    TypstDocument,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstRawBlock,
    TypstSection,
    TypstTable,
)
from typst_ir.enriched.cata import cata_enriched
from typst_ir.enriched.docx_types import DocxMeta, EnrichedBlock
from typst_ir.enriched.enrich_docx import enrich_with_docx_meta
from typst_ir.enriched.enrich_path import enrich_with_path
from typst_ir.enriched.serialize_docx import (
    draft_docx,
    serialize_docx_algebra,
    serialize_figure_with_index,
    serialize_table_with_index,
)
from typst_ir.enriched.types import EnrichedSectionF


class TestSerializeTableWithIndex:
    """Unit tests for ``serialize_table_with_index``."""

    def test_basic_table_with_caption(self) -> None:
        table = TypstTable(
            data=[["1", "2"], ["3", "4"]],
            headers=["A", "B"],
            caption="Test Table",
        )
        result = serialize_table_with_index(table, "1.2-1")
        assert "#figure(" in result
        assert "[A]" in result
        assert "caption: [表(1.2-1) Test Table]" in result
        assert "table(" in result

    def test_table_without_caption(self) -> None:
        table = TypstTable(
            data=[["x", "y"]],
            headers=["X", "Y"],
        )
        result = serialize_table_with_index(table, "1-1")
        assert "#table(" in result
        assert "表" not in result

    def test_empty_data_raises(self) -> None:
        table = TypstTable(data=[], headers=["A"])
        with pytest.raises(ValueError, match="Table data cannot be empty"):
            serialize_table_with_index(table, "1-1")

    def test_column_mismatch_raises(self) -> None:
        table = TypstTable(data=[["1", "2", "3"]], headers=["A", "B"])
        with pytest.raises(ValueError, match="Header column count"):
            serialize_table_with_index(table, "1-1")


class TestSerializeFigureWithIndex:
    """Unit tests for ``serialize_figure_with_index``."""

    def test_basic_figure(self) -> None:
        figure = TypstFigure(content="img.png", caption="A figure")
        result = serialize_figure_with_index(figure, "2.1-1")
        assert "#figure(" in result
        assert 'image("img.png", width: 80%)' in result
        assert "caption: [图(2.1-1) A figure]" in result

    def test_empty_content_raises(self) -> None:
        figure = TypstFigure(content="", caption="Empty")
        with pytest.raises(ValueError, match="Figure content.*cannot be empty"):
            serialize_figure_with_index(figure, "1-1")


class TestSerializeDocxAlgebra:
    """Unit tests for ``serialize_docx_algebra``."""

    def test_section_markers(self) -> None:
        """Section gets irstart/irend markers with path-based ID."""
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Intro"),
            body=[],
            subsections=[],
        )
        result = serialize_docx_algebra(layer)
        assert '#raw("irstart:section0")' in result
        assert '#raw("irend:section0")' in result
        assert "= 1 Intro" in result

    def test_block_markers(self) -> None:
        """Each body block gets irstart/irend markers."""
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Intro"),
            body=[
                EnrichedBlock(
                    block=TypstParagraph(text="Hello"),
                    meta=DocxMeta(
                        depth=2, path=[("section", 0), ("body", 0)], section_index="1"
                    ),
                ),
            ],
            subsections=[],
        )
        result = serialize_docx_algebra(layer)
        assert '#raw("irstart:section0body0")' in result
        assert '#raw("irend:section0body0")' in result
        assert "Hello" in result

    def test_table_with_index(self) -> None:
        """Tables get serialized with 表 caption."""
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Data"),
            body=[
                EnrichedBlock(
                    block=TypstTable(
                        data=[["a"]],
                        headers=["H"],
                        caption="My Table",
                    ),
                    meta=DocxMeta(
                        depth=3,
                        path=[("section", 0), ("body", 0), ("table", 0)],
                        section_index="1",
                        table_index="1-1",
                    ),
                ),
            ],
            subsections=[],
        )
        result = serialize_docx_algebra(layer)
        assert '#raw("irstart:section0body0table0")' in result
        assert '#raw("irend:section0body0table0")' in result
        assert "caption: [表(1-1) My Table]" in result
        assert "#figure(" in result

    def test_figure_with_index(self) -> None:
        """Figures get serialized with 图 caption."""
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Charts"),
            body=[
                EnrichedBlock(
                    block=TypstFigure(content="chart.png", caption="My Figure"),
                    meta=DocxMeta(
                        depth=3,
                        path=[("section", 0), ("body", 0), ("figure", 0)],
                        section_index="1",
                        figure_index="1-1",
                    ),
                ),
            ],
            subsections=[],
        )
        result = serialize_docx_algebra(layer)
        assert '#raw("irstart:section0body0figure0")' in result
        assert '#raw("irend:section0body0figure0")' in result
        assert "caption: [图(1-1) My Figure]" in result
        assert result.count("图(1-1) My Figure") == 1

    def test_nested_sections(self) -> None:
        """Subsections are inserted between section markers."""
        child_layer = EnrichedSectionF(
            meta=DocxMeta(
                depth=2, path=[("section", 0), ("section", 0)], section_index="1.1"
            ),
            heading=TypstHeading(text="Child"),
            body=[],
            subsections=[],
        )
        parent_layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Parent"),
            body=[],
            subsections=[serialize_docx_algebra(child_layer)],
        )
        result = serialize_docx_algebra(parent_layer)
        assert '#raw("irstart:section0")' in result
        assert "= 1 Parent" in result
        assert '#raw("irstart:section0section0")' in result
        assert "= 1.1 Child" in result
        assert '#raw("irend:section0section0")' in result
        assert '#raw("irend:section0")' in result

    def test_list_atomic(self) -> None:
        """List block gets markers but is not traversed for internal markers."""
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="List"),
            body=[
                EnrichedBlock(
                    block=TypstBulletList(items=[[TypstParagraph(text="Item")]]),
                    meta=DocxMeta(
                        depth=2, path=[("section", 0), ("body", 0)], section_index="1"
                    ),
                ),
            ],
            subsections=[],
        )
        result = serialize_docx_algebra(layer)
        assert '#raw("irstart:section0body0")' in result
        assert '#raw("irend:section0body0")' in result
        assert "- Item" in result
        assert result.count("irstart:") == 3
        assert result.count("irend:") == 3

    def test_equation_code_raw_blocks(self) -> None:
        """Equations, code blocks, and raw blocks get markers."""
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Blocks"),
            body=[
                EnrichedBlock(
                    block=TypstEquation(latex="E = mc^2", display=True),
                    meta=DocxMeta(
                        depth=2, path=[("section", 0), ("body", 0)], section_index="1"
                    ),
                ),
                EnrichedBlock(
                    block=TypstCodeBlock(text="print(1)", language="python"),
                    meta=DocxMeta(
                        depth=2, path=[("section", 0), ("body", 1)], section_index="1"
                    ),
                ),
                EnrichedBlock(
                    block=TypstRawBlock(format="html", text="<b>bold</b>"),
                    meta=DocxMeta(
                        depth=2, path=[("section", 0), ("body", 2)], section_index="1"
                    ),
                ),
            ],
            subsections=[],
        )
        result = serialize_docx_algebra(layer)
        assert "$ E = mc^2 $" in result
        assert 'lang: "python"' in result
        assert 'format: "html"' in result

    def test_table_missing_index_raises(self) -> None:
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Data"),
            body=[
                EnrichedBlock(
                    block=TypstTable(data=[["a"]], headers=["H"], caption="T"),
                    meta=DocxMeta(
                        depth=2,
                        path=[("section", 0), ("body", 0)],
                        section_index="1",
                        table_index=None,
                    ),
                ),
            ],
            subsections=[],
        )
        with pytest.raises(ValueError, match="missing table_index"):
            serialize_docx_algebra(layer)

    def test_figure_missing_index_raises(self) -> None:
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Charts"),
            body=[
                EnrichedBlock(
                    block=TypstFigure(content="img.png", caption="F"),
                    meta=DocxMeta(
                        depth=2,
                        path=[("section", 0), ("body", 0)],
                        section_index="1",
                        figure_index=None,
                    ),
                ),
            ],
            subsections=[],
        )
        with pytest.raises(ValueError, match="missing figure_index"):
            serialize_docx_algebra(layer)

    def test_unknown_block_type_raises(self) -> None:
        from unittest.mock import MagicMock

        fake_block = MagicMock()
        fake_block.typst_type = "FakeBlock"
        enriched = EnrichedBlock(
            block=TypstParagraph(text="placeholder"),
            meta=DocxMeta(
                depth=2, path=[("section", 0), ("body", 0)], section_index="1"
            ),
        )
        object.__setattr__(enriched, "block", fake_block)
        layer = EnrichedSectionF(
            meta=DocxMeta(depth=1, path=[("section", 0)], section_index="1"),
            heading=TypstHeading(text="Data"),
            body=[enriched],
            subsections=[],
        )
        with pytest.raises(ValueError, match="Unknown block type"):
            serialize_docx_algebra(layer)


class TestSerializeDocxIntegration:
    """Integration tests using full enrichment pipeline."""

    def test_via_cata_with_enriched_docx(self) -> None:
        """End-to-end: enrich -> cata with serialize_docx_algebra."""
        root = TypstSection(
            heading=TypstHeading(text="Report"),
            body=[
                TypstParagraph(text="Introduction."),
                TypstTable(data=[["a"]], headers=["H"], caption="T1"),
                TypstFigure(content="fig.png", caption="F1"),
            ],
            subsections=[
                TypstSection(
                    heading=TypstHeading(text="Sub"),
                    body=[TypstParagraph(text="Sub content.")],
                    subsections=[],
                ),
            ],
        )
        path_enriched = enrich_with_path(root)
        docx_enriched = enrich_with_docx_meta(path_enriched)

        result = cata_enriched(docx_enriched, serialize_docx_algebra)

        assert '#raw("irstart:section0")' in result
        assert '#raw("irend:section0")' in result
        assert "= 1 Report" in result
        assert '#raw("irstart:section0body0")' in result
        assert "Introduction." in result
        assert "caption: [表(1-1) T1]" in result
        assert "caption: [图(1-1) F1]" in result
        assert "= 1.1 Sub" in result
        assert "Sub content." in result


def test_draft_docx_integration(tmp_path: Path) -> None:
    """End-to-end: JSON -> enriched Typst -> PDF -> DOCX with markers."""
    doc = TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="Test"),
                body=[TypstParagraph(text="Hello")],
                subsections=[],
            )
        ]
    )
    json_path = tmp_path / "input.json"
    json_path.write_text(doc.model_dump_json(), encoding="utf-8")

    result = draft_docx(json_path)

    assert result.exists()
    assert result.suffix == ".docx"
    assert result.name == "input_draft.docx"
    with zipfile.ZipFile(result) as zf:
        xml = zf.read("word/document.xml").decode()
    assert "irstart:" in xml


def test_multiple_top_level_sections(tmp_path: Path) -> None:
    """draft_docx generates unique section IDs for multiple top-level sections."""
    doc = TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="First Section"),
                body=[TypstParagraph(text="Content of first section.")],
                subsections=[],
            ),
            TypstSection(
                heading=TypstHeading(text="Second Section"),
                body=[TypstParagraph(text="Content of second section.")],
                subsections=[],
            ),
            TypstSection(
                heading=TypstHeading(text="Third Section"),
                body=[TypstParagraph(text="Content of third section.")],
                subsections=[],
            ),
        ]
    )
    json_path = tmp_path / "multi_section.json"
    json_path.write_text(doc.model_dump_json(), encoding="utf-8")

    result = draft_docx(json_path)

    assert result.exists()
    assert result.suffix == ".docx"
    with zipfile.ZipFile(result) as zf:
        xml = zf.read("word/document.xml").decode()

    # Unique section markers
    assert "irstart:section0" in xml
    assert "irstart:section1" in xml
    assert "irstart:section2" in xml

    # Unique heading markers
    assert "irstart:section0heading0" in xml
    assert "irstart:section1heading0" in xml
    assert "irstart:section2heading0" in xml


def test_draft_docx_missing_input() -> None:
    """Missing input file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        draft_docx(Path("/nonexistent/path/input.json"))
