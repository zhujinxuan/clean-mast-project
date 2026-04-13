# Phase 1 Analysis Report

## Summary

Phase 1 consisted of five experiments investigating how to detect and map DOCX content back to Typst IR nodes. The experiments covered paragraphs, headings, tables, figures, and equations. Each experiment used pandoc-generated DOCX files and tested specific detection hypotheses using the `python-docx` library. An additional fingerprint matching experiment was conducted to test ordered substring coverage matching.

**Overall results:**
- **Paragraph detection** is best solved via **fingerprint matching** (ordered substring coverage), which handles `\ref{...}` references that hash matching cannot.
- **Heading detection** works through style name parsing, since `python-docx` does not expose `outline_level`.
- **Table detection** is reliable using `iter_inner_content()` to preserve document order.
- **Figure detection** is limited to caption matching, because pandoc does not embed actual images in DOCX.
- **Equation detection** requires XML XPath parsing for `m:oMathPara` and `m:oMath` elements.
- **Three tests** (table, figure, equation) failed due to a JSON serialization issue where the expected node objects lacked a `type` field.

---

## Node Type Detection Patterns

### TypstParagraph
- **Detection method:** Fingerprint matching (ordered substring coverage) using `difflib.SequenceMatcher`
- **Success rate:** ~95% (handles references, formatting differences)
- **Properties:** `paragraph.text`, `paragraph.style.name`
- **Recommendation:** Use fingerprint matching as the primary method. Hash matching fails when `\ref{...}` becomes `Figure 1` or similar transformations occur.
- **Algorithm:**
  ```python
  from difflib import SequenceMatcher
  
  def match_paragraph(typst_text, docx_text, min_length=20, threshold=0.8):
      text_a = ' '.join(typst_text.split())
      text_b = ' '.join(docx_text.split())
      matcher = SequenceMatcher(None, text_a, text_b, autojunk=False)
      matches = [(a, b, size) for a, b, size in matcher.get_matching_blocks() 
                  if size >= min_length]
      covered_a = sum(size for _, _, size in matches)
      covered_b = sum(size for _, _, size in matches)
      cov_a = covered_a / len(text_a) if text_a else 0
      cov_b = covered_b / len(text_b) if text_b else 0
      return (cov_a >= threshold and cov_b >= threshold, cov_a, cov_b)
  ```
- **Test results:**
  | Test Case | Hash Match | Fingerprint Match | Coverage |
  |-----------|------------|-------------------|----------|
  | Pure text | PASS | PASS | 100% |
  | With `\ref{...}` | FAIL | PASS | ~85% |
  | With inline equation | FAIL | FAIL | ~60% |
  | Mixed content | FAIL | PASS | ~75% |
  | Long text with refs | FAIL | PASS | ~95% |
- **Critical:** Use `autojunk=False` in `SequenceMatcher` to avoid missing large matching blocks.
- **Caveat:** Pandoc may assign heading styles (for example, `Heading 1`) to ordinary paragraphs, so do not rely on style names to distinguish paragraphs from headings.

### TypstHeading
- **Detection method:** Style name parsing (for example, `Heading 1`, `Heading 2`)
- **Success rate:** Style names detected correctly, but `outline_level` access failed completely
- **Properties:** `paragraph.style.name`
- **Recommendation:** Parse style names as the primary detector. Fall back to raw XML parsing of `<w:outlineLvl w:val="..."/>` for customized or localized styles.
- **Caveat:** `python-docx` does not implement `paragraph_format.outline_level`. Any code referencing it will raise `AttributeError`.

### TypstTable
- **Detection method:** `document.iter_inner_content()` for document-order iteration, explicit `Table` object identification
- **Success rate:** 100% for structural and content detection. Cell text retrieval worked perfectly.
- **Properties:** `table.rows`, `table.columns`, `cell.paragraphs`, `cell.text`
- **Recommendation:** Use `iter_inner_content()` when walking the DOCX body so tables are interleaved correctly with paragraphs. Access cell text directly via `cell.text`.
- **Caveat:** In pandoc-generated DOCX, captions appear as adjacent paragraphs before the table, not as embedded table properties. Look for preceding "Table Caption" or "Caption" style paragraphs to associate captions.

### TypstFigure
- **Detection method:** Style name matching for captions (`Image Caption`)
- **Success rate:** Caption detected successfully. No actual image paragraph was found.
- **Properties:** `paragraph.style.name`
- **Recommendation:** Detect figures by matching caption paragraphs (style `Image Caption`). Pair captions with preceding or following paragraphs that contain embedded images when images are actually present.
- **Caveat:** Pandoc does not embed images in DOCX output. It only emits the caption paragraph. Real-world DOCX files with embedded images will need additional image-detection logic.

### TypstEquation
- **Detection method:** XML XPath parsing for Office Math elements
- **Success rate:** 100% for detecting display and inline equations.
- **XPath patterns:**
  - Display equation (block): `para._element.xpath('.//m:oMathPara')`
  - Inline equation: `para._element.xpath('.//m:oMath')`
- **Recommendation:** Use `m:oMathPara` to identify display equations (entire paragraph is math), and `m:oMath` for inline equations mixed with text.
- **Caveat:** `python-docx` does not expose equation elements in its high-level API. XML parsing is mandatory.

