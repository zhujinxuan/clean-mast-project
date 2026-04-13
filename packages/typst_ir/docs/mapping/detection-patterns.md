# DOCX-Typst IR Detection Patterns

> **Status**: Phase 1 Complete - All detection patterns validated through experiments.
>
> **Last Updated**: 2026-04-08

This document describes the detection patterns used to map DOCX content back to Typst IR nodes, enabling round-trip document processing.

## Related Documents

- [ID Injection Strategies](./id-injection.md) - How to inject and preserve mapping IDs
- [Experiments Directory](../../experiments/) - Validation experiments for each pattern

## Overview

When converting from DOCX back to Typst IR, we need to identify which DOCX elements correspond to which IR nodes. This document covers:

1. **Detection methods** for each IR node type
2. **Confidence levels** for matching quality
3. **Fallback strategies** when primary methods fail
4. **Implementation algorithms** with code examples

## Quick Reference

| IR Node | Primary Method | Fallback | Confidence |
|---------|---------------|----------|------------|
| TypstParagraph | Fingerprint matching | Style + Positional | High/Medium |
| TypstHeading | Style name parsing | XML `outlineLvl` | High |
| TypstTable | Structure + Caption | Structure only | High/Medium |
| TypstFigure | Drawing + Caption | Drawing only | High/Medium |
| TypstEquation | XML XPath (`m:oMathPara`) | None | High |

---

## Pandoc DOCX Styles Reference

When using pandoc to convert Typst to DOCX, the following paragraph styles are generated:

| Style | Count | Usage |
|-------|-------|-------|
| `Figure` | 28+ | Image paragraphs (with `<w:drawing>` in runs) |
| `Captioned Figure` | 4+ | Image paragraphs with captions |
| `Image Caption` | 4+ | Caption text after figures |
| `Table Caption` | 4+ | Caption text before tables |
| `Body Text` | 2+ | Regular paragraphs |
| `First Paragraph` | 4+ | First paragraph after heading |
| `Heading 1/2/3` | 17+ | Section headings |

**Key insight**: Regular paragraphs use `Body Text` or `First Paragraph` style, NOT "Normal".

### Drawing Detection

```python
from docx.oxml.ns import qn

# Drawing is inside <w:r> (run), not directly in paragraph
has_drawing = len(para._element.xpath('.//w:drawing')) > 0

# Or check runs:
for run in para.runs:
    if run._element.find(qn('w:drawing')) is not None:
        has_drawing = True
```

---

## 1. TypstParagraph Detection

### Primary: Fingerprint Matching

Fingerprint matching uses ordered substring coverage to match paragraphs even when text has been transformed (e.g., `\ref{fig1}` → `Figure 1`).

```python
from difflib import SequenceMatcher

def match_paragraph(typst_text: str, docx_text: str,
                    min_length: int = 20, threshold: float = 0.8) -> tuple[bool, float, float]:
    """Match paragraphs using ordered substring coverage."""
    text_a = ' '.join(typst_text.split())
    text_b = ' '.join(docx_text.split())

    matcher = SequenceMatcher(None, text_a, text_b, autojunk=False)
    matches = [(a, b, size) for a, b, size in matcher.get_matching_blocks()
               if size >= min_length]

    covered_a = sum(size for a, b, size in matches)
    covered_b = sum(size for a, b, size in matches)

    cov_a = covered_a / len(text_a) if text_a else 0
    cov_b = covered_b / len(text_b) if text_b else 0

    is_match = cov_a >= threshold and cov_b >= threshold
    return is_match, cov_a, cov_b
```

### Fallback Strategy

