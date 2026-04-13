"""JSON round-trip tests for Pydantic models.

Tests that all Typst IR nodes can be serialized to JSON and deserialized
back to equivalent objects using Pydantic's built-in methods.
"""

import pytest
from pydantic import ValidationError
from typst_ir.nodes import (
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


class TestTypstTableJson:
    """JSON round-trip tests for TypstTable."""

    def test_table_model_dump_json(self):
        table = TypstTable(
            data=[["a", "b"], ["c", "d"]],
            headers=["Col1", "Col2"],
            caption="Test table",
        )
        json_str = table.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test table" in json_str
        assert "Col1" in json_str

    def test_table_model_validate_json(self):
        json_str = '{"data":[["a","b"],["c","d"]],"headers":["Col1","Col2"],"caption":"Test"}'
        table = TypstTable.model_validate_json(json_str)
        assert table.data == [["a", "b"], ["c", "d"]]
        assert table.headers == ["Col1", "Col2"]
        assert table.caption == "Test"

    def test_table_roundtrip(self):
        original = TypstTable(
            data=[["1", "2"], ["3", "4"]],
            headers=["A", "B"],
            caption="My table",
        )
        json_str = original.model_dump_json()
        restored = TypstTable.model_validate_json(json_str)
        assert original == restored


class TestTypstFigureJson:
    """JSON round-trip tests for TypstFigure."""

    def test_figure_model_dump_json(self):
        figure = TypstFigure(
            content="path/to/image.png",
            caption="A figure",
            kind="image",
        )
        json_str = figure.model_dump_json()
        assert isinstance(json_str, str)
        assert "path/to/image.png" in json_str

    def test_figure_model_validate_json(self):
        json_str = '{"content":"img.png","caption":"Test figure","kind":"diagram"}'
        figure = TypstFigure.model_validate_json(json_str)
        assert figure.content == "img.png"
        assert figure.caption == "Test figure"
        assert figure.kind == "diagram"

    def test_figure_roundtrip(self):
        original = TypstFigure(content="test.png", caption="Test")
        json_str = original.model_dump_json()
        restored = TypstFigure.model_validate_json(json_str)
        assert original == restored

    def test_figure_default_kind(self):
        original = TypstFigure(content="img.png", caption="Caption")
        assert original.kind == "image"
        json_str = original.model_dump_json()
        restored = TypstFigure.model_validate_json(json_str)
        assert restored.kind == "image"


class TestTypstHeadingJson:
    """JSON round-trip tests for TypstHeading."""

    def test_heading_model_dump_json(self):
        heading = TypstHeading(text="Chapter 1")
        json_str = heading.model_dump_json()
        assert "Chapter 1" in json_str
        assert '"level"' not in json_str

    def test_heading_model_validate_json(self):
        json_str = '{"text":"Section"}'  # no level
        heading = TypstHeading.model_validate_json(json_str)
        assert heading.text == "Section"

    def test_heading_roundtrip(self):
        original = TypstHeading(text="Title")
        json_str = original.model_dump_json()
        restored = TypstHeading.model_validate_json(json_str)
        assert original == restored

    def test_heading_default_level_removed(self):
        # TypstHeading no longer has a level field at all
        heading = TypstHeading(text="Default")
        assert not hasattr(heading, 'level') or 'level' not in heading.model_fields


class TestTypstParagraphJson:
    """JSON round-trip tests for TypstParagraph."""

    def test_paragraph_model_dump_json(self):
        para = TypstParagraph(text="This is a paragraph.")
        json_str = para.model_dump_json()
        assert "This is a paragraph." in json_str

    def test_paragraph_model_validate_json(self):
        json_str = '{"text":"Hello world"}'
        para = TypstParagraph.model_validate_json(json_str)
        assert para.text == "Hello world"

    def test_paragraph_roundtrip(self):
        original = TypstParagraph(text="Test paragraph content.")
        json_str = original.model_dump_json()
        restored = TypstParagraph.model_validate_json(json_str)
        assert original == restored


class TestTypstEquationJson:
    """JSON round-trip tests for TypstEquation."""

    def test_equation_model_dump_json(self):
        eq = TypstEquation(latex="E = mc^2", display=True)
        json_str = eq.model_dump_json()
        assert "E = mc^2" in json_str
        assert '"display":true' in json_str

    def test_equation_model_validate_json(self):
        json_str = '{"latex":"\\\\frac{a}{b}","display":false}'
        eq = TypstEquation.model_validate_json(json_str)
        assert eq.latex == "\\frac{a}{b}"
        assert eq.display is False

    def test_equation_roundtrip(self):
        original = TypstEquation(latex="x^2 + y^2 = z^2", display=True)
        json_str = original.model_dump_json()
        restored = TypstEquation.model_validate_json(json_str)
        assert original == restored

    def test_equation_default_display(self):
        original = TypstEquation(latex="x = y")
        assert original.display is False
        json_str = original.model_dump_json()
        restored = TypstEquation.model_validate_json(json_str)
        assert restored.display is False


class TestTypstCodeBlockJson:
    """JSON round-trip tests for TypstCodeBlock."""

    def test_codeblock_model_dump_json(self):
        code = TypstCodeBlock(text="print('hello')", language="python")
        json_str = code.model_dump_json()
        assert "print('hello')" in json_str
        assert "python" in json_str

    def test_codeblock_model_validate_json(self):
        json_str = '{"text":"const x = 1;","language":"javascript"}'
        code = TypstCodeBlock.model_validate_json(json_str)
        assert code.text == "const x = 1;"
        assert code.language == "javascript"

    def test_codeblock_roundtrip(self):
        original = TypstCodeBlock(text="def foo(): pass", language="python")
        json_str = original.model_dump_json()
        restored = TypstCodeBlock.model_validate_json(json_str)
        assert original == restored

    def test_codeblock_no_language(self):
        original = TypstCodeBlock(text="some raw text")
        assert original.language is None
        json_str = original.model_dump_json()
        restored = TypstCodeBlock.model_validate_json(json_str)
        assert restored.language is None


class TestTypstRawBlockJson:
    """JSON round-trip tests for TypstRawBlock."""

    def test_rawblock_model_dump_json(self):
        raw = TypstRawBlock(format="html", text="<p>content</p>")
        json_str = raw.model_dump_json()
        assert "html" in json_str
        assert "<p>content</p>" in json_str

    def test_rawblock_model_validate_json(self):
        json_str = '{"format":"latex","text":"\\\\section{Test}"}'
        raw = TypstRawBlock.model_validate_json(json_str)
        assert raw.format == "latex"
        assert raw.text == "\\section{Test}"

    def test_rawblock_roundtrip(self):
        original = TypstRawBlock(format="xml", text="<root/>")
        json_str = original.model_dump_json()
        restored = TypstRawBlock.model_validate_json(json_str)
        assert original == restored


class TestTypstSectionJson:
    """JSON round-trip tests for TypstSection (nested structure)."""

    def test_section_model_dump_json(self):
        section = TypstSection(
            heading=TypstHeading(text="Section 1"),
            body=[TypstParagraph(text="Content here.")],
            subsections=[],
        )
        json_str = section.model_dump_json()
        assert "Section 1" in json_str
        assert "Content here." in json_str
        assert '"body"' in json_str
        assert '"subsections"' in json_str
        assert '"children"' not in json_str

    def test_section_roundtrip(self):
        original = TypstSection(
            heading=TypstHeading(text="Main Section"),
            body=[
                TypstEquation(latex="E=mc^2", display=True),
                TypstCodeBlock(text="code", language="python"),
            ],
            subsections=[],
        )
        json_str = original.model_dump_json()
        restored = TypstSection.model_validate_json(json_str)
        assert original == restored


class TestTypstBulletListJson:
    """JSON round-trip tests for TypstBulletList."""

    def test_bulletlist_model_dump_json(self):
        blist = TypstBulletList(
            items=[
                [TypstParagraph(text="Item 1")],
                [TypstParagraph(text="Item 2")],
            ],
        )
        json_str = blist.model_dump_json()
        assert "Item 1" in json_str
        assert "Item 2" in json_str

    def test_bulletlist_roundtrip(self):
        original = TypstBulletList(
            items=[
                [TypstEquation(latex="x = 1")],
                [
                    TypstCodeBlock(text="print('a')"),
                    TypstCodeBlock(text="print('b')"),
                ],
            ],
        )
        json_str = original.model_dump_json()
        restored = TypstBulletList.model_validate_json(json_str)
        assert original == restored


class TestTypstOrderedListJson:
    """JSON round-trip tests for TypstOrderedList."""

    def test_orderedlist_model_dump_json(self):
        olist = TypstOrderedList(
            items=[
                [TypstParagraph(text="Step 1")],
                [TypstParagraph(text="Step 2")],
            ],
            start=1,
        )
        json_str = olist.model_dump_json()
        assert "Step 1" in json_str
        assert '"start":1' in json_str

    def test_orderedlist_model_validate_json(self):
        json_str = '{"items":[[{"typst_type":"TypstEquation","latex":"x","display":false}]],"start":5}'
        olist = TypstOrderedList.model_validate_json(json_str)
        assert olist.start == 5
        assert len(olist.items) == 1

    def test_orderedlist_roundtrip(self):
        original = TypstOrderedList(
            items=[
                [TypstEquation(latex="a")],
                [TypstEquation(latex="b")],
            ],
            start=10,
        )
        json_str = original.model_dump_json()
        restored = TypstOrderedList.model_validate_json(json_str)
        assert original == restored

    def test_orderedlist_default_start(self):
        original = TypstOrderedList(
            items=[[TypstEquation(latex="x")]],
        )
        assert original.start == 1
        json_str = original.model_dump_json()
        restored = TypstOrderedList.model_validate_json(json_str)
        assert restored.start == 1


class TestTypstDocumentJson:
    """JSON round-trip tests for TypstDocument."""

    def test_document_model_dump_json(self):
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content.")],
                    subsections=[],
                ),
            ],
        )
        json_str = doc.model_dump_json()
        assert "Title" in json_str
        assert "Content." in json_str

    def test_document_roundtrip_simple(self):
        original = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Equation"),
                    body=[TypstEquation(latex="E=mc^2")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Code"),
                    body=[TypstCodeBlock(text="code")],
                    subsections=[],
                ),
            ],
        )
        json_str = original.model_dump_json()
        restored = TypstDocument.model_validate_json(json_str)
        assert original == restored

    def test_document_roundtrip_complex(self):
        original = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Document Title"),
                    body=[
                        TypstTable(
                            data=[["a", "b"]],
                            headers=["X", "Y"],
                        ),
                        TypstFigure(
                            content="image.png",
                            caption="A figure",
                        ),
                        TypstEquation(latex="E=mc^2", display=True),
                        TypstCodeBlock(text="print('hi')", language="python"),
                        TypstRawBlock(format="html", text="<br/>"),
                    ],
                    subsections=[],
                ),
            ],
        )
        json_str = original.model_dump_json()
        restored = TypstDocument.model_validate_json(json_str)
        assert original == restored

    def test_document_empty_children(self):
        original = TypstDocument(children=[])
        json_str = original.model_dump_json()
        restored = TypstDocument.model_validate_json(json_str)
        assert original == restored


