# Polars Best Practices & Operations Reference

Performance optimization, common pitfalls, and detailed operation patterns.

## Performance Optimization

### 1. Use Lazy Evaluation

```python
# BAD: Eager mode loads everything immediately
df = pl.read_csv("large_file.csv")
result = df.filter(pl.col("age") > 25).select("name", "age")

# GOOD: Lazy mode optimizes before execution
lf = pl.scan_csv("large_file.csv")
result = lf.filter(pl.col("age") > 25).select("name", "age").collect()
```

**Benefits:**
- Predicate pushdown (filter at source)
- Projection pushdown (read only needed columns)
- Query optimization and parallel execution planning

### 2. Filter and Select Early

```python
# BAD: Process all data, then filter
result = (
    lf.group_by("category")
    .agg(pl.col("value").mean())
    .filter(pl.col("value") > 100)
)

# GOOD: Filter and select early
result = (
    lf.select("category", "value")
    .filter(pl.col("value") > 100)
    .group_by("category")
    .agg(pl.col("value").mean())
)
```

### 3. Avoid Python Functions

Stay within the expression API to maintain parallelization:

```python
# BAD: Python function disables parallelization (deprecated: apply →
#       map_elements; still slow)
df = df.with_columns(
    result=pl.col("value").map_elements(lambda x: x * 2, return_dtype=pl.Float64)
)

# GOOD: Use native expressions (parallelized)
df = df.with_columns(result=pl.col("value") * 2)
```

### 4. Streaming for Large Data

```python
# Use engine="streaming" (not the deprecated streaming=True)
lf = pl.scan_parquet("very_large.parquet")
result = lf.filter(pl.col("value") > 100).collect(engine="streaming")

# Or sink for direct streaming writes
lf.filter(pl.col("value") > 100).sink_parquet("output.parquet")
```

### 5. Optimize Data Types

```python
# Specify schema_overrides on read (dtypes= is deprecated)
df = pl.read_csv(
    "data.csv",
    schema_overrides={
        "id": pl.UInt32,       # Instead of Int64 if values fit
        "category": pl.Enum([   # Use Enum for fixed/few categories
            "small", "medium", "large"
        ]),
        "date": pl.Date,       # Instead of String
    },
)

# Downcast after loading
df = df.with_columns(
    pl.col("int_col").cast(pl.Int32),
    pl.col("category_col").cast(pl.Categorical)  # Only for open-ended categories
)
```

**Guidelines:**
- Use smallest integer type that fits your data
- Prefer `pl.Enum` when the category set is known and fixed; use `pl.Categorical` only when new values may appear
- Use `pl.Date` instead of `pl.Datetime` when time-of-day isn't needed

## Expression Patterns

### Building Expressions from Lists

```python
# WRONG: Building expression with += in loop
weighted_sum = pl.lit(0.0)
for ref in references:
    weighted_sum = weighted_sum + pl.col(ref.source_column) * ref.weight

# RIGHT: Use sum() with list comprehension and a start value
expr = sum(
    [pl.col(ref.source_column) * ref.weight for ref in references],
    pl.lit(0.0)  # Default for empty list
)
```

### Composable Expressions

```python
# Build reusable components
speed_col = pl.col("wind_speed")
dir_rad = pl.col("wind_direction").radians()  # degrees → radians

# Use in multiple expressions
u_expr = speed_col * dir_rad.sin()
v_expr = speed_col * dir_rad.cos()

# Apply all at once
df = df.with_columns(
    u_expr.alias("u_component"),
    v_expr.alias("v_component"),
)
```

### Conditional Logic

```python
# Simple conditions
df.with_columns(
    status=pl.when(pl.col("age") >= 18)
        .then(pl.lit("adult"))
        .otherwise(pl.lit("minor"))
)

# Multiple conditions — use pl.lit for string constants
df.with_columns(
    grade=pl.when(pl.col("score") >= 90).then(pl.lit("A"))
      .when(pl.col("score") >= 80).then(pl.lit("B"))
      .when(pl.col("score") >= 70).then(pl.lit("C"))
      .otherwise(pl.lit("F"))
)

# Complex conditions
df.with_columns(
    category=pl.when(
        (pl.col("revenue") > 1_000_000) & (pl.col("customers") > 100)
    ).then(pl.lit("enterprise"))
    .when(
        (pl.col("revenue") > 100_000) | (pl.col("customers") > 50)
    ).then(pl.lit("business"))
    .otherwise(pl.lit("starter"))
)
```

### Null Handling