```python
def match_paragraph_with_fallback(typst_text, docx_para, ir_index, docx_index):
    """Match paragraph with multiple fallback strategies."""

    # Primary: Fingerprint matching
    is_match, cov_a, cov_b = match_paragraph(typst_text, docx_para.text)
    if is_match:
        return {'method': 'fingerprint', 'confidence': 'high', 'coverage': (cov_a, cov_b)}

    # Fallback 1: Style-based (for short text)
    if len(typst_text) < 20:
        style = docx_para.style.name if docx_para.style else ''
        if 'Heading' in style:
            return {'method': 'style_heading', 'confidence': 'medium', 'coverage': None}
        if 'Caption' in style:
            return {'method': 'style_caption', 'confidence': 'medium', 'coverage': None}
        if 'Body Text' in style or 'First Paragraph' in style:
            return {'method': 'style_body', 'confidence': 'low', 'coverage': None}

    # Fallback 2: Positional matching
    return {'method': 'positional', 'confidence': 'low', 'coverage': None}
```

### Confidence Levels

| Method | Confidence | When Used |
|--------|------------|-----------|
| Fingerprint (cov ≥ 0.8) | High | Normal paragraphs with sufficient text |
| Style-based | Medium | Short text (< 20 chars) with known style |
| Positional | Low | Fallback when other methods fail |

### Why Fingerprint Beats Hash

| Test Case | Hash Match | Fingerprint Match | Coverage |
|-----------|------------|-------------------|----------|
| Pure text | PASS | PASS | 100% |
| With `\ref{...}` | FAIL | PASS | ~85% |
| With inline equation | FAIL | FAIL | ~60% |
| Mixed content | FAIL | PASS | ~75% |
| Long text with refs | FAIL | PASS | ~95% |
| Short text | FAIL | FAIL | <20 chars |

**Critical**: Use `SequenceMatcher(None, text_a, text_b, autojunk=False)` - without `autojunk=False`, the matcher misses large matching blocks.

### Experiment Reference

- [experiments/2026-04-08-paragraph/](../../experiments/2026-04-08-paragraph/)
- [experiments/2026-04-08-fingerprint-matching/](../../experiments/2026-04-08-fingerprint-matching/)

---

## 2. TypstHeading Detection

### Primary: Style Name Parsing

```python
import re

def detect_heading_level(para) -> int | None:
    """Detect heading level from paragraph style."""
    # Primary: Style name
    if para.style:
        match = re.search(r'Heading\s*(\d+)', para.style.name, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None
```

### Fallback: XML outlineLvl

```python
from docx.oxml.ns import qn

def detect_heading_level_with_fallback(para) -> int | None:
    """Detect heading level with XML fallback."""
    # Primary: Style name
    if para.style:
        match = re.search(r'Heading\s*(\d+)', para.style.name, re.IGNORECASE)
        if match:
            return int(match.group(1))

    # Fallback: XML outlineLvl (for custom styles)
    pPr = para._element.find(qn('w:pPr'))
    if pPr is not None:
        outlineLvl = pPr.find(qn('w:outlineLvl'))
        if outlineLvl is not None:
            return int(outlineLvl.get(qn('w:val'), '0'))

    return None
```

### Key Findings

- `paragraph_format.outline_level` is NOT available in python-docx API
- Must parse XML directly for `outlineLvl`
- Style name parsing is reliable for pandoc-generated DOCX

### Experiment Reference

- [experiments/2026-04-08-heading/](../../experiments/2026-04-08-heading/)

---

## 3. TypstTable Detection

### Primary: Structure Matching

```python
from docx.table import Table
from docx.text.paragraph import Paragraph

def detect_tables(doc) -> list[tuple[int, Table]]:
    """Detect tables in document order."""
    tables = []
    for i, content in enumerate(doc.iter_inner_content()):
        if isinstance(content, Table):
            tables.append((i, content))
    return tables
```

### Enhanced Matching: Structure + Caption

