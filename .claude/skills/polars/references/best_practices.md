# Polars Best Practices

Performance optimization, common pitfalls, and expression patterns. Load this when debugging performance issues or learning advanced patterns.

## Performance Optimization

### 1. Use Lazy Evaluation for Large Datasets

```python
# ❌ Bad: Eager mode loads everything immediately
df = pl.read_csv("large_file.csv")
result = df.filter(pl.col("age") > 25).select("name", "age")

# ✅ Good: Lazy mode optimizes before execution
lf = pl.scan_csv("large_file.csv")
result = lf.filter(pl.col("age") > 25).select("name", "age").collect()
```

**Benefits:**
- Predicate pushdown (filter at source)
- Projection pushdown (read only needed columns)
- Query optimization
- Parallel execution planning

### 2. Filter and Select Early

```python
# ❌ Bad: Process all data, then filter
result = (
    lf.group_by("category")
    .agg(pl.col("value").mean())
    .filter(pl.col("value") > 100)
    .select("category", "value")
)

# ✅ Good: Filter and select early
result = (
    lf.select("category", "value")  # Only needed columns
    .filter(pl.col("value") > 100)  # Filter early
    .group_by("category")
    .agg(pl.col("value").mean())
)
```

### 3. Avoid Python Functions

Stay within the expression API to maintain parallelization:

```python
# ❌ Bad: Python function disables parallelization
df = df.with_columns(
    result=pl.col("value").map_elements(lambda x: x * 2, return_dtype=pl.Float64)
)

# ✅ Good: Use native expressions (parallelized)
df = df.with_columns(result=pl.col("value") * 2)
```

### 4. Use Streaming for Very Large Data

```python
# Streaming mode processes data in chunks
lf = pl.scan_parquet("very_large.parquet")
result = lf.filter(pl.col("value") > 100).collect(streaming=True)

# Or use sink for direct streaming writes
lf.filter(pl.col("value") > 100).sink_parquet("output.parquet")
```

### 5. Optimize Data Types

```python
# Specify optimal types on read
df = pl.read_csv(
    "data.csv",
    dtypes={
        "id": pl.UInt32,  # Instead of Int64 if values fit
        "category": pl.Categorical,  # For low-cardinality strings
        "date": pl.Date,  # Instead of String
    }
)
```

**Guidelines:**
- Use smallest integer type that fits your data
- Use `Categorical` for strings with low cardinality (<50% unique)
- Use `Date` instead of `Datetime` when time isn't needed

## Expression Patterns

### Building Expressions from Lists

```python
# ❌ Wrong: Building expression with += in loop
weighted_sum = pl.lit(0.0)
for ref in references:
    weighted_sum = weighted_sum + pl.col(ref.source_column) * ref.weight

# ✅ Right: Use sum() with list comprehension
expr = sum(
    [pl.col(ref.source_column) * ref.weight for ref in references],
    pl.lit(0.0)  # Default for empty list
)
```

### Composable Expressions

```python
# Build reusable components
speed_col = pl.col("wind_speed")
dir_col = pl.col("wind_direction")
rad_expr = dir_col * 3.14159 / 180

# Use in multiple expressions
u_expr = speed_col * rad_expr.cos()
v_expr = speed_col * rad_expr.sin()

# Apply all at once
df = df.with_columns([
    u_expr.alias("u_component"),
    v_expr.alias("v_component"),
])
```

### Conditional Logic

```python
# Simple conditions
df.with_columns(
    status=pl.when(pl.col("age") >= 18)
        .then("adult")
        .otherwise("minor")
)

# Multiple conditions
df.with_columns(
    grade=pl.when(pl.col("score") >= 90).then("A")
      .when(pl.col("score") >= 80).then("B")
      .when(pl.col("score") >= 70).then("C")
      .otherwise("F")
)

# Complex conditions
df.with_columns(
    category=pl.when(
        (pl.col("revenue") > 1000000) & (pl.col("customers") > 100)
    ).then("enterprise")
    .when(
        (pl.col("revenue") > 100000) | (pl.col("customers") > 50)
    ).then("business")
    .otherwise("starter")
)
```

### Null Handling

```python
# Check for nulls
df.filter(pl.col("value").is_null())
df.filter(pl.col("value").is_not_null())

# Fill nulls
df.with_columns(
    pl.col("value").fill_null(0),  # Constant
    pl.col("value").fill_null(strategy="forward"),  # Forward fill
    pl.col("value").fill_null(strategy="backward"),  # Backward fill
    pl.col("value").fill_null(strategy="mean"),  # Mean fill
)

# Coalesce (first non-null)
df.with_columns(
    combined=pl.coalesce(["col1", "col2", "col3"])
)
```

## Common Pitfalls

### Pitfall 1: Row Iteration

```python
# ❌ NEVER do this
for row in df.iter_rows():
    result = row[0] * 2

# ✅ Use vectorized operations
df = df.with_columns(result=pl.col("value") * 2)
```

### Pitfall 2: Modifying in Place

