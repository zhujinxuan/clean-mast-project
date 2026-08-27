"""Tests for enriched section serializer."""

from __future__ import annotations

import pytest
from typst_ir.enriched.serialize_typst import (
    serialize,
    serialize_algebra,
    serialize_block,
    serialize_bullet_list,
    serialize_code_block,
    serialize_equation,
    serialize_figure,
    serialize_heading,
    serialize_ordered_list,
    serialize_paragraph,
    serialize_raw_block,
    serialize_table,
)
from typst_ir.enriched.types import DepthMeta, EnrichedSectionF, EnrichedSectionFFix
from typst_ir.nodes import (
    TypstBulletList,
    TypstCodeBlock,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstRawBlock,
    TypstTable,
)


class TestSerializeParagraph:
    def test_serialize_paragraph(self) -> None:
        block = TypstParagraph(text="Hello world")
        assert serialize_paragraph(block) == "Hello world\n\n"


class TestSerializeTable:
    def test_serialize_table_basic(self) -> None:
        block = TypstTable(
            data=[["1", "2"], ["3", "4"]],
            headers=["A", "B"],
        )
        result = serialize_table(block)
        assert "#table(" in result
        assert "columns: (auto, auto)" in result
        assert "[A]" in result
        assert "[B]" in result
        assert "[1]" in result
        assert "[4]" in result

    def test_serialize_table_with_caption(self) -> None:
        block = TypstTable(
            data=[["x", "y"]],
            headers=["X", "Y"],
            caption="Test Table",
        )
        result = serialize_table(block)
        assert "#figure(" in result
        assert "table(" in result
        assert "caption: [Test Table]" in result

    def test_serialize_table_empty_data_raises(self) -> None:
        block = TypstTable(data=[], headers=["A"])
        with pytest.raises(ValueError, match="Table data cannot be empty"):
            serialize_table(block)

    def test_serialize_table_column_mismatch_raises(self) -> None:
        block = TypstTable(
            data=[["1", "2", "3"]],
            headers=["A", "B"],
        )
        with pytest.raises(ValueError, match="Header column count"):
            serialize_table(block)


class TestSerializeFigure:
    def test_serialize_figure_basic(self) -> None:
        block = TypstFigure(
            content="images/chart.png",
            caption="Wind Speed Chart",
        )
        result = serialize_figure(block)
        assert "#figure(" in result
        assert 'image("images/chart.png", width: 80%)' in result
        assert "caption: [Wind Speed Chart]" in result

    def test_serialize_figure_empty_content_raises(self) -> None:
        block = TypstFigure(content="", caption="Empty")
        with pytest.raises(ValueError, match="Figure content.*cannot be empty"):
            serialize_figure(block)


class TestSerializeEquation:
    def test_serialize_equation_inline(self) -> None:
        block = TypstEquation(latex="E = mc^2", display=False)
        assert serialize_equation(block) == "$E = mc^2$"

    def test_serialize_equation_display(self) -> None:
        # Display math is a block element: trailing blank line so a following
        # heading or figure starts on its own line.
        block = TypstEquation(latex="E = mc^2", display=True)
        assert serialize_equation(block) == "$ E = mc^2 $\n\n"


class TestSerializeCodeBlock:
    def test_serialize_code_block_with_lang(self) -> None:
        block = TypstCodeBlock(text="print('hello')", language="python")
        assert serialize_code_block(block) == '#raw("print(\'hello\')", lang: "python")'

    def test_serialize_code_block_without_lang(self) -> None:
        block = TypstCodeBlock(text="some code")
        assert serialize_code_block(block) == '#raw("some code")'


class TestSerializeRawBlock:
    def test_serialize_raw_block(self) -> None:
        block = TypstRawBlock(text="<html></html>", format="html")
        assert serialize_raw_block(block) == '#raw("<html></html>", format: "html")'


