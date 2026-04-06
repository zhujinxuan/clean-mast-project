## LEARNINGS: Turbulence Atoms Implementation

### Reference Patterns

#### 1. Schema Pattern
- Use dataframely (dy) for schema definitions
- Include nullable=False for required fields, nullable=True for optional
- Add constraints like min/max for integers
- Location: `value_objects/single_mast/schemas.py`

#### 2. Atom Pattern
- All atoms inherit from `ReportAtom[Schema, SingleMastMeta]`
- Use @dataclass decorator
- Implement 3 methods: renderTable(), renderImage(), renderSummary()
- Content-addressable caching: `get_or_compute_df_hashkey()`
- Altair rendering with `vl_convert` (vlc) for PNG export
- Location: `entities/single_mast/` (NOT value_objects/ - per ddd-t-002)

#### 3. Altair → PNG Workflow
```python
import altair as alt
import vl_convert as vlc

chart = alt.Chart(df).mark_*(...).encode(...)
png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
image_path.write_bytes(png_bytes)
```

#### 4. Meta utilities
- `get_height_display_name(height, marker)` for height display with interpolation marker
- `SingleMastMeta` for mast metadata (mast_name, location, etc.)

#### 5. IEC Categories (per plan)
- A+: I_ref = 0.18
- A: I_ref = 0.16
- B: I_ref = 0.14
- C: I_ref = 0.12
- Formula: TI_IEC = I_ref * (0.75 + 5.6/V)

#### 6. Meteodyn WT Format
- First line: number of wind speed bins
- Each row: v_max + 16 sector TI values (tab-delimited)
- Example:
  ```
  28
  2.0 0.12 0.13 ... 0.11
  3.0 0.11 0.12 ... 0.10
  ```

### Key Formulas

```
TI = σ / max(μ, 1.0)
TI_rep = mean(TI) + 1.28 * std(TI)  # P90 representative TI
```

### Atom-specific Requirements

1. **SingleMastTurbulenceIntensityAtom**
   - Line chart: representative TI vs wind speed
   - IEC band fills using Altair area marks
   - One chart per height

2. **SingleMastTurbulenceSectorAtom**
   - Polar bar chart: TI by direction sector
   - mark_arc with radius = TI values
   - 16 sectors (N, NNE, NE, ..., NNW)

3. **SingleMastTurbulenceMultiHeightAtom**
   - Combined plot with IEC reference bands
   - Multiple height TI lines on same chart
   - Different colors per height

4. **SingleMastTurbulenceSummaryAtom**
   - Summary table: height | wind range | mean TI | rep TI | IEC category
   - No image (table only)
   - Chinese summary with classification stats

### TurbulenceCalculator Implementation - 2024-03-14

**Key Implementation Details:**
- Follows WeibullFitter/WindTemporalAnalyzer pattern for domain service structure
- Uses polars DataFrame operations for grouping and aggregation
- IEC Categories: A+ (0.18), A (0.16), B (0.14), C (0.12)
- MIN_SAMPLES = 10 threshold for reliable statistics
- Uses Sequence[float | None] for ti_values parameter (covariant)
- AnalysisMetadata.time_range expects str, not tuple[datetime, datetime]

**Type-Safe Patterns:**
- Cast numpy results: float(np.mean(values)) to avoid floating[Any]
- Use Sequence instead of list for function parameters (covariance)
