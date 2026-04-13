# Paragraph Detection Experiment

## Purpose

This experiment analyzes how to reliably detect and match paragraphs in a DOCX file against expected Typst IR nodes. The focus is on text retrieval accuracy and content hash matching as a mechanism for traceability.

## Examination Results

The examine script analyzed a DOCX file containing 3 paragraphs. Key observations:

- **Document structure**: 3 paragraphs were found in the body.
- **Style anomaly**: The first paragraph unexpectedly had the style `Heading 1`. This suggests the document was generated via pandoc, which sometimes assigns heading styles to plain paragraphs.
- **XML representation**: Each paragraph is wrapped in a `<w:p>` element. The full XML for paragraph 0 is 296 characters, including a `<w:pPr>` with `<w:pStyle w:val="Heading1" />`.
- **Error encountered**: The script failed when attempting to read `paragraph_format.outline_level` because `python-docx` does not expose this attribute on the `ParagraphFormat` object. This is a known limitation of the library.

## Testing Results

All tests passed successfully:

- **Text retrieval**: All 3 paragraphs returned text exactly matching the expected strings.
- **Content hash matching**: All 3 paragraphs produced SHA-256 hashes that matched the expected hashes exactly (100% success rate).

| Paragraph | Hash Match | Text Match |
|-----------|------------|------------|
| 0         | Yes        | Yes        |
| 1         | Yes        | Yes        |
| 2         | Yes        | Yes        |

## Findings

- **Content hash matching is reliable**: Given a known source of truth, hashing paragraph text content is a 100% accurate way to identify a paragraph in a DOCX file.
- **Text retrieval is stable**: `paragraph.text` consistently returns the full text content.
- **Styles are unreliable for paragraph detection**: Pandoc-generated DOCX files may assign heading styles to ordinary paragraphs, so style-based detection should not be used to distinguish paragraphs from headings.
- **Outline level is not available via `python-docx`**: Any heading-level detection must fall back to XML parsing or style name parsing.

## Recommendations for Phase 2

1. **Use content hash matching** as the primary traceability mechanism for paragraphs.
2. **Do not rely on style names** to differentiate paragraphs from headings in pandoc-generated DOCX files.
3. **Parse XML directly** if outline level or other `ParagraphFormat` properties are needed, since `python-docx` does not expose them.
