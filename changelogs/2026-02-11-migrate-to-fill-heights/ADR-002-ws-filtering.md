# ADR-002: Wind Speed Filtering for WD Fitting

## Status
Accepted

## Context
Wind direction measurements are unreliable at low wind speeds. We need to filter out timestamps where wind speed is below a threshold to ensure quality WD fitting.

## Decision
Implement WS filtering with:
- **Threshold**: 2.5 m/s (industry standard)
- **Sensor selection**: Find nearest WS sensor within 20m height difference
- **Fallback**: If no WS sensor, proceed with warning (no filtering)
- **Implementation**: Filter DataFrame once before processing loop

```python
def _find_nearby_ws_sensor(timeseries, target_height, max_height_diff=20.0):
    # Find closest WS sensor within height range
    
# Filter once
if ws_sensor:
    base_df = timeseries.df.filter(pl.col(ws_col) > ws_threshold)
```

## Consequences

### Positive
- More reliable WD fitting
- Configurable threshold
- Clear fallback behavior

### Negative
- Requires WS sensor nearby
- May reduce data volume significantly

## Alternatives Considered
1. **No filtering**: Would include unreliable low-wind data
2. **Hardcoded threshold**: Less flexible
3. **Filter per height pair**: Inefficient (filter once is better)

## References
- Plan: `.sisyphus/plans/improve-wd-fitting-comprehensive.md`
