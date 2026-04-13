"""
Create Typst IR with headings at multiple levels.

Usage: python create_test.py
Output: input.json
"""
from pathlib import Path

from typst_ir import TypstDocument, TypstHeading, TypstParagraph

# Create document with headings at levels 1-3
doc = TypstDocument(children=[
    TypstHeading(text="Level One Unique Hash X1", level=1),
    TypstParagraph(text="Content under level one unique A1"),
    TypstHeading(text="Level Two Unique Hash Y2", level=2),
    TypstParagraph(text="Content under level two unique B2"),
    TypstHeading(text="Level Three Unique Hash Z3", level=3),
    TypstParagraph(text="Content under level three unique C3"),
])

# Save to input.json
Path("input.json").write_text(doc.model_dump_json())
print(f"Created input.json with {len(doc.children)} nodes")
