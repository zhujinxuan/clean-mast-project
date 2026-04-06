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
1. **Domain layer defines IR types** - `subdomains/assessment/domain/types/ir.py`
   - Frozen dataclasses: TypstDocument, TypstTable, etc.
   - No dependencies on infrastructure
2. **Infrastructure layer provides pure serializers** - `infrastructure/typst_ir/serializer.py`
   - Converts IR to output format (Typst markup)
   - No file I/O, no side effects
3. **Adapter layer (CLI) handles serialization and file I/O** - `adapters/cli/generate_report.py`
   - Calls `builder.build_typst()` → returns IR
   - Calls `serialize(doc)` → gets markup string
   - Writes to file
4. **Separate IR construction from serialization** - Business logic must not mix with infrastructure concerns
5. **Type safety for document structure** - Verify structure at compile time

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
```

## Correct Pattern (USE)

```python
# ✅ Domain layer: IR types (frozen dataclasses)
from dataclasses import dataclass

@dataclass(frozen=True)
class TypstDocument:
    title: str
    sections: tuple[TypstSection, ...]

# ✅ Infrastructure layer: Pure serializer
def serialize(doc: TypstDocument) -> str:
    """Convert IR to Typst markup. Pure function, no side effects."""
    return f"#set document(title: \"{doc.title}\")\n..."

# ✅ Adapter layer (CLI): Orchestration
def generate_report(builder: ReportBuilder, output_path: Path):
    doc = builder.build_typst()  # Returns IR
    markup = serialize(doc)      # Converts to string
    output_path.write_text(markup)  # File I/O at boundary
```

## Consequences

### Positive
- Type safety: Document structure verified at compile time
- Testability: IR nodes easy to construct and assert
- Separation of concerns: Business logic vs. infrastructure
- Extensibility: Can add new output formats (HTML, PDF-direct) by adding serializers
- Backward compatibility: Old build() path preserved

### Negative
- Additional layer of abstraction
- More code to maintain (IR types + serializers)
- Migration effort for existing sections

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
