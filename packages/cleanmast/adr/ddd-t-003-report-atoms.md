---
id: ddd-t-003-report-atoms
name: report-atoms
description: ReportAtom pattern for content-addressable report components
tags: [ddd, reporting, atom, content-addressable, rendering]
applies_when:
  - creating report components
  - implementing analysis-to-report conversion
  - adding new visualization types
---

# DDD-T-003: Report Atoms

## Status

**Accepted**

## Context

Reports in CleanMast need structured, cacheable, and reusable visualizations. Traditional report generation couples data analysis with presentation, making it difficult to:

- Cache expensive calculations
- Reuse visualizations across reports
- Track dependencies between data and outputs
- Generate incremental updates when only partial data changes

We need a pattern that separates analysis from rendering, enables caching by content identity, and provides polymorphic output capabilities.

## Decision

### 1. ReportAtom is an Entity

ReportAtom is classified as an **Entity** (see [ddd-t-002-entities-value-objects.md](ddd-t-002-entities-value-objects.md)) because:

- It has identity independent of attribute values (via content hash)
- The same data content always produces the same identity
- It tracks its own lifecycle through hash-based reference generation

### 2. Content-Addressable Hashing

Each ReportAtom computes a content hash for efficient caching and identity:

```python
def get_or_compute_df_hashkey(self) -> str:
    """Get content hash - computes once, caches forever."""
    if self._df_hashkey is None:
        buf = io.BytesIO()
        self.df.write_parquet(buf)  # Parquet serialization
        content_hash = hashlib.sha256(buf.getvalue()).hexdigest()[:12]
        atom_type = self.__class__.__name__
        self._df_hashkey = f"{atom_type}_{content_hash}"
    return self._df_hashkey
```

**Rationale for Parquet + SHA256**:
- Parquet provides stable binary representation (unlike CSV or JSON)
- Columnar format preserves data types and precision
- SHA256 provides collision-resistant hashing
- First 12 characters balance brevity with uniqueness (1 in 16^12 collision probability)

### 3. Generic Type Parameters (T, M)

ReportAtom uses two type parameters for compile-time safety:

```python
T = TypeVar("T", bound=SchemaProtocol)  # Schema type for validation
M = TypeVar("M")                        # Metadata type for display

@dataclass
class ReportAtom(ABC, Generic[T, M]):
    df: pl.DataFrame
    schema: type[T]      # Validates df structure
    meta: M              # Display properties (caption, width, etc.)
```

**Benefits**:
- `T` ensures DataFrame matches expected schema at runtime
- `M` allows different metadata types per atom subtype
- Type checking catches mismatches between schema and data

### 4. Polymorphic Rendering Interfaces

All atoms implement three rendering methods for different output contexts:

```python
@abstractmethod
def renderTable(self) -> str:
    """Render as Typst/markdown table."""
    pass

@abstractmethod
def renderImage(self, output_dir: Path, force: bool = False) -> Path:
    """Generate image file, return path."""
    pass

@abstractmethod
def renderSummary(self) -> str:
    """Render as text summary/paragraph."""
    pass
```

**Usage Patterns**:
- `renderTable()` for data tables in reports
- `renderImage()` for charts and visualizations
- `renderSummary()` for narrative text descriptions

### 5. AtomCollection for Composition

Atoms are organized into immutable collections for report assembly:

```python
@dataclass(frozen=True)
class AtomCollection:
    _by_mast: dict[str, list[ReportAtom]]
    _by_key: dict[tuple[str, type[ReportAtom]], ReportAtom]

    def get(self, mast: str, atom_type: type[T]) -> T | None:
        """Get atom by mast and type."""
        
    def get_all_by_type(self, atom_type: type[T]) -> list[T]:
        """Get all atoms of specific type, in mast order."""
```

**Purpose**:
- Organize atoms by mast name
- Efficient lookup by (mast, type) tuple
- Prevent duplicate atom types per mast
- Maintain insertion order for consistent report generation

### 6. Domain-Specific Atom Types

CleanMast defines approximately 25+ concrete atom types organized by analysis domain:

#### Wind Rose Analysis (3 atoms)
- `SingleMastMonthlyWindFrequencyRoseAtom` - 16-sector direction frequency polar chart
- `SingleMastWindPowerRoseAtom` - Wind power density by direction
- `SingleMastMonthlyWindRoseGridAtom` - 3x4 grid of monthly roses

#### Weibull Distribution (3 atoms)
- `SingleMastWeibullParametersAtom` - Table of k, c parameters per height
- `SingleMastWeibullDistributionAtom` - Histogram + PDF overlay per height
- `SingleMastWeibullMultiHeightAtom` - Combined distribution plot (all heights)

#### Turbulence Intensity (4 atoms)
- `SingleMastTurbulenceIntensityAtom` - TI vs wind speed with IEC bands
- `SingleMastTurbulenceSectorAtom` - Sector-wise TI polar chart
- `SingleMastTurbulenceMultiHeightAtom` - Combined TI plot with IEC comparison
- `SingleMastTurbulenceSummaryAtom` - Summary table across heights

#### Wind Frequency (4 atoms)
- `SingleMastWindFrequencyTableAtom` - Frequency by speed bin (all heights)
- `SingleMastWindPowerFrequencyTableAtom` - Power frequency table
- `SingleMastWindFrequencyDistributionAtom` - Grouped bar chart per height
- `SingleMastWindRangeSummaryAtom` - 3-25 m/s range summary

