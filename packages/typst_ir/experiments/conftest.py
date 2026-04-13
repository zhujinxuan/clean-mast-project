from typst_ir import (
    TypstDocument,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)


def build_simple_document():
    """Create a simple document with one paragraph."""
    return TypstDocument(children=[TypstParagraph(text="Test content")])


def build_heading_document(levels=[1, 2, 3]):
    """Create a document with headings at specified levels."""
    children = []
    for level in levels:
        children.append(TypstHeading(text=f"Heading {level}", level=level))
    return TypstDocument(children=children)


def build_table_document():
    """Create a document with a table."""
    return TypstDocument(children=[
        TypstTable(
            headers=["Col A", "Col B"],
            data=[["Row 1", "Row 1"]],
            caption="Test Table"
        )
    ])
