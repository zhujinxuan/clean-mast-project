---
id: serialization-001-cli-boundary
name: cli-boundary
description: Serialization at CLI boundary for type-safe IR layer
tags: [serialization, ir, typst, cli, boundary]
applies_when:
  - generating Typst reports
  - converting IR to output format
  - handling file I/O at boundaries
---

# SERIALIZATION-001: CLI Boundary Pattern

## Constraint (MUST)
1. **Domain layer defines IR types** - Now in `packages/typst_ir` package
   - Pydantic models: TypstDocument, TypstTable, etc.
   - Frozen models for safety and hashability
   - No dependencies on infrastructure
2. **Infrastructure layer provides pure serializers** - `typst_ir.serializer`
   - Converts IR to output format (Typst markup)
   - No file I/O, no side effects
3. **Adapter layer (CLI) handles serialization and file I/O** - Imports from `typst_ir`
   - Calls builder to create IR objects using `typst_ir` nodes
   - Calls `serialize(doc)` → gets markup string
   - Writes to file
4. **Separate IR construction from serialization** - Business logic must not mix with infrastructure concerns
5. **Type safety for document structure** - Verify structure via Pydantic validation
6. **JSON-based rendering pipeline** - IR can be serialized to/from JSON for CLI boundaries
   - `model_dump_json()` for JSON output
   - `model_validate_json()` for JSON input
7. **Pydantic models for validation** - All IR nodes use Pydantic BaseModel for automatic validation

## Rationale (WHY)

The assessment subdomain generates Typst reports. Previously, report generation mixed IR construction, serialization, and file I/O in the builder. This violated clean architecture principles:
- Business logic (IR construction) was mixed with infrastructure concerns (serialization, file I/O)
- No type safety for document structure
- Difficult to test and extend

This follows "Parse, don't validate" philosophy:
- Parse untrusted input at boundaries (not applicable here, but similar principle)
- Keep internal representation type-safe
- Serialize only at output boundaries

## Anti-Pattern (AVOID)

```python
# ❌ Mixing IR construction with serialization in builder
class ReportBuilder:
    def build(self):
        doc = TypstDocument(...)
        markup = doc.to_typst()  # NEVER - serialization in domain
        with open("report.typ", "w") as f:
            f.write(markup)  # NEVER - file I/O in domain

# ❌ Untyped document structure
def generate_report():
    return {"title": "...", "sections": [...]}  # NEVER - use IR types

# ❌ Serializer with side effects
def serialize(doc: TypstDocument) -> str:
    logger.info("Serializing...")  # NEVER - keep pure
    save_to_cache(doc)  # NEVER - no side effects

# ❌ Manual dict construction instead of Pydantic models
doc_dict = {
    "children": [
        {"type": "TypstHeading", "text": "Title", "level": 1}
    ]
}  # NEVER - use TypstDocument model directly
```

## Correct Pattern (USE)

```python
# ✅ Import IR types from typst_ir package
from typst_ir import TypstDocument, TypstHeading, TypstParagraph
from typst_ir.renderer import render_to_typst, render_to_pdf

# ✅ Domain layer: IR types (frozen Pydantic models)
doc = TypstDocument(children=[
    TypstHeading(text="Report", level=1),
    TypstParagraph(text="Content here..."),
])

# ✅ Infrastructure layer: Pure serializer
from typst_ir import serialize
markup = serialize(doc)  # Converts to string

# ✅ JSON serialization for CLI boundaries
json_str = doc.model_dump_json()
doc = TypstDocument.model_validate_json(json_str)

# ✅ Adapter layer (CLI): Orchestration with rendering
markup = render_to_typst(json_str)  # JSON -> Typst markup
pdf_path = render_to_pdf(json_str, output_dir)  # JSON -> PDF
docx_path = render_to_docx(json_str, output_dir)  # JSON -> DOCX
```

## Consequences

### Positive
- Type safety: Document structure verified via Pydantic at runtime
- Testability: IR nodes easy to construct and assert (JSON round-trip supported)
- Separation of concerns: Business logic vs. infrastructure
- Extensibility: Can add new output formats (HTML, PDF-direct) by adding serializers
- Backward compatibility: Old build() path preserved
- Package reusability: `typst_ir` is a standalone package usable by other projects
- CLI-friendly: JSON serialization enables language-agnostic boundaries

### Negative
- Additional layer of abstraction
- More code to maintain (IR types + serializers)
- Migration effort for existing sections
- Pydantic dependency adds overhead

## Phase Links
| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/serialization-001-cli-boundary/on-plan.md) |
| Review Plan | [review-plan.md](./phases/serialization-001-cli-boundary/review-plan.md) |
| Code | [code.md](./phases/serialization-001-cli-boundary/code.md) |
| Review | [review-implementation.md](./phases/serialization-001-cli-boundary/review-implementation.md) |

## Related ADRs
- [structure-001-subdomain-layout.md](structure-001-subdomain-layout.md) - Domain layer purity
- [platform-001-cross-platform-paths.md](platform-001-cross-platform-paths.md) - POSIX paths at boundaries

## References
- "Parse, Don't Validate" by Alexis King
- Clean Architecture by Robert C. Martin
