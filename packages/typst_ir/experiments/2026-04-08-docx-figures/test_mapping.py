#!/usr/bin/env python3
"""Test mapping creation for DOCX with figures.

This script tests the mapping creation between Typst IR nodes and DOCX paragraphs,
specifically checking how figures are detected and mapped.
"""

import json
import sys
from pathlib import Path

from docx import Document

# Add typst_ir to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from typst_ir.nodes import TypstDocument


def analyze_docx_structure(docx_path: str):
    """Analyze DOCX structure and identify potential figure elements."""
    doc = Document(docx_path)
    
    print("=" * 60)
    print("DOCX Structure Analysis for Mapping")
    print("=" * 60)
    
    # Use iter_inner_content to preserve document order
    elements = []
    for i, content in enumerate(doc.iter_inner_content()):
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        
        if isinstance(content, Paragraph):
            style_name = content.style.name if content.style else "None"
            text_preview = content.text[:80] + "..." if len(content.text) > 80 else content.text
            
            # Check for drawings
            drawings = content._element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing')
            has_drawing = len(drawings) > 0
            
            # Check for equations
            math_para = content._element.find('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMathPara')
            math_inline = content._element.find('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath')
            has_math = math_para is not None or math_inline is not None
            
            element_type = "paragraph"
            if 'heading' in style_name.lower():
                element_type = "heading"
            elif 'caption' in style_name.lower():
                element_type = "caption"
            elif has_drawing:
                element_type = "figure_image"
            elif has_math:
                element_type = "equation"
            
            elements.append({
                'index': i,
                'type': element_type,
                'style': style_name,
                'text': text_preview,
                'has_drawing': has_drawing,
                'has_math': has_math,
            })
            
        elif isinstance(content, Table):
            elements.append({
                'index': i,
                'type': 'table',
                'rows': len(content.rows),
                'cols': len(content.columns),
            })
    
    # Print analysis
    print(f"\nTotal elements: {len(elements)}")
    
    # Group by type
    from collections import Counter
    type_counts = Counter(e['type'] for e in elements)
    print("\nElement types:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")
    
    # Print figure-related elements
    figure_elements = [e for e in elements if e['type'] in ('figure_image', 'caption')]
    if figure_elements:
        print(f"\n🖼️  Figure-related elements ({len(figure_elements)}):")
        for e in figure_elements:
            print(f"  [{e['index']}] {e['type']}: {e['style']}")
            print(f"      Text: {e['text']}")
            if e['type'] == 'figure_image':
                print(f"      Has drawing: {e['has_drawing']}")
    
    # Print tables
    tables = [e for e in elements if e['type'] == 'table']
    if tables:
        print(f"\n📊 Tables ({len(tables)}):")
        for e in tables:
            print(f"  [{e['index']}] {e['rows']}x{e['cols']}")
    
    # Print headings
    headings = [e for e in elements if e['type'] == 'heading']
    if headings:
        print(f"\n📌 Headings ({len(headings)}):")
        for e in headings[:10]:  # Show first 10
            print(f"  [{e['index']}] {e['style']}: {e['text']}")
    
    # Print equations
    equations = [e for e in elements if e['type'] == 'equation']
    if equations:
        print(f"\n📐 Equations ({len(equations)}):")
        for e in equations[:10]:  # Show first 10
            print(f"  [{e['index']}] {e['text']}")
    
    return elements


def load_ir_json(json_path: str):
    """Load Typst IR from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    doc = TypstDocument.model_validate(data)
    
    print("=" * 60)
    print("Typst IR Analysis")
    print("=" * 60)
    
    # Count node types
    from collections import Counter
    node_types = Counter()
    
    def count_nodes(node):
        node_type = type(node).__name__
        node_types[node_type] += 1
        if hasattr(node, 'children'):
            for child in node.children:
                count_nodes(child)
    
    count_nodes(doc)
    
    print("\nNode types in IR:")
    for t, count in sorted(node_types.items()):
        print(f"  {t}: {count}")
    
    # Find figures
    figures = []
    def find_figures(node, path="root"):
        if type(node).__name__ == 'TypstFigure':
            figures.append({
                'path': path,
                'caption': node.caption,
                'kind': node.kind,
            })
        if hasattr(node, 'children'):
            for i, child in enumerate(node.children):
                find_figures(child, f"{path}.children[{i}]")
    
    find_figures(doc)
    
    if figures:
        print(f"\n🖼️  Figures in IR ({len(figures)}):")
        for fig in figures[:10]:  # Show first 10
            print(f"  {fig['path']}: {fig['caption'][:50]}...")
    
    return doc, node_types


def main():
    # Paths
    project_root = Path(__file__).parent.parent.parent.parent.parent
    docx_path = project_root / "test-data" / "cleanmast" / "kp-202603-report" / "rep-ts" / "report.docx"
    json_path = project_root / "test-data" / "cleanmast" / "kp-202603-report" / "rep-ts" / "report.typ.json"
    
    if not docx_path.exists():
        print(f"❌ DOCX not found: {docx_path}")
        print("Run run_report.py first to generate the DOCX")
        sys.exit(1)
    
    if not json_path.exists():
        print(f"❌ IR JSON not found: {json_path}")
        print("Run run_report.py first to generate the IR JSON")
        sys.exit(1)
    
    # Analyze DOCX
    docx_elements = analyze_docx_structure(str(docx_path))
    
    # Load IR
    doc, node_types = load_ir_json(str(json_path))
    
    # Summary
    print("\n" + "=" * 60)
    print("MAPPING SUMMARY")
    print("=" * 60)
    
    print(f"\nDOCX elements: {len(docx_elements)}")
    print(f"IR nodes: {sum(node_types.values())}")
    
    # Check for figures
    docx_figures = [e for e in docx_elements if e['type'] in ('figure_image', 'caption')]
    ir_figures = node_types.get('TypstFigure', 0)
    
    print("\nFigure comparison:")
    print(f"  DOCX figure elements: {len(docx_figures)}")
    print(f"  IR TypstFigure nodes: {ir_figures}")
    
    if len(docx_figures) > 0 and ir_figures > 0:
        print("\n✓ Both DOCX and IR have figures - mapping should work")
    elif len(docx_figures) == 0 and ir_figures > 0:
        print("\n⚠️  IR has figures but DOCX doesn't - pandoc may not embed images")
    elif len(docx_figures) > 0 and ir_figures == 0:
        print("\n⚠️  DOCX has figures but IR doesn't - unexpected")
    else:
        print("\n❌ No figures in either DOCX or IR")
    
    return {
        'docx_elements': len(docx_elements),
        'ir_nodes': sum(node_types.values()),
        'docx_figures': len(docx_figures),
        'ir_figures': ir_figures,
    }


if __name__ == "__main__":
    result = main()
    print(f"\nResult: {result}")