class TestSerializeHeading:
    def test_serialize_heading_depth1(self) -> None:
        block = TypstHeading(text="Title")
        assert serialize_heading(block, 1) == "= Title\n"

    def test_serialize_heading_depth2(self) -> None:
        block = TypstHeading(text="Section")
        assert serialize_heading(block, 2) == "== Section\n"

    def test_serialize_heading_normalized(self) -> None:
        block = TypstHeading(text="Title")
        assert serialize_heading(block, 0) == "= Title\n"


class TestSerializeBulletList:
    def test_serialize_bullet_list(self) -> None:
        block = TypstBulletList(
            items=[
                [TypstParagraph(text="First")],
                [TypstParagraph(text="Second")],
            ]
        )
        result = serialize_bullet_list(block, 1)
        assert result == "- First\n- Second\n"

    def test_serialize_bullet_list_with_heading(self) -> None:
        block = TypstBulletList(
            items=[
                [TypstHeading(text="Item Heading")],
            ]
        )
        result = serialize_bullet_list(block, 2)
        assert result == "- == Item Heading\n"


class TestSerializeOrderedList:
    def test_serialize_ordered_list(self) -> None:
        block = TypstOrderedList(
            items=[
                [TypstParagraph(text="First")],
                [TypstParagraph(text="Second")],
            ]
        )
        result = serialize_ordered_list(block, 1)
        assert result == "+ First\n+ Second\n"

    def test_serialize_ordered_list_start_bug_mirrored(self) -> None:
        block = TypstOrderedList(
            items=[
                [TypstParagraph(text="First")],
            ],
            start=5,
        )
        result = serialize_ordered_list(block, 1)
        assert result == "+ First\n"


class TestSerializeBlock:
    def test_serialize_block_paragraph(self) -> None:
        block = TypstParagraph(text="Hello")
        assert serialize_block(block, 1) == "Hello\n\n"

    def test_serialize_block_heading(self) -> None:
        block = TypstHeading(text="Title")
        assert serialize_block(block, 2) == "== Title\n"

    def test_serialize_block_unknown_type(self) -> None:
        class FakeBlock:
            typst_type = "FakeBlock"

        with pytest.raises(ValueError, match="Unknown block type: FakeBlock"):
            serialize_block(FakeBlock(), 1)  # type: ignore[arg-type]


class TestSerializeAlgebra:
    def test_serialize_algebra_basic(self) -> None:
        layer = EnrichedSectionF(
            meta=DepthMeta(depth=1),
            heading=TypstHeading(text="Section"),
            body=[TypstParagraph(text="Hello")],
            subsections=["== Sub\nSub body\n\n"],
        )
        result = serialize_algebra(layer)
        assert result == "= Section\nHello\n\n== Sub\nSub body\n\n"

    def test_serialize_algebra_nested_depth(self) -> None:
        layer = EnrichedSectionF(
            meta=DepthMeta(depth=3),
            heading=TypstHeading(text="Deep"),
            body=[TypstHeading(text="Body Heading")],
            subsections=[],
        )
        result = serialize_algebra(layer)
        assert result == "=== Deep\n=== Body Heading\n"


class TestSerializeFullTree:
    def test_serialize_full_tree(self) -> None:
        grandchild = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=3),
                heading=TypstHeading(text="Grandchild"),
                body=[TypstParagraph(text="gc body")],
                subsections=[],
            )
        )
        child = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=2),
                heading=TypstHeading(text="Child"),
                body=[TypstParagraph(text="child body")],
                subsections=[grandchild],
            )
        )
        parent = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="Parent"),
                body=[TypstParagraph(text="parent body")],
                subsections=[child],
            )
        )

        result = serialize(parent)
        assert "= Parent\n" in result
        assert "parent body\n\n" in result
        assert "== Child\n" in result
        assert "child body\n\n" in result
        assert "=== Grandchild\n" in result
        assert "gc body\n\n" in result

    def test_serialize_empty_tree(self) -> None:
        tree = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="Lonely"),
                body=[],
                subsections=[],
            )
        )
        result = serialize(tree)
        assert result == "= Lonely\n"
