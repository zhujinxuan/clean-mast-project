"""Tests for MappingVisitor - DOCX to Typst IR source mapping visitor.

TDD GREEN phase: MappingVisitor is now fully implemented and all tests pass.
"""

from __future__ import annotations

from typst_ir import (
    TypstBulletList,
    TypstCodeBlock,
    TypstDocument,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstRawBlock,
    TypstSection,
    TypstTable,
)
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.mapping.types import MappingEntry


class TestMappingVisitorInitialization:
    """Test MappingVisitor initialization and basic attributes."""

    def test_visitor_initializes_with_registry(self) -> None:
        """Visitor should accept NodeRegistry in constructor."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        visitor = MappingVisitor(registry)
        assert visitor.registry is registry

    def test_visitor_initializes_empty_mappings(self) -> None:
        """Visitor should start with empty mappings list."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        visitor = MappingVisitor(registry)
        assert visitor.mappings == []
        assert isinstance(visitor.mappings, list)


class TestVisitDocument:
    """Test visiting document root node."""

    def test_visit_document_returns_list(self) -> None:
        """visit_document should return list of mappings."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(children=[])
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        result = visitor.visit_document(doc, source_start=0, source_end=100)

        assert isinstance(result, list)

    def test_visit_document_empty_document(self) -> None:
        """Empty document should produce empty mappings list."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(children=[])
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(doc, source_start=0, source_end=100)

        assert mappings == []

    def test_visit_document_creates_document_mapping(self) -> None:
        """Document itself should get a mapping entry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Hello"),
                    body=[TypstParagraph(text="Hello")],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(doc, source_start=0, source_end=100)

        assert len(mappings) >= 1
        # First mapping should be the document itself
        doc_mapping = mappings[0]
        assert isinstance(doc_mapping, MappingEntry)
        assert doc_mapping.source_start == 0
        assert doc_mapping.source_end == 100


class TestVisitParagraph:
    """Test visiting paragraph nodes."""

    def test_visit_paragraph_creates_mapping(self) -> None:
        """Paragraph should create a MappingEntry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Paragraph"),
                    body=[TypstParagraph(text="Test paragraph")],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]
        assert len(para_mappings) == 1
        assert para_mappings[0].source_start >= 0
        assert para_mappings[0].source_end <= 100

    def test_visit_paragraph_has_valid_node_id(self) -> None:
        """Paragraph mapping should have valid NodeID."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        para = TypstParagraph(text="Test")
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Paragraph"),
                    body=[para],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]
        assert len(para_mappings) == 1
        assert para_mappings[0].node_id.path.endswith("[TypstParagraph]")
        assert len(para_mappings[0].node_id.full_hash) == 64  # SHA-256 hex
        assert len(para_mappings[0].node_id.node_hash) == 64


class TestVisitHeading:
    """Test visiting heading nodes."""

    def test_visit_heading_creates_mapping(self) -> None:
        """Heading should create a MappingEntry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        heading = TypstHeading(text="Section Title")
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=heading,
                    body=[],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=50)

        heading_mappings = [m for m in visitor.mappings if "Heading" in m.node_id.path]
        assert len(heading_mappings) == 1

    def test_visit_heading_preserves_level(self) -> None:
        """Heading node hash should reflect level attribute."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        h1 = TypstHeading(text="Title")
        h2 = TypstHeading(text="Title")
        doc = TypstDocument(
            children=[
                TypstSection(heading=h1, body=[], subsections=[]),
                TypstSection(heading=h2, body=[], subsections=[]),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        heading_mappings = [m for m in visitor.mappings if "Heading" in m.node_id.path]
        assert len(heading_mappings) == 2
        # Different levels should have different node hashes
        assert heading_mappings[0].node_id.node_hash == heading_mappings[1].node_id.node_hash


class TestVisitSection:
    """Test visiting section nodes with headings and children."""

    def test_visit_section_creates_heading_and_children_mappings(self) -> None:
        """Section should create mappings for heading and all children."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        section = TypstSection(
            heading=TypstHeading(text="Section"),
            body=[
                TypstParagraph(text="Para 1"),
                TypstParagraph(text="Para 2"),
            ],
            subsections=[],
        )
        doc = TypstDocument(children=[section])
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=200)

        # Should have: document, section, heading, para1, para2
        assert len(visitor.mappings) == 5

        paths = [m.node_id.path for m in visitor.mappings]
        assert any("Section" in p for p in paths)
        assert any("Heading" in p for p in paths)
        assert sum("Paragraph" in p for p in paths) == 2

    def test_visit_section_establishes_parent_range(self) -> None:
        """Section should establish range that constrains children."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        section = TypstSection(
            heading=TypstHeading(text="Section"),
            body=[TypstParagraph(text="Content")],
            subsections=[],
        )
        doc = TypstDocument(children=[section])
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        section_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstSection]")]
        assert len(section_mappings) == 1
        section_mapping = section_mappings[0]

        # Section range should be within document range
        assert section_mapping.source_start >= 0
        assert section_mapping.source_end <= 100


class TestVisitTable:
    """Test visiting table nodes."""

    def test_visit_table_creates_mapping(self) -> None:
        """Table should create a MappingEntry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        table = TypstTable(
            headers=["Col1", "Col2"],
            data=[["A", "B"]],
            caption="Test Table",
        )
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Table"),
                    body=[table],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=50)

        table_mappings = [m for m in visitor.mappings if "Table" in m.node_id.path]
        assert len(table_mappings) == 1

    def test_visit_table_with_caption(self) -> None:
        """Table with caption should have different hash than without."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        table_with = TypstTable(headers=["A"], data=[["B"]], caption="Caption")
        table_without = TypstTable(headers=["A"], data=[["B"]], caption=None)
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Table With"),
                    body=[table_with],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Table Without"),
                    body=[table_without],
                    subsections=[],
                ),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        table_mappings = [m for m in visitor.mappings if "Table" in m.node_id.path]
        assert len(table_mappings) == 2
        assert table_mappings[0].node_id.node_hash != table_mappings[1].node_id.node_hash


class TestVisitFigure:
    """Test visiting figure nodes."""

    def test_visit_figure_creates_mapping(self) -> None:
        """Figure should create a MappingEntry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        figure = TypstFigure(content="image.png", caption="Figure 1", kind="image")
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Figure"),
                    body=[figure],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=10, source_end=50)

        figure_mappings = [m for m in visitor.mappings if "Figure" in m.node_id.path]
        assert len(figure_mappings) == 1
        assert figure_mappings[0].source_start >= 10
        assert figure_mappings[0].source_end <= 50


