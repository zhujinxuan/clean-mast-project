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
