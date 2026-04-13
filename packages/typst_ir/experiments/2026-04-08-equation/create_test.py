"""
Create Typst IR with equations (inline and display).

Usage: python create_test.py
Output: input.json
"""
from pathlib import Path

from typst_ir import TypstDocument, TypstEquation, TypstParagraph

# Create document with equations
doc = TypstDocument(children=[
    TypstParagraph(text="Text before equation unique P1"),
    TypstEquation(latex="E = mc^2", display=True),  # Display equation
    TypstParagraph(text="Text with inline equation $a^2 + b^2 = c^2$"),
    TypstEquation(latex="\\sum_{i=1}^n x_i", display=True),  # Another display
    TypstParagraph(text="Text after equation unique P2"),
])

# Save to input.json
Path("input.json").write_text(doc.model_dump_json())
print(f"Created input.json with {len(doc.children)} nodes")
print("Note: Equations will be converted to OMML in DOCX")