#### Temporal Patterns (7 atoms)
- `SingleMastWindTimeseriesAtom` - Full time series line chart
- `SingleMastDailyPatternAtom` - 24-hour average pattern
- `SingleMastDailyPowerPatternAtom` - 24-hour power pattern
- `SingleMastMonthlyPatternAtom` - Monthly grouped bar chart
- `SingleMastMonthlyPowerPatternAtom` - Monthly power pattern
- `SingleMastMonthlyDailyWindAtom` - 3x4 grid of daily patterns
- `SingleMastMonthlyDailyPowerAtom` - 3x4 grid of daily power patterns

#### Vertical Profile (3 atoms)
- `SingleMastVerticalProfileAtom` - Power law scatter + fit line
- `SingleMastWindShearTableAtom` - Shear statistics per height pair
- `SingleMastWindShearExponentAtom` - Shear exponent matrix

#### Monthly Wind Statistics
- `SingleMastMonthlyWindAtom` - Monthly wind speed statistics table + chart
- `SingleMastMonthlyWindPowerAtom` - Monthly wind power statistics

### 7. Factory Pattern with Validation

Atoms are created through a factory method that validates data:

```python
@classmethod
def create(cls, schema: type[T], df: pl.DataFrame, meta: M) -> ReportAtom[T, M]:
    """Factory: validates once, returns typed atom."""
    validated = schema().validate(df, cast=True)
    instance = cls.__new__(cls)
    instance.df = validated
    instance.schema = schema
    instance.meta = meta
    instance._df_hashkey = None
    return instance
```

**Benefits**:
- Data validation at creation time
- Schema casting for type safety
- Clean initialization without `__init__` boilerplate

### 8. Migration Path from Julia

The Julia ReportAtom pattern uses similar concepts but different syntax:

| Aspect | Julia | Python |
|--------|-------|--------|
| Type parameters | `{T<:Schema, M<:Meta}` | `Generic[T, M]` |
| Data storage | DataFrame | Polars DataFrame |
| Content hash | SHA256 of Arrow | SHA256 of Parquet |
| Rendering | Makie figures | Altair + vl-convert |
| Output | PNG + Typst | PNG + Typst |

**Migration Strategy**:
1. Port analysis logic to domain services (calculators)
2. Create Python schemas with dataframely
3. Implement atoms inheriting from ReportAtom
4. Create analysis-to-atom converters
5. Generate visualizations with Altair instead of Makie

## Rationale (WHY)

- **Content-Addressability**: Same data always produces same reference, enabling automatic caching
- **Polymorphic Rendering**: One atom can generate table, image, and summary from same data
- **Type Safety**: Generic parameters ensure schema and metadata consistency
- **Separation of Concerns**: Analysis (calculators) separated from presentation (atoms)
- **Incremental Updates**: Changed data produces new hash, triggering selective regeneration
- **Testability**: Atoms can be tested independently with mock data

## Consequences

### Positive

- Automatic caching via content hash eliminates redundant regeneration
- Polymorphic rendering supports multiple output formats from single source
- Type-safe generic parameters catch errors at development time
- Analysis-to-atom converters enable flexible report assembly
- Immutable AtomCollection ensures consistent report structure

### Negative

- Content hashing adds overhead for large DataFrames
- Parquet serialization for hashing may be slow for very large datasets
- Generic type parameters add complexity to inheritance
- Three rendering methods per atom increases implementation burden
- Schema validation at creation time may be expensive

## Anti-Patterns (AVOID)

```python
# ❌ Rendering directly in analysis code
def analyze_wind_rose(data) -> Path:
    result = calculate(data)
    fig = create_figure(result)  # Don't do this
    fig.save("output.png")
    return Path("output.png")

# ❌ Skipping content hashing for caching
class MyAtom(ReportAtom[...]):
    def __eq__(self, other):
        return self.df.equals(other.df)  # Don't do this - slow comparison

# ❌ Mutating atom data after creation
atom.df = modified_df  # Don't do this - breaks hash consistency

# ❌ Rendering without output directory parameter
def renderImage(self) -> bytes:  # Don't do this - can't cache to file
    return create_png(self.df)

# ✅ Use ReportAtom pattern with content hashing
class WindRoseAtom(ReportAtom[WindRoseSchema, SingleMastMeta]):
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"rose_{cache_key}.png"
        if not force and image_path.exists():
            return image_path  # Return cached
        # Generate and save
        return image_path

# ✅ Separate analysis from rendering
calculator = WindRoseCalculator()
result = calculator.calculate(input)  # Pure analysis
converter = WindRoseAnalysisToAtoms()
atoms = converter.convert(result, mast_name)  # Analysis → Atoms
```

## References

- Evans, E. "Domain-Driven Design" Chapter 5 - Entities, Chapter 6 - Aggregates
- [ddd-t-001-aggregates.md](ddd-t-001-aggregates.md) - Aggregate pattern and boundaries
- [ddd-t-002-entities-value-objects.md](ddd-t-002-entities-value-objects.md) - Entity classification
- [persistence-001-parquet-storage.md](persistence-001-parquet-storage.md) - Parquet serialization
- [structure-001-subdomain-layout.md](structure-001-subdomain-layout.md) - Folder structure for entities