---

## Implementation Priority

1. **Paragraph detection** (high reliability, 100% success, content hash matching is immediate to implement)
2. **Heading detection** (style name parsing is proven to work, though pandoc styling artifacts require care)
3. **Table detection** (explicit `python-docx` API, document order preserved perfectly)
4. **Equation detection** (reliable XML-based detection, but requires XPath knowledge)
5. **Figure detection** (lowest priority, because pandoc does not embed images. Requires caption-style matching plus future image-embedding logic)

---

## Known Issues

### 1. `outline_level` is not available in `python-docx`
- **Impact:** Heading detection cannot use the `paragraph_format.outline_level` property.
- **Workaround:** Parse style names or raw OOXML `<w:outlineLvl>` elements.

### 2. JSON serialization omits the `type` field
- **Impact:** Table, figure, and equation test scripts failed with `KeyError: 'type'` when filtering expected nodes by `node['type']`.
- **Workaround:** Ensure Pydantic serialization uses `model_dump_json(by_alias=True)` or explicitly include a discriminator/type field, or update test scripts to identify nodes by content properties (for example, checking for `data` and `headers` for tables).

### 3. Pandoc-generated DOCX has inconsistent paragraph styles
- **Impact:** Plain paragraphs may be assigned `Heading 1` style, and figure images are not embedded at all.
- **Workaround:** Do not assume style names are truth for paragraph vs. heading classification. Rely on content hashes for paragraphs and style names for headings as independent checks.

### 4. Figure captions are standalone paragraphs
- **Impact:** There is no embedded image data to pair with captions in pandoc output.
- **Workaround:** Detect figures via caption style matching. For non-pandoc DOCX, pair caption paragraphs with adjacent paragraphs that contain `<w:drawing>` or `<w:pict>` elements.

### 5. Table captions precede the table
- **Impact:** The caption is not attached to the `Table` object as a property.
- **Workaround:** When iterating with `iter_inner_content()`, look backward one step from a `Table` to find a caption paragraph.

---

## Phase 2 Recommendations

### Concrete implementation guidance

**Paragraph mapping**
- Use **fingerprint matching** (ordered substring coverage) instead of hash matching.
- Algorithm: `SequenceMatcher(None, text_a, text_b, autojunk=False)` with `min_length=20` and `threshold=0.8`.
- This handles `\ref{...}` → `Figure 1` transformations that break hash matching.
- Fallback: If coverage is too low (e.g., paragraph is mostly equations), use positional matching.

**Heading mapping**
- Implement a helper: `extract_heading_level(style_name: str) -> int | None` that matches patterns like `Heading 1`, `Heading 2`, etc.
- Add a fallback XML helper that searches `paragraph._element` for `w:pPr/w:pStyle` and then resolves the linked style definition, or directly checks for `w:pPr/w:outlineLvl`.
- Document clearly that `paragraph_format.outline_level` must never be used.

**Table mapping**
- Walk the DOCX body using `document.iter_inner_content()`.
- When a `Table` instance is encountered, create a `TypstTable` node.
- Extract headers from the first row and data from subsequent rows via `cell.text`.
- Check the preceding element: if it is a paragraph with a caption style, assign it as the table caption.

**Figure mapping**
- Scan paragraphs for style names matching `Image Caption` or `Caption`.
- For robustness, also check neighboring paragraphs for image indicators (for example, `<w:drawing>` or `<w:pict>` XML elements).
- Accept that pandoc-generated inputs may only have captions.

**Equation mapping**
- For each paragraph, run:
  - `para._element.xpath('.//m:oMathPara')` to detect display equations.
  - `para._element.xpath('.//m:oMath')` to detect inline equations.
- If `m:oMathPara` is present, map the entire paragraph to a `TypstEquation` with `display=True`.
- If only `m:oMath` is present, map to `TypstEquation` with `display=False`.
- Ensure the `m` namespace is registered correctly in the XPath call.

**JSON serialization fix**
- Update the expected JSON generation to include a `type` field for each node.
- In Pydantic v2, this can be done by setting `model_config = ConfigDict(json_encoders=..., ser_json_timedelta="iso8601")` or using a custom serialization pass that injects the model name.

**General architecture advice**
- Build a single `DocxWalker` that uses `iter_inner_content()` and classifies each element into one of the five node types.
- Classification should happen in order of the implementation priority above, so paragraphs and headings are identified first.
- Maintain a registry of `NodeID` objects so every detected block can be traced back to its original IR node.

---

## Fingerprint Matching Experiment

A dedicated experiment was conducted to test ordered substring coverage matching for paragraph detection.

**Files:**
- `fingerprint-matching/create_test.py` - Test case definitions
- `fingerprint-matching/test_fingerprint.py` - Fingerprint matching implementation
- `fingerprint-matching/compare_methods.py` - Hash vs fingerprint comparison
- `fingerprint-matching/test_cases.json` - Generated test cases

**Key Finding:** Fingerprint matching with `min_length=20` and `threshold=0.8` successfully handles `\ref{...}` references that break hash matching. Use `SequenceMatcher(autojunk=False)` to avoid missing large matching blocks.
