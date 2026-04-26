# Typst IR

Typst Intermediate Representation for document processing.

## Overview

`typst_ir` provides type-safe, immutable Pydantic models for representing Typst documents as an intermediate representation (IR). It enables:

- **Type-safe document construction** using frozen Pydantic BaseModels
- **JSON serialization** for CLI boundaries and inter-process communication
- **Multi-format rendering** to Typst markup, PDF, and DOCX
- **Optional validation** using tree-sitter or regex fallback

## Installation

From the workspace root:

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install typst-ir
```

## Quick Start

Create a document, serialize to JSON, and render to PDF:

```python
from typst_ir import TypstDocument, TypstSection, TypstHeading, TypstParagraph, TypstTable
from typst_ir.renderer import render_to_pdf
from pathlib import Path

# Create a document
doc = TypstDocument(children=[
    TypstSection(
        heading=TypstHeading(text="Wind Energy Report", level=1),
        body=[
            TypstParagraph(text="This report analyzes wind data from meteorological towers."),
            TypstTable(
                headers=["Height (m)", "Wind Speed (m/s)", "Direction (°)"],
                data=[
                    ["50", "8.5", "270"],
                    ["80", "9.2", "265"],
                    ["100", "9.8", "260"],
                ],
                caption="Wind measurements at different heights",
            ),
        ],
        subsections=[],
    ),
])

# Serialize to JSON for CLI boundaries
json_str = doc.model_dump_json()

# Render to PDF
pdf_path = render_to_pdf(json_str, Path("./output"))
print(f"PDF saved to: {pdf_path}")
```

## Node Types

The `typst_ir` package provides 11 node types for building documents:

### Document Structure

| Node | Description | Key Attributes |
|------|-------------|----------------|
| `TypstDocument` | Root container | `children: list[TypstSection]` |
| `TypstSection` | Grouped content with heading | `heading: TypstHeading, body: list[TypstBodyBlock], subsections: list[TypstSection]` |
| `TypstHeading` | Section headings | `text: str, level: int` |

### Content Blocks

| Node | Description | Key Attributes |
|------|-------------|----------------|
| `TypstParagraph` | Plain text paragraphs | `text: str` |
| `TypstTable` | Tabular data | `data: list[list[str]], headers: list[str], caption: str \| None` |
| `TypstFigure` | Images and diagrams | `content: str, caption: str, kind: str` |
| `TypstEquation` | LaTeX math equations | `latex: str, display: bool` |
| `TypstCodeBlock` | Syntax-highlighted code | `text: str, language: str \| None` |
| `TypstRawBlock` | Unprocessed content | `format: str, text: str` |

### Lists

| Node | Description | Key Attributes |
|------|-------------|----------------|
| `TypstBulletList` | Unordered lists | `items: list[list[TypstBlock]]` |
| `TypstOrderedList` | Numbered lists | `items: list[list[TypstBlock]], start: int` |

### Examples

**Heading with Levels:**
```python
from typst_ir import TypstHeading

heading1 = TypstHeading(text="Main Title", level=1)   # = Main Title
heading2 = TypstHeading(text="Section", level=2)      # == Section
heading3 = TypstHeading(text="Subsection", level=3)   # === Subsection
```

**Table with Caption:**
```python
from typst_ir import TypstTable

table = TypstTable(
    headers=["Parameter", "Value", "Unit"],
    data=[
        ["Mean wind speed", "7.5", "m/s"],
        ["Weibull k", "2.1", "-"],
        ["Air density", "1.225", "kg/m³"],
    ],
    caption="Wind resource parameters",
)
```

**Mathematical Equations:**
```python
from typst_ir import TypstEquation

# Inline equation
inline = TypstEquation(latex="E = mc^2", display=False)

# Display (block) equation
display = TypstEquation(
    latex="P = \\frac{1}{2} \\rho A v^3",
    display=True,
)
```

**Nested Lists:**
```python
from typst_ir import TypstBulletList, TypstParagraph

bullet_list = TypstBulletList(items=[
    [TypstParagraph(text="First item")],
    [TypstParagraph(text="Second item with "), TypstParagraph(text="additional content")],
])
```

## Pydantic Models

All IR nodes are frozen Pydantic `BaseModel` instances, providing:

- **Type validation** at construction time
- **Immutability** via `frozen=True` configuration
- **Hashability** for use in sets and dict keys
- **JSON serialization** with `model_dump_json()`
- **JSON deserialization** with `model_validate_json()`

```python
from typst_ir import TypstParagraph