class TestJsonHumanReadable:
    """Tests for JSON formatting and human readability."""

    def test_json_indent_parameter(self):
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Math"),
                    body=[TypstEquation(latex="x")],
                    subsections=[],
                ),
            ],
        )
        json_str = doc.model_dump_json(indent=2)
        assert "\n" in json_str
        assert "  " in json_str

    def test_json_indent_4(self):
        para = TypstParagraph(text="Hello")
        json_str = para.model_dump_json(indent=4)
        assert "    " in json_str

    def test_json_no_indent(self):
        para = TypstParagraph(text="Hello")
        json_str = para.model_dump_json()
        assert "\n" not in json_str


class TestJsonValidationErrors:
    """Tests for invalid JSON handling."""

    def test_invalid_json_raises_validation_error(self):
        invalid_json = "not valid json {{{"
        with pytest.raises(ValidationError):
            TypstDocument.model_validate_json(invalid_json)

    def test_missing_required_field(self):
        json_str = '{"wrong_field": "value"}'
        with pytest.raises(ValidationError):
            TypstParagraph.model_validate_json(json_str)

    def test_wrong_type_raises_error(self):
        json_str = '{"text": 123}'
        with pytest.raises(ValidationError):
            TypstHeading.model_validate_json(json_str)

    def test_old_section_schema_rejected(self):
        import json
        old_json = json.dumps({
            "typst_type": "TypstSection",
            "heading": {"typst_type": "TypstHeading", "text": "Old", "level": 1},
            "children": [{"typst_type": "TypstParagraph", "text": "old"}]
        })
        with pytest.raises(ValidationError):
            TypstSection.model_validate_json(old_json)

    def test_empty_json_raises_error(self):
        json_str = "{}"
        with pytest.raises(ValidationError):
            TypstParagraph.model_validate_json(json_str)


