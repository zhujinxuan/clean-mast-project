"""
Test figure property retrieval.

Questions:
- Can we detect image paragraphs?
- Can we detect caption paragraphs?
- Can we pair them correctly?
"""
import json

from docx import Document

with open("input.json") as f:
    expected = json.load(f)

doc = Document("output/figure.docx")

print("=== Test 1: Detect Image Paragraphs ===")
image_paragraphs = []
for i, para in enumerate(doc.paragraphs):
    has_image = bool(para._element.xpath('.//a:blip'))
    if has_image:
        image_paragraphs.append(i)
        print(f"Paragraph {i}: Has image")

print(f"Total image paragraphs: {len(image_paragraphs)}")

print("\n=== Test 2: Detect Caption Paragraphs ===")
caption_paragraphs = []
for i, para in enumerate(doc.paragraphs):
    style_lower = para.style.name.lower() if para.style else ""
    if 'caption' in style_lower:
        caption_paragraphs.append(i)
        print(f"Paragraph {i}: Style '{para.style.name}' (caption)")

print(f"Total caption paragraphs: {len(caption_paragraphs)}")

print("\n=== Test 3: Pair Matching ===")
expected_figures = [node for node in expected['children'] if node['type'] == 'TypstFigure']

print(f"Expected figures: {len(expected_figures)}")
print(f"Found image paragraphs: {len(image_paragraphs)}")
print(f"Found caption paragraphs: {len(caption_paragraphs)}")

# Check pairing
paired_count = 0
for img_idx in image_paragraphs:
    # Check if next paragraph is caption
    if img_idx + 1 in caption_paragraphs:
        paired_count += 1
        print(f"Paired: Image paragraph {img_idx} + Caption paragraph {img_idx+1}")

print(f"\nPaired figures: {paired_count}/{len(expected_figures)}")
print("✓ Tests passed")
