# ADR-003: Report Atom Pattern for Modular Report Generation

## Status

Accepted

## Context

The representative year timeseries report generation needed:
1. **Modularity**: Mix/match different report components (wind, power, roses)
2. **Testability**: Each component testable in isolation
3. **Multiple formats**: Same content → Typst, PDF, DOCX
4. **Caching**: Avoid regenerating unchanged content
5. **Python implementation**: Julia already had templates, Python needed equivalent

Existing approaches considered:
- **Template inheritance** (Julia style): Too rigid for Python
- **Function-based**: Hard to test, no standardization
- **Class-based without schema**: No data validation

## Decision

Adopt **Atom pattern**: Self-contained report components with:

### Structure

```python
@dataclass
class ReportAtom(ABC, Generic[T, M]):
    df: DataFrame          # Data
    schema: Type[T]        # Validation schema
    meta: M                # Metadata

    def renderTable(self) -> str: ...
    def renderImage(self, output_dir: Path) -> Path: ...
    def renderSummary(self) -> str: ...
```

### Key Features

1. **Schema Validation**: dataframely schemas validate DataFrame structure
2. **Content-Addressable Caching**: SHA256 hash of DataFrame content
3. **Three Outputs**: Table (Typst), Image (PNG), Summary (Chinese text)
4. **Composition**: ReportBuilder aggregates multiple atoms

### Implementation

Four atoms for representative year report:
- `SingleMastMonthlyWindAtom`: Monthly wind speed analysis
- `SingleMastMonthlyWindPowerAtom`: Wind power density analysis
- `SingleMastMonthlyWindFrequencyRoseAtom`: Direction frequency rose
- `SingleMastWindPowerRoseAtom`: Power distribution by direction

## Consequences

**Positive**:
- **Modular**: Add/remove atoms without affecting others
- **Testable**: Mock DataFrames, test rendering in isolation
- **Type-safe**: Generic types ensure schema/meta compatibility
- **Cached**: Skip regeneration when data unchanged
- **Consistent**: All atoms follow same interface

**Negative**:
- **Boilerplate**: More code than simple functions
- **Learning curve**: Team must understand pattern
- **Generic complexity**: Type parameters add complexity

**Neutral**:
- Requires schema definitions (dataframely dependency)
- Altair for visualization (different from Julia's Plots)

## Alternatives Considered

### 1. Template Inheritance (Julia Style)

**Decision**: Rejected

Julia uses Jinja2 templates with inheritance. Python tried this but:
- Typst syntax harder to template than LaTeX
- Less flexible for conditional content
- Harder to unit test

### 2. Function-Based Approach

**Decision**: Rejected

Simple functions for each component:
- No standardization across components
- Hard to enforce consistent interface
- Caching harder to implement

### 3. Class-Based Without Schema

**Decision**: Rejected

Atoms as classes but no dataframely validation:
- Runtime errors from DataFrame shape mismatches
- No type safety on schema
- Harder to catch errors early

### 4. Monolithic Report Generator

**Decision**: Rejected

Single class generating entire report:
- Not modular
- Hard to test
- No reusability of components

## References

- [C4 Reporting Component](../c4/03-component/reporting.md)
- [Report module source](../../../../packages/cleanmast/src/cleanmast/report/)
- [dataframely documentation](https://github.com/nyggus/dataframely)
- [ADR-001: C4 Model](001-adopt-c4-model.md)