```python
def match_table(ir_table, docx_table, docx_contents, table_index):
    """Match table using both structure and caption."""

    # Match 1: Table structure (rows x columns)
    ir_rows = len(ir_table.data)
    ir_cols = len(ir_table.headers)
    docx_rows = len(docx_table.rows)
    docx_cols = len(docx_table.columns)

    structure_match = (ir_rows == docx_rows and ir_cols == docx_cols)

    # Match 2: Caption (if present)
    caption_match = None
    caption_text = None
    if ir_table.caption and table_index > 0:
        prev = docx_contents[table_index - 1]
        if isinstance(prev, Paragraph):
            style_lower = prev.style.name.lower() if prev.style else ""
            if 'caption' in style_lower:
                caption_text = prev.text
                is_match, cov_a, cov_b = match_paragraph(ir_table.caption, prev.text)
                caption_match = is_match and cov_a >= 0.8 and cov_b >= 0.8

    # Determine confidence
    if structure_match and caption_match:
        confidence = 'high'
    elif structure_match or caption_match:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'structure': structure_match,
        'caption': caption_match,
        'caption_text': caption_text,
        'confidence': confidence,
        'ir_dims': (ir_rows, ir_cols),
        'docx_dims': (docx_rows, docx_cols),
    }
```

### Confidence Levels

| Match Type | Confidence | Reason |
|------------|------------|--------|
| Structure + Caption | High | Both dimensions and caption match |
| Structure only | Medium | Dimensions match but caption missing/mismatch |
| Caption only | Medium | Caption matches but dimensions unknown |
| Positional only | Low | Same position in sequence |

### Key Findings

- Tables are SEPARATE objects from paragraphs
- `iter_inner_content()` preserves document order (paragraphs AND tables interleaved)
- Caption is typically the preceding paragraph
- Tables may NOT have captions (some tables in test had no caption)

### Experiment Reference

- [experiments/2026-04-08-table/](../../experiments/2026-04-08-table/)

---

## 4. TypstFigure Detection

> **CRITICAL UPDATE**: Previous Phase 1 finding was incorrect. We tested with `--no-docx` which strips images.
> When running pandoc WITHOUT `--no-docx`, images ARE embedded!

### Real DOCX Structure (with images)

```
word/media/
├── rId9.png      # Embedded images (32 files in test)
├── rId12.png
└── ...

Paragraph styles:
- "Figure" or "Captioned Figure" → Paragraph contains <w:drawing>
- "Image Caption" → Caption text (separate paragraph)
- "Table Caption" → Table caption
```

### Primary: Drawing Detection + Caption Matching

```python
from docx.text.paragraph import Paragraph

def detect_figures(doc) -> list[dict]:
    """Detect figures with drawing and caption info."""
    figures = []
    contents = list(doc.iter_inner_content())

    for i, content in enumerate(contents):
        if isinstance(content, Paragraph):
            # Check for drawing in runs (not directly in paragraph!)
            has_drawing = len(content._element.xpath('.//w:drawing')) > 0

            if has_drawing:
                # Look for caption in next element
                caption = None
                caption_index = None
                if i + 1 < len(contents):
                    next_content = contents[i + 1]
                    if isinstance(next_content, Paragraph):
                        next_style = next_content.style.name.lower() if next_content.style else ""
                        if 'caption' in next_style:
                            caption = next_content.text
                            caption_index = i + 1

                figures.append({
                    'index': i,
                    'style': content.style.name,
                    'has_drawing': True,
                    'caption': caption,
                    'caption_index': caption_index,
                })

    return figures
```

### Enhanced Matching: Drawing + Caption

```python
def match_figure(ir_figure, docx_para, docx_contents, para_index):
    """Match figure using both drawing presence and caption."""

    # Match 1: Drawing presence
    has_drawing = len(docx_para._element.xpath('.//w:drawing')) > 0

    # Match 2: Caption (if present)
    caption_match = None
    if ir_figure.caption and para_index + 1 < len(docx_contents):
        next_content = docx_contents[para_index + 1]
        if hasattr(next_content, 'style') and next_content.style:
            if 'caption' in next_content.style.name.lower():
                is_match, cov_a, cov_b = match_paragraph(ir_figure.caption, next_content.text)
                caption_match = is_match and cov_a >= 0.8 and cov_b >= 0.8

    # Determine confidence
    if has_drawing and caption_match:
        confidence = 'high'
    elif has_drawing or caption_match:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'drawing': has_drawing,
        'caption': caption_match,
        'confidence': confidence,
    }
```