```python
# Check for nulls
df.filter(pl.col("value").is_null())
df.filter(pl.col("value").is_not_null())

# Fill nulls
df.with_columns(
    pl.col("value").fill_null(0),
    pl.col("value").fill_null(strategy="forward"),
    pl.col("value").fill_null(strategy="backward"),
    pl.col("value").fill_null(strategy="mean"),
)

# Coalesce (first non-null)
df.with_columns(
    combined=pl.coalesce(["col1", "col2", "col3"])
)
```

## Operations Reference

### Selection

```python
# Specific columns
df.select("name", "age", "city")

# Pattern matching with selectors (not pl.NUMERIC_DTYPES — deprecated)
import polars.selectors as cs
df.select(cs.numeric())          # All numeric columns
df.select(cs.string())           # All string columns
df.select(pl.all().exclude("id", "timestamp"))  # Exclude specific

# Computed columns
df.select(
    "name",
    (pl.col("age") * 12).alias("age_in_months"),
)
```

### With Columns (Add/Modify)

```python
# Add new columns
df.with_columns(
    age_doubled=pl.col("age") * 2,
    full_name=pl.col("first_name") + " " + pl.col("last_name"),
)

# Modify existing (names must match)
df.with_columns(
    pl.col("name").str.to_uppercase().alias("name"),
)

# Multiple parallel operations
df.with_columns(
    pl.col("value") * 10,
    pl.col("value") * 100,
)
```

### Filtering

```python
# Single condition
df.filter(pl.col("age") > 25)

# Multiple conditions (AND)
df.filter(pl.col("age") > 25, pl.col("city") == "NY")

# OR conditions
df.filter((pl.col("age") > 30) | (pl.col("salary") > 100_000))

# String operations
df.filter(pl.col("name").str.contains("John"))
df.filter(pl.col("email").str.starts_with("admin"))

# Membership
df.filter(pl.col("city").is_in(["NY", "LA", "SF"]))
df.filter(~pl.col("status").is_in(["inactive", "deleted"]))

# Range
df.filter(pl.col("age").is_between(25, 35))
```

### Grouping and Aggregation

```python
# Single column
df.group_by("department").agg(
    pl.col("salary").mean().alias("avg_salary"),
    pl.len().alias("count"),
)

# Multiple columns
df.group_by("department", "location").agg(pl.col("salary").sum())

# Common aggregations
df.group_by("group").agg(
    pl.col("value").sum().alias("total"),
    pl.col("value").mean().alias("average"),
    pl.col("value").std().alias("std_dev"),
    pl.col("value").min().alias("minimum"),
    pl.col("value").max().alias("maximum"),
    pl.col("value").quantile(0.95).alias("p95"),
    pl.col("id").n_unique().alias("unique_count"),
)

# Conditional aggregations
df.group_by("department").agg(
    (pl.col("salary") > 100_000).sum().alias("high_earners"),
    pl.col("salary").filter(pl.col("bonus") > 0).mean().alias("avg_with_bonus"),
)
```

### Window Functions

```python
# Group statistics on each row
df.with_columns(
    avg_by_dept=pl.col("salary").mean().over("department"),
    rank_in_dept=pl.col("salary").rank().over("department"),
)

# Rolling windows
df.with_columns(
    rolling_avg=pl.col("value").rolling_mean(window_size=7),
)

# Cumulative
df.with_columns(
    cumsum=pl.col("value").cum_sum().over("group"),
    cummax=pl.col("value").cum_max().over("group"),
)

# Shift/Lag — for time-series differences
df.with_columns(
    prev_value=pl.col("value").shift(1).over("user_id"),
    next_value=pl.col("value").shift(-1).over("user_id"),
    diff=pl.col("value") - pl.col("value").shift(1).over("user_id"),
)
```

### Joins

```python
# Inner join
df1.join(df2, on="id", how="inner")

# Left join
df1.join(df2, on="id", how="left")

# Different column names
df1.join(df2, left_on="user_id", right_on="id")

# Multiple columns
df1.join(df2, on=["id", "date"], how="left")
```

### Date and Time

```python
df.with_columns(
    # Parse strings to dates
    date=pl.col("date_str").str.strptime(pl.Date, "%Y-%m-%d"),

    # Extract components
    year=pl.col("date").dt.year(),
    month=pl.col("date").dt.month(),
    day=pl.col("date").dt.day(),
    weekday=pl.col("date").dt.weekday(),
    hour=pl.col("datetime").dt.hour(),

    # Date arithmetic
    next_week=pl.col("date") + pl.duration(weeks=1),
    days_diff=(pl.col("end_date") - pl.col("start_date")).dt.total_days(),
)
```

### Concatenation

```python
# Vertical (stack rows) — preferred over manual accumulation
pl.concat([df1, df2], how="vertical")

# Horizontal (add columns)
pl.concat([df1, df2], how="horizontal")

# Rechunk for performance
pl.concat([df1, df2, df3], rechunk=True)
```

