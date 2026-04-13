"""
Create Typst IR with tables.

Usage: python create_test.py
Output: input.json
"""
from pathlib import Path

from typst_ir import TypstDocument, TypstParagraph, TypstTable

# Create document with table and surrounding content
doc = TypstDocument(children=[
    TypstParagraph(text="Paragraph before table unique P1"),
    TypstTable(
        headers=["Col A Uniq1", "Col B Uniq2"],
        data=[
            ["Cell 1-1 Unique X1", "Cell 1-2 Unique Y1"],
            ["Cell 2-1 Unique X2", "Cell 2-2 Unique Y2"],
        ],
        caption="Table One Caption Unique Q1"
    ),
    TypstParagraph(text="Paragraph after table unique P2"),
])

# Save to input.json
Path("input.json").write_text(doc.model_dump_json())
print(f"Created input.json with {len(doc.children)} nodes")