### Confidence Levels

| Match Type | Confidence | Reason |
|------------|------------|--------|
| Drawing + Caption | High | Both drawing and caption match |
| Drawing only | Medium | Drawing found but caption missing/mismatch |
| Caption only | Medium | Caption matches but no drawing |
| Style only | Low | Only style indicates figure |

### Key Findings

1. **Images ARE embedded** when using pandoc without `--no-docx`
2. **Drawing elements**: `<w:drawing>` inside `<w:r>` (run), NOT directly in paragraph
3. **Caption styles**: `Image Caption`, `Table Caption`, `Captioned Figure`
4. **Figure paragraphs**: Have `Figure` or `Captioned Figure` style + `<w:drawing>` in runs
5. **Mapping**: Figure paragraph (with drawing) + following caption paragraph → TypstFigure

### Detection Priority

1. Check for `<w:drawing>` element in runs (primary)
2. Check style name for `Figure` or `Captioned Figure`
3. Look for following `Image Caption` paragraph
4. Match caption text with fingerprint matching

### Experiment Reference

- [experiments/2026-04-08-figure/](../../experiments/2026-04-08-figure/) - Original (with `--no-docx`)
- [experiments/2026-04-08-docx-figures/](../../experiments/2026-04-08-docx-figures/) - Corrected (with images)

---

## 5. TypstEquation Detection

### Primary: XML XPath Detection

```python
from docx.oxml.ns import qn

def detect_equation(para) -> str | None:
    """Detect equation type from paragraph."""
    has_math_para = para._element.find(qn('m:oMathPara')) is not None
    has_math = bool(para._element.xpath('.//m:oMath'))

    if has_math_para:
        return 'display'  # TypstEquation(display=True)
    elif has_math:
        return 'inline'   # TypstEquation(display=False)

    return None
```

### Key Findings

- `m:oMathPara` = display equation (entire paragraph is math)
- `m:oMath` = inline equation (can be mixed with text)
- python-docx does NOT expose equation elements in high-level API
- Must use XPath for detection

### Experiment Reference

- [experiments/2026-04-08-equation/](../../experiments/2026-04-08-equation/)

---

## Sequential Matching Algorithm

The complete algorithm for matching DOCX content to IR nodes:

```python
from dataclasses import dataclass
from typing import Literal
from docx.table import Table
from docx.text.paragraph import Paragraph

@dataclass
class MappingResult:
    ir_node_id: str
    ir_node_type: str
    docx_index: int
    method: str  # 'fingerprint', 'style', 'structure', 'drawing', 'positional'
    confidence: Literal['high', 'medium', 'low']
    details: dict

def match_docx_to_ir(doc, ir_nodes: list) -> list[MappingResult]:
    """Match DOCX content to IR nodes with confidence tracking."""
    mappings = []
    ir_index = 0
    contents = list(doc.iter_inner_content())

    for i, content in enumerate(contents):
        if ir_index >= len(ir_nodes):
            break

        ir_node = ir_nodes[ir_index]

        if isinstance(content, Paragraph):
            if ir_node.type == 'TypstParagraph':
                result = match_paragraph_with_fallback(
                    ir_node.text, content, ir_index, i
                )
                if result['confidence'] != 'low' or i == ir_index:
                    mappings.append(MappingResult(
                        ir_node_id=ir_node.id,
                        ir_node_type='TypstParagraph',
                        docx_index=i,
                        method=result['method'],
                        confidence=result['confidence'],
                        details={'coverage': result['coverage']}
                    ))
                    ir_index += 1

            elif ir_node.type == 'TypstHeading':
                level = detect_heading_level(content)
                if level == ir_node.level:
                    mappings.append(MappingResult(
                        ir_node_id=ir_node.id,
                        ir_node_type='TypstHeading',
                        docx_index=i,
                        method='style',
                        confidence='high',
                        details={'level': level}
                    ))
                    ir_index += 1

            elif ir_node.type == 'TypstFigure':
                result = match_figure(ir_node, content, contents, i)
                if result['confidence'] != 'low':
                    mappings.append(MappingResult(
                        ir_node_id=ir_node.id,
                        ir_node_type='TypstFigure',
                        docx_index=i,
                        method='drawing' if result['drawing'] else 'caption',
                        confidence=result['confidence'],
                        details=result
                    ))
                    ir_index += 1

            elif ir_node.type == 'TypstEquation':
                eq_type = detect_equation(content)
                if eq_type == 'display' and ir_node.display:
                    mappings.append(MappingResult(
                        ir_node_id=ir_node.id,
                        ir_node_type='TypstEquation',
                        docx_index=i,
                        method='xpath',
                        confidence='high',
                        details={'type': eq_type}
                    ))
                    ir_index += 1

        elif isinstance(content, Table):
            if ir_node.type == 'TypstTable':
                result = match_table(ir_node, content, contents, i)
                mappings.append(MappingResult(
                    ir_node_id=ir_node.id,
                    ir_node_type='TypstTable',
                    docx_index=i,
                    method='structure' if result['structure'] else 'caption',
                    confidence=result['confidence'],
                    details=result
                ))
                ir_index += 1

    return mappings
```