# Automatic validation
para = TypstParagraph(text="Hello")  # ✓ Works

# Invalid types raise validation errors
para = TypstParagraph(text=123)  # ✗ ValidationError: text must be str

# Models are frozen (immutable)
para = TypstParagraph(text="Hello")
# para.text = "World"  # ✗ FrozenInstanceError
```

## JSON Serialization

The JSON serialization enables CLI boundaries and language-agnostic interfaces:

```python
from typst_ir import TypstDocument, TypstSection, TypstHeading

# Create and serialize
doc = TypstDocument(children=[
    TypstSection(
        heading=TypstHeading(text="Title", level=1),
        body=[],
        subsections=[],
    )
])
json_str = doc.model_dump_json()
# {"children": [{"heading": {"text": "Title", "level": 1, "type": "TypstHeading"}, "body": [], "subsections": [], "type": "TypstSection"}]}

# Deserialize from JSON
doc = TypstDocument.model_validate_json(json_str)
```

## Rendering

The `typst_ir.renderer` module provides high-level rendering functions:

### `render_to_typst(json_str: str) -> str`

Render JSON IR to Typst markup string.

```python
from typst_ir.renderer import render_to_typst

json_str = '{"children": [{"heading": {"text": "Hello", "level": 1, "type": "TypstHeading"}, "body": [], "subsections": [], "type": "TypstSection"}]}'
markup = render_to_typst(json_str)
# Returns: "= Hello\n"
```

### `render_to_pdf(json_str: str, output_dir: Path) -> Path`

Render JSON IR to PDF file using the `typst` CLI.

```python
from typst_ir.renderer import render_to_pdf
from pathlib import Path

pdf_path = render_to_pdf(json_str, Path("./output"))
# Returns: Path("output/report.pdf")
```

**Requirements:** [typst CLI](https://github.com/typst/typst) must be installed.

### `render_to_docx(json_str: str, output_dir: Path) -> Path`

Render JSON IR to DOCX file using `pandoc`.

```python
from typst_ir.renderer import render_to_docx
from pathlib import Path

docx_path = render_to_docx(json_str, Path("./output"))
# Returns: Path("output/report.docx")
```

**Requirements:** [pandoc](https://pandoc.org/) must be installed.

## Tree-Sitter Validation

Optional validation of generated Typst content using tree-sitter:

```python
from typst_ir.validation import validate_typst_content

# Validate Typst markup
result = validate_typst_content("# Heading\n\nSome text.")
print(result.valid)  # True
print(result.errors)  # []
print(result.method)  # "tree-sitter" or "regex"
```

### Setup

Tree-sitter validation requires additional dependencies:

```bash
pip install tree-sitter tree-sitter-typst
```

If tree-sitter is not available, validation falls back to regex-based checks for:
- Balanced delimiters (`{}`, `[]`, `()`)
- Valid escape sequences
- Closed string literals

## Development

### Run Tests

```bash
# Run all tests for the package
uv run pytest packages/typst_ir/tests

# Run with coverage
uv run pytest packages/typst_ir/tests --cov=typst_ir
```

### Baseline Verification

Run the verification baseline to ensure code quality:

```bash
uv run python scripts/verify_baseline.py --package typst_ir
```

This runs:
1. Type checking (`ty`)
2. Linting (`ruff`)
3. Unit tests (`pytest`)

### Project Structure

```
packages/typst_ir/
├── src/typst_ir/
│   ├── __init__.py       # Public API exports
│   ├── nodes.py          # IR node types (Pydantic models)
│   ├── serializer.py     # IR to Typst markup conversion
│   ├── renderer.py       # High-level rendering to PDF/DOCX
│   └── validation.py     # Optional tree-sitter validation
└── tests/
    ├── test_nodes.py           # Node construction tests
    ├── test_serializer.py      # Serialization tests
    ├── test_renderer.py        # Rendering tests
    └── test_validation.py      # Validation tests
```

## API Reference

### Public Exports

```python
from typst_ir import (
    # Node types
    TypstDocument, TypstSection, TypstHeading, TypstParagraph,
    TypstTable, TypstFigure, TypstEquation, TypstCodeBlock, TypstRawBlock,
    TypstBulletList, TypstOrderedList,
    TypstBlock, TypstChild,  # Type aliases
    # Serialization
    serialize,
    # Rendering
    render_to_typst, render_to_pdf, render_to_docx,
    # Validation
    ValidationResult, validate_typst_content, escape_special_chars,
)
```

## License

MIT License - See project root for details.
