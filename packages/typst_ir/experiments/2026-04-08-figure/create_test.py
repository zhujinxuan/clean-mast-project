"""
Create Typst IR with figures.

Usage: python create_test.py
Output: input.json

Note: Figures will be converted to DOCX with image placeholder
and separate caption paragraph.
"""
from pathlib import Path

from typst_ir import TypstDocument, TypstFigure, TypstParagraph

# Create document with figure
doc = TypstDocument(children=[
    TypstParagraph(text="Paragraph before figure unique P1"),
    TypstFigure(
        content="figure1.png",  # Image placeholder
        caption="Figure One Caption Unique F1",
        kind="image"
    ),
    TypstParagraph(text="Paragraph after figure unique P2"),
])

# Save to input.json
Path("input.json").write_text(doc.model_dump_json())
print(f"Created input.json with {len(doc.children)} nodes")
print("Note: Figure will need image file or placeholder in DOCX")
