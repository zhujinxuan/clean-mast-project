"""Tests for Typst IR nodes.

TDD tests for node construction, validation, and immutability.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from typst_ir import (
    TypstBulletList,
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstSection,
    TypstTable,
)


class TestTypstSection:
    """Test TypstSection node construction and behavior."""

    def test_section_construction_with_heading_and_children(self) -> None:
        """Test basic section construction with heading and children."""
        heading = TypstHeading(text="Section Title")
        body = [TypstParagraph(text="First paragraph.")]
        section = TypstSection(heading=heading, body=body, subsections=[])
        
        assert section.heading == heading
        assert section.body == body

    def test_section_with_multiple_children(self) -> None:
        """Test section with multiple child blocks."""
        heading = TypstHeading(text="Section Title")
        body = [
            TypstParagraph(text="First paragraph."),
            TypstParagraph(text="Second paragraph."),
            TypstTable(data=[["a", "b"]], headers=["A", "B"]),
        ]
        section = TypstSection(heading=heading, body=body, subsections=[])
        
        assert len(section.body) == 3
        assert isinstance(section.body[0], TypstParagraph)
        assert isinstance(section.body[2], TypstTable)

    def test_section_with_nested_section(self) -> None:
        """Test section can contain other sections (nesting)."""
        inner_heading = TypstHeading(text="Inner Section")
        inner_section = TypstSection(
            heading=inner_heading,
            body=[TypstParagraph(text="Inner content.")],
            subsections=[]
        )
        
        outer_heading = TypstHeading(text="Outer Section")
        outer_section = TypstSection(
            heading=outer_heading,
            body=[],
            subsections=[inner_section]
        )
        
        assert isinstance(outer_section.subsections[0], TypstSection)
        assert outer_section.subsections[0].heading.text == "Inner Section"

    def test_section_is_frozen(self) -> None:
        """Test that section is immutable (frozen)."""
        section = TypstSection(
            heading=TypstHeading(text="Title"),
            body=[],
            subsections=[],
        )
        
        with pytest.raises(Exception):  # pydantic.ValidationError or similar
            section.heading = TypstHeading(text="New Title")

    def test_section_empty_children_allowed(self) -> None:
        """Test that empty children list is allowed."""
        section = TypstSection(
            heading=TypstHeading(text="Empty Section"),
            body=[],
            subsections=[],
        )
        assert section.body == []
        assert section.subsections == []


class TestTypstBulletList:
    """Test TypstBulletList node construction and behavior."""

    def test_bullet_list_construction_with_items(self) -> None:
        """Test basic bullet list construction with items."""
        items = [
            [TypstParagraph(text="First item")],
            [TypstParagraph(text="Second item")],
        ]
        bullet_list = TypstBulletList(items=items)
        
        assert bullet_list.items == items
        assert len(bullet_list.items) == 2

    def test_bullet_list_with_multiple_blocks_per_item(self) -> None:
        """Test bullet list items with multiple blocks."""
        items = [
            [
                TypstParagraph(text="Item with paragraph."),
                TypstTable(data=[["x"]], headers=["X"]),
            ],
            [TypstParagraph(text="Simple item.")],
        ]
        bullet_list = TypstBulletList(items=items)
        
        assert len(bullet_list.items[0]) == 2
        assert isinstance(bullet_list.items[0][1], TypstTable)

    def test_bullet_list_empty_items_allowed(self) -> None:
        """Test that empty items list is allowed."""
        bullet_list = TypstBulletList(items=[])
        assert bullet_list.items == []

    def test_bullet_list_is_frozen(self) -> None:
        """Test that bullet list is immutable (frozen)."""
        bullet_list = TypstBulletList(items=[[TypstParagraph(text="Item")]])
        
        with pytest.raises(Exception):
            bullet_list.items = []


class TestTypstOrderedList:
    """Test TypstOrderedList node construction and behavior."""

    def test_ordered_list_construction_with_items(self) -> None:
        """Test basic ordered list construction with items."""
        items = [
            [TypstParagraph(text="First item")],
            [TypstParagraph(text="Second item")],
        ]
        ordered_list = TypstOrderedList(items=items)
        
        assert ordered_list.items == items
        assert len(ordered_list.items) == 2
        assert ordered_list.start == 1  # Default value

    def test_ordered_list_with_custom_start(self) -> None:
        """Test ordered list with non-default start value."""
        items = [[TypstParagraph(text="Item")]]
        ordered_list = TypstOrderedList(items=items, start=5)
        
        assert ordered_list.start == 5

    def test_ordered_list_with_multiple_blocks_per_item(self) -> None:
        """Test ordered list items with multiple blocks."""
        items = [
            [
                TypstParagraph(text="Item with details."),
                TypstFigure(content="img.png", caption="Figure caption"),
            ],
        ]
        ordered_list = TypstOrderedList(items=items)
        
        assert len(ordered_list.items[0]) == 2
        assert isinstance(ordered_list.items[0][1], TypstFigure)

    def test_ordered_list_empty_items_allowed(self) -> None:
        """Test that empty items list is allowed."""
        ordered_list = TypstOrderedList(items=[])
        assert ordered_list.items == []
        assert ordered_list.start == 1  # Default still applies

    def test_ordered_list_is_frozen(self) -> None:
        """Test that ordered list is immutable (frozen)."""
        ordered_list = TypstOrderedList(items=[[TypstParagraph(text="Item")]], start=1)
        
        with pytest.raises(Exception):
            ordered_list.start = 10


class TestNodeIntegration:
    """Test interactions between different node types."""

    def test_section_can_contain_lists(self) -> None:
        """Test that sections can contain bullet and ordered lists."""
        bullet_list = TypstBulletList(
            items=[[TypstParagraph(text="Bullet item")]]
        )
        ordered_list = TypstOrderedList(
            items=[[TypstParagraph(text="Ordered item")]]
        )
        
        section = TypstSection(
            heading=TypstHeading(text="Lists Section"),
            body=[bullet_list, ordered_list],
            subsections=[]
        )
        
        assert isinstance(section.body[0], TypstBulletList)
        assert isinstance(section.body[1], TypstOrderedList)

    def test_document_can_contain_sections(self) -> None:
        """Test that documents can contain sections as children."""
        section = TypstSection(
            heading=TypstHeading(text="Doc Section"),
            body=[TypstParagraph(text="Content.")],
            subsections=[]
        )

        doc = TypstDocument(children=[section])
        assert isinstance(doc.children[0], TypstSection)

    def test_document_rejects_non_section_children(self) -> None:
        """Test that documents reject non-section children with ValidationError."""
        with pytest.raises(ValidationError):
            TypstDocument(children=[TypstParagraph(text="x")])

    def test_nested_document_structure(self) -> None:
        """Test complex nested document with sections and lists."""
        inner_section = TypstSection(
            heading=TypstHeading(text="Inner"),
            body=[TypstBulletList(items=[[TypstParagraph(text="Bullet")]])],
            subsections=[]
        )
        
        outer_section = TypstSection(
            heading=TypstHeading(text="Outer"),
            body=[
                TypstParagraph(text="Intro."),
                TypstOrderedList(items=[[TypstParagraph(text="Step 1")]]),
            ],
            subsections=[inner_section]
        )
        
        doc = TypstDocument(children=[outer_section])
        
        assert len(doc.children) == 1
        assert len(outer_section.body) == 2
        assert isinstance(outer_section.subsections[0], TypstSection)


class TestTypstEquation:
    """Test TypstEquation node construction and behavior."""

    def test_equation_construction_inline(self) -> None:
        """Test basic equation construction (inline by default)."""
        from typst_ir.nodes import TypstEquation
        
        eq = TypstEquation(latex="E = mc^2")
        
        assert eq.latex == "E = mc^2"
        assert eq.display is False  # Default is inline

    def test_equation_construction_display(self) -> None:
        """Test display equation construction."""
        from typst_ir.nodes import TypstEquation
        
        eq = TypstEquation(latex="\\int_0^\\infty e^{-x} dx = 1", display=True)
        
        assert eq.latex == "\\int_0^\\infty e^{-x} dx = 1"
        assert eq.display is True

    def test_equation_is_frozen(self) -> None:
        """Test that equation is immutable (frozen)."""
        from typst_ir.nodes import TypstEquation
        
        eq = TypstEquation(latex="x^2 + y^2 = r^2")
        
        with pytest.raises(Exception):
            eq.latex = "new equation"

    def test_equation_complex_latex(self) -> None:
        """Test equation with complex LaTeX content."""
        from typst_ir.nodes import TypstEquation
        
        latex = "\\frac{\\partial u}{\\partial t} = \\alpha \\nabla^2 u"
        eq = TypstEquation(latex=latex, display=True)
        
        assert eq.latex == latex
        assert eq.display is True


class TestTypstCodeBlock:
    """Test TypstCodeBlock node construction and behavior."""

    def test_code_block_construction_with_language(self) -> None:
        """Test code block construction with language specified."""
        from typst_ir.nodes import TypstCodeBlock
        
        code = TypstCodeBlock(text="print('hello')", language="python")
        
        assert code.text == "print('hello')"
        assert code.language == "python"

    def test_code_block_construction_without_language(self) -> None:
        """Test code block construction without language (None default)."""
        from typst_ir.nodes import TypstCodeBlock
        
        code = TypstCodeBlock(text="some raw text")
        
        assert code.text == "some raw text"
        assert code.language is None

    def test_code_block_is_frozen(self) -> None:
        """Test that code block is immutable (frozen)."""
        from typst_ir.nodes import TypstCodeBlock
        
        code = TypstCodeBlock(text="original", language="julia")
        
        with pytest.raises(Exception):
            code.text = "modified"

    def test_code_block_multiline(self) -> None:
        """Test code block with multiline text."""
        from typst_ir.nodes import TypstCodeBlock
        
        text = "line 1\\nline 2\\nline 3"
        code = TypstCodeBlock(text=text, language="python")
        
        assert code.text == text
        assert code.language == "python"


class TestTypstRawBlock:
    """Test TypstRawBlock node construction and behavior."""

    def test_raw_block_construction(self) -> None:
        """Test raw block construction with format and text."""
        from typst_ir.nodes import TypstRawBlock
        
        raw = TypstRawBlock(format="html", text="<p>Hello</p>")
        
        assert raw.format == "html"
        assert raw.text == "<p>Hello</p>"

    def test_raw_block_with_different_formats(self) -> None:
        """Test raw block with various format types."""
        from typst_ir.nodes import TypstRawBlock
        
        formats = ["html", "xml", "markdown", "latex"]
        for fmt in formats:
            raw = TypstRawBlock(format=fmt, text=f"content in {fmt}")
            assert raw.format == fmt
            assert raw.text == f"content in {fmt}"

    def test_raw_block_is_frozen(self) -> None:
        """Test that raw block is immutable (frozen)."""
        from typst_ir.nodes import TypstRawBlock
        
        raw = TypstRawBlock(format="html", text="<div></div>")
        
        with pytest.raises(Exception):
            raw.format = "xml"

    def test_raw_block_empty_text(self) -> None:
        """Test raw block with empty text."""
        from typst_ir.nodes import TypstRawBlock
        
        raw = TypstRawBlock(format="json", text="")
        
        assert raw.format == "json"
        assert raw.text == ""


class TestNewNodeIntegration:
    """Test integration of new nodes with existing document structure."""

    def test_section_can_contain_new_nodes(self) -> None:
        """Test that sections can contain equation, code, and raw blocks."""
        from typst_ir.nodes import TypstCodeBlock, TypstEquation, TypstRawBlock
        
        section = TypstSection(
            heading=TypstHeading(text="Mixed Content"),
            body=[
                TypstParagraph(text="Introduction."),
                TypstEquation(latex="a^2 + b^2 = c^2"),
                TypstCodeBlock(text="x = 1 + 2", language="python"),
                TypstRawBlock(format="html", text="<br>"),
            ],
            subsections=[]
        )
        
        assert isinstance(section.body[1], TypstEquation)
        assert isinstance(section.body[2], TypstCodeBlock)
        assert isinstance(section.body[3], TypstRawBlock)

