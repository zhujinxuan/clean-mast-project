## SingleMastDailyPatternAtom Implementation

**Date**: 2026-03-13
**Task**: Create daily pattern atom for single mast analysis

### Implementation Notes

1. **File Location**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/daily_pattern.py`

2. **Class Structure**:
   - Inherits from `ReportAtom[TemporalPatternSchema, SingleMastMeta]`
   - Follows the same pattern as `SingleMastWindTimeseriesAtom` in `timeseries.py`
   - Uses `@dataclass` decorator
   - Implements all 3 abstract methods: `renderTable()`, `renderImage()`, `renderSummary()`

3. **Key Features**:
   - **renderTable()**: 24-hour table with columns for each height (hour vs avg speed per height)
   - **renderImage()**: Altair line chart with points at each hour, X-axis 0-23, Y-axis mean wind speed, multi-line (one per height), filtered to heights >= 100m
   - **renderSummary()**: Chinese narrative describing daily pattern characteristics (peak/min hours, variation stats)

4. **Data Aggregation**:
   - Groups by hour and height
   - Calculates mean of `mean_speed` across all days for each hour
   - Filters to heights >= 100m for visualization

5. **Pattern Consistency**:
   - Same imports as timeseries.py
   - Same ADR-GUARDRAILS header
   - Same method signatures
   - Same caching strategy via base class

### Verification
- Import test passed ✓
- All required methods present ✓