---

## Implementation Notes

This section documents details of the current implementation in `typst_ir.mapping.detection` and `typst_ir.mapping.matcher`.

### Fingerprint Matching Normalization

Before matching, both Typst and DOCX texts are normalized via `_normalize_whitespace()`, which collapses all whitespace runs into single spaces and strips leading or trailing whitespace. This ensures that line breaks, multiple spaces, or tab characters do not break matching.

Fingerprint matching is robust against reference substitution. For example, when pandoc renders ``\ref{fig1}`` to ``Figure 1``, the shared surrounding text still produces long matching blocks via `SequenceMatcher`.

Critical implementation detail: `SequenceMatcher(None, text_a, text_b, autojunk=False)` must be used. Without `autojunk=False`, the matcher may discard large matching blocks.

### Confidence Thresholds

Confidence is computed at three discrete levels based on match quality:

| Level | Threshold | When Assigned |
|-------|-----------|---------------|
| High | `>= 0.8` | Fingerprint coverage on both sides, or combined structure + caption match |
| Medium | `>= 0.5` | Style-based short-text match, or single-factor match (structure only, drawing only, caption only) |
| Low | `< 0.5` | Positional fallback, hash fallback, or no strong signal |

Note: the `0.5` boundary is implicit in method selection rather than an explicit floating-point comparison for all node types. Table and figure matching use structural logic instead of coverage fractions.

### Fallback Hierarchy for Paragraphs

`match_paragraph_with_fallback()` implements the following cascade:

1. **Fingerprint** - ordered substring coverage with `threshold=0.8` and `min_length=20` (high confidence).
2. **Style detection** - for short text (`< 20 chars`): checks paragraph style for `Heading`, `Caption`, or `Body Text` (medium or low confidence).
3. **Hash matching** - tertiary fallback for very short body text: SHA-256 of normalized text (low confidence).
4. **Positional fallback** - final fallback based on document sequence position (low confidence).

### Heading Detection

`detect_heading_level()` uses two strategies in order:

1. **Style name parsing** - regex search for `Heading N` (case-insensitive) in `paragraph.style.name`.
2. **XML `outlineLvl` fallback** - if the style name does not match, the function searches the paragraph XML (`w:pPr/w:outlineLvl`) for the `w:val` attribute. This catches custom styles that are not named "Heading N".

### Table Detection

`detect_tables()` iterates over `doc_document.iter_inner_content()` and collects all `Table` instances, preserving interleaved document order.

`match_table()` evaluates two signals:

- **Structure**: compares IR dimensions (`len(data)` rows, `len(headers)` columns) to DOCX dimensions (`len(table.rows)`, `len(table.columns)`).
- **Caption**: if the IR table has a caption, the function looks at the immediately preceding paragraph. If that paragraph has a caption style, fingerprint matching is applied to the caption text.

Confidence logic:

- `high` - structure matches AND caption matches
- `medium` - exactly one of structure or caption matches
- `low` - neither matches

### Figure Detection

`detect_figures()` iterates over `iter_inner_content()` and identifies paragraphs containing `<w:drawing>` via XPath `.//w:drawing`. For each figure paragraph, it checks the next element in sequence; if that element is a `Paragraph` with `caption` in its style name, the caption is recorded.

`match_figure()` uses the same signals:

- `drawing` - `True` when the paragraph contains `<w:drawing>`
- `caption` - `True` when the following paragraph's caption text passes fingerprint matching

### Equation Detection

`detect_equation()` searches paragraph XML for Office Math (OMML) elements:

- `m:oMathPara` present → returns `"display"` (block equation)
- `m:oMath` present but no `m:oMathPara` → returns `"inline"`
- neither present → returns `None`

---

## Usage Examples

### Using `DocxMatcher` for Sequential Matching

The recommended way to match an entire document is via `DocxMatcher`:

```python
from docx import Document
from typst_ir import TypstDocument, TypstHeading, TypstParagraph
from typst_ir.mapping.matcher import DocxMatcher

# Build IR nodes
ir_doc = TypstDocument(children=[
    TypstHeading(text="Executive Summary", level=1),
    TypstParagraph(text="Revenue increased by 12% year over year."),
    TypstParagraph(text="Operating margin remained steady at 18%."),
])
ir_nodes = ir_doc.children

# Match against DOCX
doc = Document("report.docx")
matcher = DocxMatcher()
mappings = matcher.match(ir_nodes, doc)

# Review mappings
for entry in mappings:
    print(f"{entry.node_type} @ DOCX {entry.source_start}")
    print(f"  method={entry.method.value} confidence={entry.confidence.value}")
```

### Low-Level Detection Functions

For custom matching logic, use the detection functions directly:

```python
from docx import Document
from typst_ir.mapping.detection import (
    match_paragraph_with_fallback,
    detect_heading_level,
    detect_equation,
)

doc = Document("report.docx")
para = doc.paragraphs[0]

# Paragraph matching
result = match_paragraph_with_fallback(
    "Executive Summary", para, ir_index=0, docx_index=0
)
print(result["method"], result["confidence"])

# Heading detection
level = detect_heading_level(para)
print(level)  # 1, 2, 3, ... or None

# Equation detection
eq_type = detect_equation(para)
print(eq_type)  # "display", "inline", or None
```

---

## Known Issues

1. **`outline_level` not in python-docx API** - Must parse XML
2. **Drawing in runs, not paragraphs** - `<w:drawing>` is inside `<w:r>` (run), must use `xpath('.//w:drawing')`
3. **Tables may lack captions** - Some tables have no caption; rely on structure matching
4. **Paragraph styles vary** - Regular paragraphs use `Body Text` or `First Paragraph`, NOT "Normal"
5. **Inline equations reduce coverage** - Paragraphs with many equations may not match fingerprint
6. **Short text may not match** - Minimum substring length threshold (20 chars); use style-based fallback

---

## Confidence-Based Matching Strategy

When fingerprint matching fails, use cascading fallbacks:

```
High Confidence:
  - Fingerprint match (coverage ≥ 0.8)
  - Style match for headings
  - Structure + caption match for tables/figures
  - XPath match for equations

Medium Confidence:
  - Style match for short text (< 20 chars)
  - Structure only for tables
  - Drawing only for figures
  - Caption only for tables/figures

Low Confidence:
  - Positional matching (same index in sequence)
  - Style match for body text
```

Implementation should:
1. Try primary method first
2. Fall back to secondary methods
3. Record confidence level for each mapping
4. Allow downstream consumers to filter by confidence

---

## References

- [ID Injection Strategies](./id-injection.md)
- [python-docx Documentation](https://python-docx.readthedocs.io/)
- [ECMA-376](https://www.ecma-international.org/publications-and-standards/standards/ecma-376/) - Office Open XML specification
- `typst_ir.mapping` - Current implementation