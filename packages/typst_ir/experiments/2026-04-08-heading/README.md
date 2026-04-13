# Heading Detection Experiment

## Purpose

This experiment evaluates methods for detecting headings in a DOCX file, specifically testing whether `outline_level` from the `python-docx` API can be used to identify heading paragraphs and their levels.

## Examination Results

The examine script found 6 paragraphs in the document and attempted to read the `outline_level` property for each:

- **Paragraph 0** text: "Level One Unique Hash X1..."
- **Style name**: `Heading 1`
- **Error**: The script crashed with `AttributeError: 'ParagraphFormat' object has no attribute 'outline_level'`

This error occurs because `python-docx` does not expose `outline_level` on the `ParagraphFormat` object, even though the underlying OOXML schema supports it.

## Testing Results

The test script failed immediately with the same `AttributeError`:

```
AttributeError: 'ParagraphFormat' object has no attribute 'outline_level'
```

No outline level data could be retrieved for any paragraph. The test was designed to validate `outline_level` reliability but could not proceed past the first access.

## Findings

- **`outline_level` is not accessible via `python-docx`**: This is a hard API limitation. Scripts expecting this property will fail.
- **Style name is a viable fallback**: Paragraph 0 had the style name `Heading 1`, which strongly indicates it is a heading.
- **Heading detection must use style name parsing or raw XML**: Since the high-level API lacks outline level support, detection strategies need to:
  - Parse the style name (e.g., `Heading 1`, `Heading 2`) to infer the level.
  - Or parse the underlying OOXML (`<w:outlineLvl w:val="..."/>`) directly.

## Recommendations for Phase 2

1. **Abandon `outline_level` via `python-docx`**. It is not implemented in the library.
2. **Use style name parsing as the primary heading detector**. Look for style names matching patterns like `Heading N`.
3. **Add raw XML parsing as a fallback** for documents where style names are customized or localized.
4. **Document this limitation** clearly in any mapping or detection code so future developers do not attempt to use `paragraph_format.outline_level`.
