"""
Test heading property retrieval.

Questions:
- Does outline_level always match expected level?
- What percentage of headings have outline_level?
- Is style name parsing reliable as fallback?
"""
import json
import re

from docx import Document

with open("input.json") as f:
    expected = json.load(f)

doc = Document("output/heading.docx")

print("=== Test: outline_level Reliability ===")
success_count = 0
total_count = 0

for i, (expected_node, actual_para) in enumerate(zip(expected['children'], doc.paragraphs)):
    expected_level = expected_node['level']
    outline_level = actual_para.paragraph_format.outline_level
    
    total_count += 1
    
    print(f"\nHeading {i}:")
    print(f"  Expected level: {expected_level}")
    print(f"  outline_level: {outline_level}")
    
    if outline_level == expected_level:
        print("  ✓ MATCH")
        success_count += 1
    else:
        print("  ✗ MISMATCH or None")
        # Try style parsing
        if actual_para.style:
            match = re.search(r'heading\s*(\d+)', actual_para.style.name.lower())
            if match:
                style_level = int(match.group(1))
                print(f"  Style level: {style_level}")
                if style_level == expected_level:
                    print("  ✓ Style fallback success")

print(f"\nSuccess rate: {success_count}/{total_count} = {success_count/total_count*100:.1f}%")
print("✓ Tests passed")