class TestNestedStructuresRoundtrip:
    """Tests for deeply nested structures."""

    def test_deeply_nested_sections(self):
        original = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Level 1"),
                    body=[TypstEquation(latex="x")],
                    subsections=[
                        TypstSection(
                            heading=TypstHeading(text="Level 2"),
                            body=[TypstEquation(latex="y")],
                            subsections=[
                                TypstSection(
                                    heading=TypstHeading(text="Level 3"),
                                    body=[TypstCodeBlock(text="code")],
                                    subsections=[],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        json_str = original.model_dump_json()
        restored = TypstDocument.model_validate_json(json_str)
        assert original == restored

    def test_list_within_section(self):
        original = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Section with Lists"),
                    body=[
                        TypstEquation(latex="x = y"),
                        TypstBulletList(
                            items=[
                                [TypstEquation(latex="a")],
                                [TypstEquation(latex="b")],
                            ],
                        ),
                        TypstOrderedList(
                            items=[
                                [TypstCodeBlock(text="step1")],
                                [TypstCodeBlock(text="step2")],
                            ],
                            start=1,
                        ),
                    ],
                    subsections=[],
                ),
            ],
        )
        json_str = original.model_dump_json()
        restored = TypstDocument.model_validate_json(json_str)
        assert original == restored

    def test_mixed_content_document(self):
        original = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Full Document"),
                    body=[
                        TypstHeading(text="Full Document"),
                        TypstEquation(latex="Introduction"),
                    ],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Tables and Figures"),
                    body=[
                        TypstTable(
                            data=[["1", "2"], ["3", "4"]],
                            headers=["A", "B"],
                            caption="Data table",
                        ),
                        TypstFigure(
                            content="plot.png",
                            caption="Results plot",
                        ),
                    ],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Code and Equations"),
                    body=[
                        TypstEquation(latex="F = ma", display=True),
                        TypstCodeBlock(
                            text="def calculate(): return 42",
                            language="python",
                        ),
                        TypstRawBlock(format="html", text="<div>Raw</div>"),
                    ],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Bullet List"),
                    body=[
                        TypstBulletList(
                            items=[
                                [TypstEquation(latex="p1")],
                                [TypstEquation(latex="p2")],
                            ],
                        ),
                    ],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Ordered List"),
                    body=[
                        TypstOrderedList(
                            items=[
                                [TypstCodeBlock(text="c1")],
                                [TypstCodeBlock(text="c2")],
                            ],
                        ),
                    ],
                    subsections=[],
                ),
            ],
        )
        json_str = original.model_dump_json()
        restored = TypstDocument.model_validate_json(json_str)
        assert original == restored