## Common Pitfalls

### Pitfall 1: Row Iteration

```python
# NEVER do this
for row in df.iter_rows():
    result = row[0] * 2

# Use vectorized operations
df = df.with_columns(result=pl.col("value") * 2)
```

### Pitfall 2: Scalar Extraction

```python
# WRONG: Chained indexer — fragile and hard to read
value = df["col"][0]

# RIGHT: Use .item() for single scalars
value = df["col"].item(0)
# Or select + item:
value = df.select(pl.col("col")).item()

# Only use .to_series() when you truly need a Series object
```

### Pitfall 3: Modifying in Place

```python
# WRONG: Polars is immutable — this creates a warning, not a mutation
df["new_col"] = df["old_col"] * 2

# RIGHT: Functional style
df = df.with_columns(new_col=pl.col("old_col") * 2)
```

### Pitfall 4: Inefficient Joins

```python
# BAD: Join large tables without filtering
result = large_df1.join(large_df2, on="id")

# GOOD: Filter before joining
result = (
    large_df1.filter(pl.col("active"))
    .join(large_df2.filter(pl.col("status") == "valid"), on="id")
)
```

### Pitfall 5: Many Small DataFrames

```python
# BAD: Many intermediate DataFrames
df1 = df.filter(pl.col("age") > 25)
df2 = df1.select("name", "age")
df3 = df2.sort("age")
result = df3.head(10)

# GOOD: Chain operations (internally optimized)
result = (
    df.filter(pl.col("age") > 25)
    .select("name", "age")
    .sort("age")
    .head(10)
)

# BETTER: Use lazy mode
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

```python
# Check DataFrame size
print(f"Estimated size: {df.estimated_size('mb'):.2f} MB")

# Profile query plan
lf = pl.scan_parquet("data.parquet")
print(lf.explain())  # Shows optimized plan by default

# Reduce footprint
lf = pl.scan_parquet("data.parquet")   # 1. Use lazy
lf = lf.select("col1", "col2")         # 2. Select needed columns only
df = df.drop("large_text_col")         # 3. Drop unused columns
```

## File Format Best Practices

| Format | Best For | Pros | Cons |
|--------|----------|------|------|
| **Parquet** | Large datasets, archival | Excellent compression, fast reads | Not human-readable |
| **CSV** | Small datasets, inspection | Universal, readable | Slow, large, no types |
| **Arrow IPC** | Inter-process comms | Fastest, zero-copy | Less compression |

```python
# Lazy reading (preferred)
lf = pl.scan_parquet("data.parquet")

# Multiple files in parallel
lf = pl.scan_parquet("data/*.parquet")

# Specify schema with schema_overrides
lf = pl.scan_csv("data.csv", schema_overrides={"id": pl.Int64})

# Predicate pushdown
result = lf.filter(pl.col("date") >= "2023-01-01").collect()

# Writing: use Parquet for large data
df.write_parquet("output.parquet", compression="zstd")

# Partition large datasets
df.write_parquet("output", partition_by=["year", "month"])

# Streaming sink
lf.sink_parquet("output.parquet")
```

## Code Organization

### Reusable Expressions

```python
# Define once, use everywhere
age_group = (
    pl.when(pl.col("age") < 18).then(pl.lit("minor"))
    .when(pl.col("age") < 65).then(pl.lit("adult"))
    .otherwise(pl.lit("senior"))
)

revenue_per_customer = pl.col("revenue") / pl.col("customer_count")

df = df.with_columns(
    age_group=age_group,
    rpc=revenue_per_customer,
)
```

### Pipeline Functions (LazyFrame in, LazyFrame out)

```python
def clean_data(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Clean and standardize data."""
    return lf.with_columns(
        pl.col("name").str.to_uppercase(),
        pl.col("date").str.strptime(pl.Date, "%Y-%m-%d"),
        pl.col("amount").fill_null(0),
    )

def add_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Add computed features."""
    return lf.with_columns(
        month=pl.col("date").dt.month(),
        year=pl.col("date").dt.year(),
    )

# Compose pipeline
result = (
    pl.scan_parquet("data.parquet")
    .pipe(clean_data)
    .pipe(add_features)
    .filter(pl.col("year") == 2023)
    .collect()
)
```

### Schema-Contract Functions

```python
import dataframely as dy

class OutputSchema(dy.Schema):
    height = dy.Float64(nullable=False)
    value = dy.Float64(nullable=False)

def process(lf: pl.LazyFrame) -> dy.DataFrame[OutputSchema]:
    result = lf.select(
        pl.col("height"),
        pl.col("raw_value").alias("value"),
    ).collect()
    return OutputSchema.validate(result, cast=False)  # Strict: reject mismatches
```
