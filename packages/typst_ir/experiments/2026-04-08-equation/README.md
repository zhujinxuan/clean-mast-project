# Equation Detection Experiment

## Purpose

This experiment tests how mathematical equations (both display and inline) are represented in a DOCX file's XML, using Office Math Markup Language (OMML) tags.

## Examination Results

The examine script found 5 paragraphs and checked each for OMML tags:

- **Paragraph 0**: "Text before equation unique P1..."
  - `m:oMathPara`: False
  - `m:oMath`: False
- **Paragraph 1**: "..."
  - `m:oMathPara`: **True** (display equation)
  - `m:oMath`: **True**
  - Entire paragraph is a display equation.
- **Paragraph 2**: "Text with inline equation ..."
  - `m:oMathPara`: False
  - `m:oMath`: **True** (inline equation)
  - Equation is mixed with regular text.
- **Paragraph 3**: "..."
  - `m:oMathPara`: **True** (display equation)
  - `m:oMath`: **True**
  - Entire paragraph is a display equation.
- **Paragraph 4**: "Text after equation unique P2..."
  - `m:oMathPara`: False
  - `m:oMath`: False

Both `m:oMathPara` (display/block equations) and `m:oMath` (inline equations) were detected correctly in the expected paragraphs.

## Testing Results

- **Test 1 (Display equations)**: 2 display equations detected (Paragraphs 1 and 3). Passed.
- **Test 2 (Inline equations)**: 1 inline equation detected (Paragraph 2). Passed.
- **Test 3 (Expected matching)**: Failed with `KeyError: 'type'` when filtering expected JSON by `node['type'] == 'TypstEquation'`.

Tests 1 and 2 confirm that OMML tag presence is a reliable detection signal. Test 3 failed due to the same JSON serialization mismatch seen in table and figure tests.

## Findings

- **`m:oMathPara` reliably indicates display equations**: When this tag is present, the entire paragraph is a block-level equation.
- **`m:oMath` reliably indicates inline equations**: When this tag is present without `m:oMathPara`, the equation is inline and mixed with text.
- **OMML detection is 100% accurate in this document**: All expected equations were found, and no false positives occurred.
- **JSON serialization issue**: The expected IR JSON lacks `type` fields, breaking type-based assertions in test scripts.

## Recommendations for Phase 2

1. **Use OMML tags for equation detection**:
   - `m:oMathPara` present → map to `TypstEquation` with `display=True`
   - `m:oMath` present without `m:oMathPara` → map to `TypstEquation` with `display=False`
2. **Detect inline equations at the paragraph XML level**: Scan the paragraph's `<w:p>` element for `{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath`.
3. **Handle mixed content for inline equations**: Inline equations appear alongside regular text runs. The mapping logic should preserve surrounding text while extracting the equation for the IR node.
4. **Fix expected JSON serialization** to include `type` fields, or adapt test scripts to identify equations by the presence of a `latex` attribute instead of `type`.