class TestAllNodeTypes:
    def test_all_node_types_individually(self):
        nodes = [
            TypstTable(data=[["x"]], headers=["H"]),
            TypstFigure(content="img.png", caption="Caption"),
            TypstHeading(text="Heading"),
            TypstParagraph(text="Paragraph"),
            TypstEquation(latex="x = y"),
            TypstCodeBlock(text="code"),
            TypstRawBlock(format="fmt", text="raw"),
        ]

        for node in nodes:
            json_str = node.model_dump_json()
            restored = node.__class__.model_validate_json(json_str)
            assert node == restored, f"Round-trip failed for {node.__class__.__name__}"

    def test_document_with_all_node_types(self):
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Table"),
                    body=[TypstTable(data=[["a"]], headers=["H"])],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Figure"),
                    body=[TypstFigure(content="f.png", caption="F")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Heading"),
                    body=[TypstHeading(text="H")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Equation"),
                    body=[TypstEquation(latex="eq")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="CodeBlock"),
                    body=[TypstCodeBlock(text="cb")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="RawBlock"),
                    body=[TypstRawBlock(format="r", text="raw")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="S"),
                    body=[TypstEquation(latex="e")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="BulletList"),
                    body=[TypstBulletList(items=[[TypstEquation(latex="b")]])],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="OrderedList"),
                    body=[TypstOrderedList(items=[[TypstCodeBlock(text="c")]])],
                    subsections=[],
                ),
            ]
        )
        json_str = doc.model_dump_json()
        restored = TypstDocument.model_validate_json(json_str)
        assert doc == restored

    def test_paragraph_in_section_children(self):
        section = TypstSection(
            heading=TypstHeading(text="Section Title"),
            body=[
                TypstParagraph(text="Section intro."),
                TypstParagraph(text="More content."),
            ],
            subsections=[],
        )
        json_str = section.model_dump_json()
        restored = TypstSection.model_validate_json(json_str)
        assert isinstance(restored.body[0], TypstParagraph)
        assert isinstance(restored.body[1], TypstParagraph)
        assert section == restored

    def test_paragraph_in_bullet_list_items(self):
        bullet_list = TypstBulletList(
            items=[
                [TypstParagraph(text="Item 1")],
                [TypstParagraph(text="Item 2a"), TypstParagraph(text="Item 2b")],
            ]
        )
        json_str = bullet_list.model_dump_json()
        restored = TypstBulletList.model_validate_json(json_str)
        assert isinstance(restored.items[0][0], TypstParagraph)
        assert isinstance(restored.items[1][0], TypstParagraph)
        assert isinstance(restored.items[1][1], TypstParagraph)
        assert bullet_list == restored

    def test_paragraph_in_ordered_list_items(self):
        ordered_list = TypstOrderedList(
            items=[
                [TypstParagraph(text="Step 1")],
                [TypstParagraph(text="Step 2a"), TypstParagraph(text="Step 2b")],
            ],
            start=1,
        )
        json_str = ordered_list.model_dump_json()
        restored = TypstOrderedList.model_validate_json(json_str)
        assert isinstance(restored.items[0][0], TypstParagraph)
        assert isinstance(restored.items[1][0], TypstParagraph)
        assert isinstance(restored.items[1][1], TypstParagraph)
        assert ordered_list == restored
