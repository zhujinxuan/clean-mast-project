"""
Create Typst IR with paragraphs and save to input.json.

Usage: python create_test.py
Output: input.json
"""
from pathlib import Path

from typst_ir import TypstDocument, TypstParagraph

# Create document with unique paragraphs
doc = TypstDocument(children=[
    TypstParagraph(text="First paragraph unique hash abc123."),
    TypstParagraph(text="Second paragraph unique hash def456."),
    TypstParagraph(text="Third paragraph unique hash ghi789."),
])

# Save to input.json
Path("input.json").write_text(doc.model_dump_json())
print(f"Created input.json with {len(doc.children)} paragraphs")
