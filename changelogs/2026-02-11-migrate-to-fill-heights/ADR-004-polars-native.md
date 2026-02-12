# ADR-004: Polars-Native Implementation

## Status
Accepted

## Context
The codebase was using a mix of numpy and polars, with Python loops for data processing. We wanted to modernize to pure Polars for better performance and cleaner code.

## Decision
Refactor to Polars-native patterns:
- Use `pl.col()` expressions for column operations
- Build DataFrames instead of Python lists
- Use `.filter()`, `.select()`, `.with_columns()` chains
- Keep numpy only for `polyfit` (Polars has no equivalent)

### Example: WD Fill Execution
```python
# Before: Loop + numpy
for ref in references:
    extrapolated = df[ref.source_column] * scale
    weighted_list.append(extrapolated * ref.weight)

# After: Pure expressions
expr = sum([
    pl.col(ref.source_column) * scale * weight
    for ref in references
], pl.lit(0.0))
return df.with_columns(expr.alias(target_column))[target_column]
```

## Consequences

### Positive
- Cleaner, more readable code
- Better performance (vectorized)
- Lazy evaluation benefits
- Type safety with expressions

### Negative
- Learning curve for Polars expressions
- Some numpy functions still needed (polyfit)
- Debugging expressions can be harder

## Alternatives Considered
1. **Keep numpy**: Less efficient, more verbose
2. **Use pandas**: Polars is faster and more modern
3. **Pure Python**: Too slow for large datasets

## References
- Plan: `.sisyphus/plans/refactor-wd-ultra-pure-polars.md`
- Documentation: `CLAUDE.md` Polars Best Practices section
