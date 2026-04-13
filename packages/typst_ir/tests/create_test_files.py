"""Create test DOCX files and validate customIRID injection."""
from __future__ import annotations

import hashlib

# Import from typst_ir
import sys
import zipfile
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from typst_ir.mapping.injector import inject_ids
from typst_ir.mapping.types import DocxTypstMapping, MappingEntry, NodeID


def create_simple_docx(output_path: Path) -> None:
    """Create a simple document with a single paragraph."""
    doc = Document()
    doc.add_paragraph("This is a simple test paragraph for ID injection validation.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"Created: {output_path}")


def create_table_docx(output_path: Path) -> None:
    """Create a document with a 2x2 table."""
    doc = Document()
    doc.add_paragraph("Table test document with a 2x2 table.")
    
    table = doc.add_table(rows=2, cols=2)
    table.style = 'Table Grid'
    
    # Add header row
    table.cell(0, 0).text = "Header 1"
    table.cell(0, 1).text = "Header 2"
    
    # Add data row
    table.cell(1, 0).text = "Data A"
    table.cell(1, 1).text = "Data B"
    
    doc.add_paragraph("Text after the table.")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"Created: {output_path}")


def create_nested_docx(output_path: Path) -> None:
    """Create a complex document with nested structures."""
    doc = Document()
    
    # Add heading
    doc.add_heading("Nested Structure Test Document", level=1)
    
    # Add multiple paragraphs
    doc.add_paragraph("First paragraph with some content about wind energy measurements.")
    doc.add_paragraph("Second paragraph discussing meteorological tower data analysis.")
    
    # Add a subheading
    doc.add_heading("Data Section", level=2)
    
    # Add more paragraphs
    doc.add_paragraph("Paragraph under the data section with technical details.")
    
    # Add a nested list
    doc.add_paragraph("Bullet point 1")
    doc.add_paragraph("Bullet point 2")
    doc.add_paragraph("Bullet point 3")
    
    # Add another table
    table = doc.add_table(rows=3, cols=3)
    table.style = 'Table Grid'
    
    for i in range(3):
        for j in range(3):
            table.cell(i, j).text = f"Cell {i},{j}"
    
    doc.add_paragraph("Final paragraph after the table.")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"Created: {output_path}")


def create_test_mapping(num_paragraphs: int) -> DocxTypstMapping:
    """Create a test mapping for the specified number of paragraphs."""
    entries = {}
    path_index = {}
    
    for i in range(num_paragraphs):
        node_id = NodeID(
            path=f"doc.children.{i}",
            full_hash=hashlib.sha256(b"test").hexdigest()[:16],
            node_hash=hashlib.sha256(f"para{i}".encode()).hexdigest()[:16]
        )
        entry = MappingEntry(
            node_id=node_id,
            source_start=i,
            source_end=i + 1
        )
        entries[node_id.canonical] = entry
        path_index[node_id.path] = node_id.canonical
    
    return DocxTypstMapping(
        version="1.0.0",
        full_hash=hashlib.sha256(b"test_doc").hexdigest()[:16],
        entries=entries,
        path_index=path_index
    )


def verify_custom_irid(docx_path: Path) -> dict:
    """Verify that customIRID attributes are present in the DOCX XML."""
    results = {
        "file": str(docx_path),
        "has_custom_irid": False,
        "irid_count": 0,
        "irid_values": [],
        "xml_excerpt": ""
    }
    
    try:
        with zipfile.ZipFile(docx_path, 'r') as zf:
            if "word/document.xml" in zf.namelist():
                xml_content = zf.read("word/document.xml").decode('utf-8')
                
                # Check for customIRID
                if "customIRID" in xml_content:
                    results["has_custom_irid"] = True
                    
                    # Count occurrences
                    results["irid_count"] = xml_content.count("customIRID")
                    
                    # Extract some IRID values
                    import re
                    irid_matches = re.findall(r'w:customIRID="([^"]*)"', xml_content)
                    results["irid_values"] = irid_matches[:5]  # First 5
                    
                    # Get excerpt around first customIRID
                    idx = xml_content.find("customIRID")
                    if idx >= 0:
                        start = max(0, idx - 200)
                        end = min(len(xml_content), idx + 300)
                        results["xml_excerpt"] = xml_content[start:end]
    except Exception as e:
        results["error"] = str(e)
    
    return results


def main():
    """Main test execution."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    evidence_dir = Path(".sisyphus/evidence")
    
    # Ensure directories exist
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    test_files = {
        "simple": fixtures_dir / "simple.docx",
        "table": fixtures_dir / "table.docx",
        "nested": fixtures_dir / "nested.docx"
    }
    
    # Create test files
    print("=== Creating Test Files ===")
    create_simple_docx(test_files["simple"])
    create_table_docx(test_files["table"])
    create_nested_docx(test_files["nested"])
    
    # Create mappings and inject IDs
    print("\n=== Injecting IDs ===")
    verification_results = {}
    
    for name, path in test_files.items():
        # Count paragraphs in the document
        doc = Document(str(path))
        para_count = len(doc.paragraphs)
        
        # Add table cell paragraphs
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    para_count += len(cell.paragraphs)
        
        print(f"{name}: {para_count} paragraphs")
        
        # Create mapping
        mapping = create_test_mapping(para_count)
        
        # Inject IDs
        output_path = evidence_dir / f"task-07-{name}" / f"{name}_injected.docx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            inject_ids(path, output_path, mapping)
            print(f"  Injected: {output_path}")
            
            # Verify injection
            verification_results[name] = verify_custom_irid(output_path)
            verification_results[name]["original_file"] = str(path)
            verification_results[name]["injected_file"] = str(output_path)
            verification_results[name]["mapping_entries"] = len(mapping.entries)
            
        except Exception as e:
            print(f"  ERROR injecting {name}: {e}")
            verification_results[name] = {
                "error": str(e),
                "original_file": str(path),
                "injected_file": str(output_path)
            }
    
    # Print verification results
    print("\n=== Verification Results ===")
    for name, result in verification_results.items():
        print(f"\n{name}:")
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Has customIRID: {result['has_custom_irid']}")
            print(f"  IRID count: {result['irid_count']}")
            print(f"  IRID values: {result['irid_values'][:3]}")
    
    return verification_results


if __name__ == "__main__":
    results = main()
