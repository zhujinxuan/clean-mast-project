# ADR-003: Base Height Constraint

## Status
Accepted

## Context
Linear regression on scattered WD data may not pass through (dh=0, deg_diff=0). Physically, at the base height, the direction difference should be exactly 0.

## Decision
Add base height constraint to fitting:
- Add constraint points: (dh=0, deg_diff=0)
- One point per valid timestamp
- Forces regression line through origin
- Ensures physical correctness at base height

```python
# Add constraint: one point per timestamp
valid_count = len(base_df)
constraint_df = pl.DataFrame({
    "h_diff": [0.0] * valid_count,
    "deg_diff": [0.0] * valid_count
})
scatter_df = pl.concat([scatter_df, constraint_df])
```

## Consequences

### Positive
- Forces fit through physically correct point
- Improves extrapolation accuracy
- Handles edge cases better

### Negative
- Slightly more computation
- May over-constrain if base data is noisy

## Alternatives Considered
1. **No constraint**: Fit may not pass through (0,0)
2. **Weighted constraint**: More complex, marginal benefit
3. **Force intercept=0**: Too restrictive (may lose trend)

## References
- Plan: `.sisyphus/plans/improve-wd-fitting-comprehensive.md`