```python
# ❌ Polars is immutable, this doesn't work as expected
df["new_col"] = df["old_col"] * 2

# ✅ Functional style
df = df.with_columns(new_col=pl.col("old_col") * 2)
```

### Pitfall 3: Not Using Expressions

```python
# ❌ String-based operations won't work
df.select("value * 2")

# ✅ Expression-based
df.select(pl.col("value") * 2)
```

### Pitfall 4: Inefficient Joins

```python
# ❌ Join large tables without filtering
result = large_df1.join(large_df2, on="id")

# ✅ Filter before joining
result = (
    large_df1.filter(pl.col("active"))
    .join(
        large_df2.filter(pl.col("status") == "valid"),
        on="id"
    )
)
```

### Pitfall 5: Creating Many Small DataFrames

```python
# ❌ Many intermediate DataFrames
df1 = df.filter(pl.col("age") > 25)
df2 = df1.select("name", "age")
df3 = df2.sort("age")
result = df3.head(10)

# ✅ Chain operations
result = (
    df.filter(pl.col("age") > 25)
    .select("name", "age")
    .sort("age")
    .head(10)
)

# ✅ Better: Use lazy mode
result = (
    df.lazy()
    .filter(pl.col("age") > 25)
    .select("name", "age")
    .sort("age")
    .head(10)
    .collect()
)
```

## Memory Management

### Monitor Memory Usage

```python
# Check DataFrame size
print(f"Estimated size: {df.estimated_size('mb'):.2f} MB")

# Profile memory during operations
lf = pl.scan_csv("large.csv")
print(lf.explain())  # See query plan
```

### Reduce Memory Footprint

```python
# 1. Use lazy mode
lf = pl.scan_parquet("data.parquet")

# 2. Select only needed columns
lf = lf.select("col1", "col2")

# 3. Optimize data types
df = df.with_columns(
    pl.col("int_col").cast(pl.Int32),  # Downcast if possible
    pl.col("category").cast(pl.Categorical)
)

# 4. Drop unused columns
df = df.drop("large_text_col", "unused_col")
```

## Testing and Debugging

### Inspect Query Plans

```python
lf = pl.scan_csv("data.csv")
query = lf.filter(pl.col("age") > 25).select("name", "age")

# View optimized query plan
print(query.explain())

# View detailed plan
print(query.explain(optimized=True))
```

### Sample Data for Development

```python
# Use n_rows for testing
df = pl.read_csv("large.csv", n_rows=1000)

# Or sample after reading
df_sample = df.sample(n=1000, seed=42)
```

### Validate Schemas

```python
# Check schema
print(df.schema)

# Ensure schema matches expectation
expected_schema = {
    "id": pl.Int64,
    "name": pl.Utf8,
    "date": pl.Date
}
assert df.schema == expected_schema
```

## File Format Best Practices

### Choose the Right Format

| Format | Best For | Pros | Cons |
|--------|----------|------|------|
| **Parquet** | Large datasets, archival | Excellent compression, fast reads | Not human-readable |
| **CSV** | Small datasets, inspection | Universal, readable | Slow, large, no types |
| **Arrow IPC** | Inter-process comms | Fastest, zero-copy | Less compression |

### Reading Best Practices

```python
# 1. Use lazy reading
lf = pl.scan_parquet("data.parquet")

# 2. Read multiple files efficiently
lf = pl.scan_parquet("data/*.parquet")

# 3. Specify schema when known
lf = pl.scan_csv("data.csv", dtypes={"id": pl.Int64})

# 4. Use predicate pushdown
result = lf.filter(pl.col("date") >= "2023-01-01").collect()
```

### Writing Best Practices

```python
# Use Parquet for large data
df.write_parquet("output.parquet", compression="zstd")

# Partition large datasets
df.write_parquet("output", partition_by=["year", "month"])

# Streaming write for very large data
lf.sink_parquet("output.parquet")
```

## Code Organization

### Reusable Expressions

```python
# Define reusable expressions
age_group = (
    pl.when(pl.col("age") < 18).then("minor")
    .when(pl.col("age") < 65).then("adult")
    .otherwise("senior")
)

revenue_per_customer = pl.col("revenue") / pl.col("customer_count")

# Use in multiple contexts
df = df.with_columns(
    age_group=age_group,
    rpc=revenue_per_customer
)
```

### Pipeline Functions

```python
def clean_data(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Clean and standardize data."""
    return lf.with_columns(
        pl.col("name").str.to_uppercase(),
        pl.col("date").str.strptime(pl.Date, "%Y-%m-%d"),
        pl.col("amount").fill_null(0)
    )

def add_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Add computed features."""
    return lf.with_columns(
        month=pl.col("date").dt.month(),
        year=pl.col("date").dt.year(),
    )

# Compose pipeline
result = (
    pl.scan_csv("data.csv")
    .pipe(clean_data)
    .pipe(add_features)
    .filter(pl.col("year") == 2023)
    .collect()
)
```