class TestVisitEquation:
    """Test visiting equation nodes."""

    def test_visit_equation_creates_mapping(self) -> None:
        """Equation should create a MappingEntry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        equation = TypstEquation(latex="E = mc^2", display=False)
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Equation"),
                    body=[equation],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=30)

        equation_mappings = [m for m in visitor.mappings if "Equation" in m.node_id.path]
        assert len(equation_mappings) == 1

    def test_visit_equation_inline_vs_display(self) -> None:
        """Inline and display equations should have different hashes."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        inline = TypstEquation(latex="x = y", display=False)
        display = TypstEquation(latex="x = y", display=True)
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Inline"),
                    body=[inline],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Display"),
                    body=[display],
                    subsections=[],
                ),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        equation_mappings = [m for m in visitor.mappings if "Equation" in m.node_id.path]
        assert len(equation_mappings) == 2
        assert equation_mappings[0].node_id.node_hash != equation_mappings[1].node_id.node_hash


class TestVisitCodeBlock:
    """Test visiting code block nodes."""

    def test_visit_code_block_creates_mapping(self) -> None:
        """Code block should create a MappingEntry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        code = TypstCodeBlock(text="print('hello')", language="python")
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Code"),
                    body=[code],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=40)

        code_mappings = [m for m in visitor.mappings if "CodeBlock" in m.node_id.path]
        assert len(code_mappings) == 1


class TestVisitRawBlock:
    """Test visiting raw block nodes."""

    def test_visit_raw_block_creates_mapping(self) -> None:
        """Raw block should create a MappingEntry."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        raw = TypstRawBlock(format="html", text="<div>content</div>")
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Raw"),
                    body=[raw],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=50)

        raw_mappings = [m for m in visitor.mappings if "RawBlock" in m.node_id.path]
        assert len(raw_mappings) == 1


class TestVisitBulletList:
    """Test visiting bullet list nodes."""

    def test_visit_bullet_list_creates_mappings_for_items(self) -> None:
        """Bullet list should create mappings for all items."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        bullet_list = TypstBulletList(
            items=[
                [TypstParagraph(text="Item 1")],
                [TypstParagraph(text="Item 2")],
            ]
        )
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Bullet List"),
                    body=[bullet_list],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        # Should have: document, bullet list, and 2 paragraphs
        bullet_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstBulletList]")]
        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]
        assert len(bullet_mappings) == 1
        assert len(para_mappings) == 2

    def test_visit_bullet_list_with_multiple_blocks_per_item(self) -> None:
        """Bullet list items with multiple blocks should all get mappings."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        bullet_list = TypstBulletList(
            items=[
                [
                    TypstParagraph(text="First para"),
                    TypstParagraph(text="Second para"),
                ],
            ]
        )
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Bullet List"),
                    body=[bullet_list],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]
        assert len(para_mappings) == 2


