# Figure Detection Experiment

## Purpose

This experiment tests how figures (images with captions) are represented in a DOCX file, focusing on detecting image paragraphs, caption paragraphs, and the relationship between them.

## Examination Results

The examine script found 3 paragraphs and performed detailed XML checks for images and drawings:

- **Paragraph 0**: "Paragraph before figure unique P1..." 
  - Style: `Heading 1`
  - Has image: `False`
  - Has drawing: `False`
- **Paragraph 1**: "Figure One Caption Unique F1..."
  - Style: `Image Caption`
  - Has image: `False`
  - Has drawing: `False`
  - Figure-related style detected (keywords: "image caption")
- **Paragraph 2**: "Paragraph after figure unique P2..."
  - Style: `Heading 1`
  - Has image: `False`
  - Has drawing: `False`

No actual image or drawing elements were found in any paragraph. This is consistent with pandoc-generated DOCX files, which may represent figures using text/caption paragraphs without embedding true `w:drawing` elements.

## Testing Results

- **Test 1 (Image paragraphs)**: 0 image paragraphs detected. Passed structurally but found no image content.
- **Test 2 (Caption paragraphs)**: 1 caption paragraph detected (Paragraph 1, style `Image Caption`). Passed.
- **Test 3 (Pair matching)**: Failed with `KeyError: 'type'` when trying to filter expected JSON nodes by `node['type'] == 'TypstFigure'`.

The pair matching failure is the same JSON serialization format issue seen in the table and equation experiments.

## Findings

- **Pandoc-generated figures lack image/drawing elements**: The DOCX contains a caption but no `<w:drawing>` or image tags. This means figure detection cannot rely solely on finding embedded images.
- **Caption detection via style works**: The `Image Caption` style was correctly identified and can be used as a strong signal for figure presence.
- **Style-based heuristics are essential**: Since raw image elements are absent, detecting a paragraph with an "Image Caption" style (or similar) and treating adjacent content as a figure is the most robust strategy.
- **JSON format issue blocks type-based matching**: Expected IR JSON nodes lack the `type` field, breaking tests that filter by node type.

## Recommendations for Phase 2

1. **Implement figure detection as a caption-first heuristic**: Look for paragraphs with styles matching `Image Caption`, `Figure Caption`, or localized equivalents. Treat the caption as the figure anchor.
2. **Do not require embedded images for figure detection**: In pandoc-generated output, figures may be represented purely as captions.
3. **Consider pairwise analysis**: When an image element *is* present, associate it with the nearest caption paragraph (before or after) to form a complete figure mapping.
4. **Fix or adapt to JSON serialization**: Update expected JSON files to include `type` fields, or change test scripts to identify expected figures by structural properties (e.g., presence of `caption` and `kind`).
