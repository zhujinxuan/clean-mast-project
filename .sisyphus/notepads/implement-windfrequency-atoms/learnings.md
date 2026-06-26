## LEARNINGS: WindFrequency Atoms Implementation

### Reference Patterns

#### 1. Schema Pattern
- Use dataframely (dy) for schema definitions
- Include nullable=False for required fields
- WindFrequencySchema fields:
  - height (Float64)
  - bin_start, bin_end (Float64) - bin boundaries
  - bin_center (Float64) - center of bin
  - frequency (Float64) - probability 0-1
  - occurrence_hours (Float64) - frequency * 8760
  - power_frequency (Float64) - energy contribution
  - power_hours (Float64) - power frequency * 8760

#### 2. Key Formulas
```
P = 0.5 * ρ * v³  (wind power density)
frequency = count_bin / total_count
power_frequency = sum(power_in_bin) / total_power
occurrence_hours = frequency * 8760 (hours per year)
```

#### 3. Binning Strategy
- 1 m/s bins from 0 to 28 m/s
- 3-25 m/s range for summary (productive wind range)
- Bins: [0,1), [1,2), ..., [27,28), [28,∞)

#### 4. Atom Patterns
- Table atoms: pivot by height for multi-height display
- Distribution atom: grouped bar chart with speed freq and power freq side by side
- Summary atom: 3-25 m/s aggregated statistics

#### 5. Chart Pattern (Grouped Bar)
```python
# Speed frequency bars
speed_bars = alt.Chart(df).mark_bar().encode(
    x=alt.X('bin_center:Q', title='风速(m/s)'),
    y=alt.Y('frequency:Q', title='频率'),
    color=alt.value('#1f77b4')
)

# Power frequency bars (offset)
power_bars = alt.Chart(df).mark_bar().encode(
    x=alt.X('bin_center:Q'),
    y=alt.Y('power_frequency:Q'),
    color=alt.value('#ff7f0e')
)

# Combined with facet or offset
```

---

## DDD Migration: wind_frequency subdomain porting (2026-05-21)

### Batch 1 Pattern Applied
- Entities: 4 files ported to `subdomains/wind_frequency/entities/` with `_atom` suffix
  - `wind_frequency_hours_atom.py`
  - `wind_power_hours_atom.py`
  - `wind_productive_range_atom.py`
  - `wind_distribution_subgrid.py` (no `_atom` suffix - pre-existing naming)
- Value objects: `WindFrequencySchema` extracted to `value_objects/schemas.py`
- Services: `WindFrequencySubsection` ported to `services/wind_frequency_section.py`

### Import Pattern
- **Entities** use relative imports:
  - `ReportAtom` → `....shared.protocols.report_atom` (4 levels up)
  - `TypstParagraph`, `TypstTable` → `....shared.ir_types`
  - `WindFrequencySchema` → `..value_objects.schemas` (2 levels up)
  - `SingleMastMeta` → KEPT absolute path (shared by 7 subdomains, not extracted)
- **Services** use relative imports for entities and shared kernel:
  - Entity imports: `..entities.wind_*`
  - `render_subsection_content` → `....shared.utils.subsection_renderer`
  - `AtomCollection` → `....shared.collections.atom_collection`
  - `TypstHeading`, `TypstSection` → `....shared.ir_types`

### Deprecation Stubs
- 5 files in old `domain/` locations replaced with re-export stubs
- Old `schemas.py` had duplicate `WindFrequencySchema` class removed (re-export only)
- All stubs verified: `old_path.Class is new_path.Class` → `True`

### Verification
- 28/28 atom tests pass
- 31/31 calculator tests pass
- 4/4 subsection tests pass
- LSP diagnostics: 0 errors across wind_frequency subdomain
- Stub identity: all old paths resolve to same objects as new canonical paths
