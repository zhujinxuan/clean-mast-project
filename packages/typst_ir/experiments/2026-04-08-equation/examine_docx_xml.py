"""
Examine DOCX XML structure for equations.

Questions:
- How are equations represented in XML (OMML)?
- Can we detect display vs inline equations?
- What's the difference between m:oMath and m:oMathPara?
"""

from docx import Document
from docx.oxml.ns import qn

doc = Document("output/equation.docx")

print("=== Equation Structure ===")
print(f"Paragraphs: {len(doc.paragraphs)}")

for i, para in enumerate(doc.paragraphs):
    print(f"\n--- Paragraph {i} ---")
    print(f"Text: {para.text[:50]}...")
    
    # Check for display equation
    has_math_para = para._element.find(qn('m:oMathPara')) is not None
    print(f"Has m:oMathPara (display): {has_math_para}")
    
    # Check for inline equation
    has_math = bool(para._element.xpath('.//m:oMath'))
    print(f"Has m:oMath (inline): {has_math}")
    
    # Check if equation-only paragraph
    if has_math_para:
        print("  ** Display equation (entire paragraph is equation)")
        # Show XML
        math_para = para._element.find(qn('m:oMathPara'))
        print("  m:oMathPara tag present")
    elif has_math:
        print("  ** Inline equation (mixed with text)")
        
        # Show XML snippet
        for elem in para._element.iter():
            if 'oMath' in elem.tag:
                print(f"  Found: {elem.tag}")