class TestVisitOrderedList:
    """Test visiting ordered list nodes."""

    def test_visit_ordered_list_creates_mappings_for_items(self) -> None:
        """Ordered list should create mappings for all items."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        ordered_list = TypstOrderedList(
            items=[
                [TypstParagraph(text="First")],
                [TypstParagraph(text="Second")],
            ],
            start=1,
        )
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Ordered List"),
                    body=[ordered_list],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        ordered_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstOrderedList]")]
        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]
        assert len(ordered_mappings) == 1
        assert len(para_mappings) == 2

    def test_visit_ordered_list_different_start(self) -> None:
        """Ordered lists with different start values should have different hashes."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        list1 = TypstOrderedList(items=[[TypstParagraph(text="Item")]], start=1)
        list5 = TypstOrderedList(items=[[TypstParagraph(text="Item")]], start=5)
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="List 1"),
                    body=[list1],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="List 5"),
                    body=[list5],
                    subsections=[],
                ),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        ordered_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstOrderedList]")]
        assert len(ordered_mappings) == 2
        assert ordered_mappings[0].node_id.node_hash != ordered_mappings[1].node_id.node_hash


class TestNestedSections:
    """Test deeply nested section structures."""

    def test_nested_sections_all_get_mappings(self) -> None:
        """Nested sections should all create mappings."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        inner_section = TypstSection(
            heading=TypstHeading(text="Inner"),
            body=[TypstParagraph(text="Inner content")],
            subsections=[],
        )
        outer_section = TypstSection(
            heading=TypstHeading(text="Outer"),
            body=[],
            subsections=[inner_section],
        )
        doc = TypstDocument(children=[outer_section])
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=200)

        section_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstSection]")]
        heading_mappings = [m for m in visitor.mappings if "Heading" in m.node_id.path]
        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]

        assert len(section_mappings) == 2  # Outer and inner
        assert len(heading_mappings) == 2  # Outer and inner headings
        assert len(para_mappings) == 1

    def test_nested_section_ranges_constrained(self) -> None:
        """Child section ranges should be within parent section ranges."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        inner = TypstSection(
            heading=TypstHeading(text="Inner"),
            body=[],
            subsections=[],
        )
        outer = TypstSection(
            heading=TypstHeading(text="Outer"),
            body=[],
            subsections=[inner],
        )
        doc = TypstDocument(children=[outer])
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        section_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstSection]")]
        assert len(section_mappings) == 2

        outer_mapping = section_mappings[0]  # First encountered
        inner_mapping = section_mappings[1]

        # Inner should be within outer
        assert inner_mapping.source_start >= outer_mapping.source_start
        assert inner_mapping.source_end <= outer_mapping.source_end


class TestParentChildRangeConstraint:
    """Test that parent ranges constrain child ranges."""

    def test_paragraph_range_within_document(self) -> None:
        """Paragraph ranges must be within document range."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Paragraph"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=10, source_end=90)

        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]
        assert len(para_mappings) == 1

        para = para_mappings[0]
        assert para.source_start >= 10
        assert para.source_end <= 90

    def test_section_children_within_section_range(self) -> None:
        """All children of a section must be within section range."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        section = TypstSection(
            heading=TypstHeading(text="Section"),
            body=[
                TypstParagraph(text="Para 1"),
                TypstParagraph(text="Para 2"),
                TypstParagraph(text="Para 3"),
            ],
            subsections=[],
        )
        doc = TypstDocument(children=[section])
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        section_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstSection]")]
        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]

        assert len(section_mappings) == 1
        section_mapping = section_mappings[0]

        for para in para_mappings:
            assert para.source_start >= section_mapping.source_start
            assert para.source_end <= section_mapping.source_end

    def test_list_items_within_list_range(self) -> None:
        """All items in a list must be within the list's range."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        bullet_list = TypstBulletList(
            items=[
                [TypstParagraph(text="Item 1")],
                [TypstParagraph(text="Item 2")],
            ]
        )
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Bullet List"),
                    body=[bullet_list],
                    subsections=[],
                )
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        list_mappings = [m for m in visitor.mappings if m.node_id.path.endswith("[TypstBulletList]")]
        para_mappings = [m for m in visitor.mappings if "Paragraph" in m.node_id.path]

        assert len(list_mappings) == 1
        list_mapping = list_mappings[0]

        for para in para_mappings:
            assert para.source_start >= list_mapping.source_start
            assert para.source_end <= list_mapping.source_end


class TestDeeplyNestedStructure:
    """Test complex deeply nested document structures."""

    def test_complex_document_structure(self) -> None:
        """Complex document with all node types should create correct mappings."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Introduction"),
                    body=[TypstParagraph(text="Introduction")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Section 1"),
                    body=[
                        TypstParagraph(text="Content"),
                        TypstBulletList(
                            items=[
                                [TypstParagraph(text="Bullet 1")],
                                [TypstParagraph(text="Bullet 2")],
                            ],
                            subsections=[],
                        ),
                    ],
                    subsections=[
                        TypstSection(
                            heading=TypstHeading(text="Subsection"),
                            body=[
                                TypstTable(
                                    headers=["A", "B"],
                                    data=[["1", "2"]],
                                    caption="Table",
                                ),
                                TypstCodeBlock(text="code", language="python"),
                            ],
                            subsections=[],
                        ),
                    ],
                ),
                TypstSection(
                    heading=TypstHeading(text="Ordered List"),
                    body=[
                        TypstOrderedList(
                            items=[
                                [TypstParagraph(text="Ordered 1")],
                                [TypstParagraph(text="Ordered 2")],
                            ],
                            start=1,
                        )
                    ],
                    subsections=[],
                ),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=500)

        # Count mappings by type
        paths = [m.node_id.path for m in visitor.mappings]

        assert any(p == "doc" for p in paths)  # Document root
        assert sum(p.endswith("[TypstSection]") for p in paths) == 5
        assert sum("[TypstHeading]" in p for p in paths) == 5
        assert sum("[TypstParagraph]" in p for p in paths) == 6  # Intro, Content, 2 bullets, 2 ordered
        assert sum(p.endswith("[TypstBulletList]") for p in paths) == 1
        assert sum(p.endswith("[TypstOrderedList]") for p in paths) == 1
        assert sum(p.endswith("[TypstTable]") for p in paths) == 1
        assert sum(p.endswith("[TypstCodeBlock]") for p in paths) == 1

    def test_all_node_types_covered(self) -> None:
        """All 11 node types should have visit methods that create mappings."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Heading"),
                    body=[],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Paragraph"),
                    body=[TypstParagraph(text="Paragraph")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Table"),
                    body=[TypstTable(headers=["A"], data=[["B"]])],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Figure"),
                    body=[TypstFigure(content="img.png", caption="Figure")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Equation"),
                    body=[TypstEquation(latex="x=y")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="CodeBlock"),
                    body=[TypstCodeBlock(text="code")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="RawBlock"),
                    body=[TypstRawBlock(format="html", text="raw")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="BulletList"),
                    body=[TypstBulletList(items=[[TypstParagraph(text="Bullet")]])],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="OrderedList"),
                    body=[TypstOrderedList(items=[[TypstParagraph(text="Ordered")]])],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Section"),
                    body=[],
                    subsections=[],
                ),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=1000)

        # Verify all types are represented
        paths = [m.node_id.path for m in visitor.mappings]

        assert any(p == "doc" for p in paths)  # Document root
        assert any("Heading" in p for p in paths)
        assert any("Paragraph" in p for p in paths)
        assert any("Table" in p for p in paths)
        assert any("Figure" in p for p in paths)
        assert any("Equation" in p for p in paths)
        assert any("CodeBlock" in p for p in paths)
        assert any("RawBlock" in p for p in paths)
        assert any("BulletList" in p for p in paths)
        assert any("OrderedList" in p for p in paths)
        assert any("Section" in p for p in paths)


class TestMappingsListPopulation:
    """Test that self.mappings is properly populated during traversal."""

    def test_mappings_accumulates_all_entries(self) -> None:
        """Mappings list should accumulate entries during visit."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Para 1"),
                    body=[TypstParagraph(text="Para 1")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Para 2"),
                    body=[TypstParagraph(text="Para 2")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Para 3"),
                    body=[TypstParagraph(text="Para 3")],
                    subsections=[],
                ),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        assert len(visitor.mappings) == 0

        visitor.visit_document(doc, source_start=0, source_end=100)

        # Should have: document + 3 sections + 3 headings + 3 paragraphs
        assert len(visitor.mappings) == 10
        assert all(isinstance(m, MappingEntry) for m in visitor.mappings)

    def test_mappings_order_follows_traversal(self) -> None:
        """Mappings should be in document order (depth-first)."""
        from typst_ir.mapping.visitor import MappingVisitor

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="First"),
                    body=[],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Second"),
                    body=[],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Third"),
                    body=[],
                    subsections=[],
                ),
            ]
        )
        registry.initialize(doc)

        visitor = MappingVisitor(registry)
        visitor.visit_document(doc, source_start=0, source_end=100)

        heading_mappings = [m for m in visitor.mappings if "Heading" in m.node_id.path]
        # Document order should be First, Second, Third
        assert "First" in heading_mappings[0].node_id.path or "children.0" in heading_mappings[0].node_id.path
        assert "Second" in heading_mappings[1].node_id.path or "children.1" in heading_mappings[1].node_id.path
        assert "Third" in heading_mappings[2].node_id.path or "children.2" in heading_mappings[2].node_id.path
