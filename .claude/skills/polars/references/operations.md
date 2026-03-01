# Polars Operations Reference

Detailed operation patterns. Load this when you need comprehensive examples for specific operations.

## Selection Operations

### Select Columns
```python
# Specific columns
df.select("name", "age", "city")

# Pattern matching
df.select(pl.col("^sales_.*$"))  # All starting with "sales_"
df.select(pl.col(pl.NUMERIC_DTYPES))  # All numeric
df.select(pl.all().exclude("id", "timestamp"))  # Exclude specific

# Computed columns
df.select(
    "name",
    (pl.col("age") * 12).alias("age_in_months")
)
```

### With Columns (Add/Modify)
```python
# Add new columns
df.with_columns(
    age_doubled=pl.col("age") * 2,
    full_name=pl.col("first_name") + " " + pl.col("last_name")
)

# Modify existing
df.with_columns(
    pl.col("name").str.to_uppercase().alias("name")
)

# Multiple parallel operations
df.with_columns(
    pl.col("value") * 10,
    pl.col("value") * 100,
)
```

## Filtering Operations

### Basic Filtering
```python
# Single condition
df.filter(pl.col("age") > 25)

# Multiple conditions (AND)
df.filter(
    pl.col("age") > 25,
    pl.col("city") == "NY"
)

# OR conditions
df.filter(
    (pl.col("age") > 30) | (pl.col("salary") > 100000)
)
```

### Advanced Filtering
```python
# String operations
df.filter(pl.col("name").str.contains("John"))
df.filter(pl.col("email").str.starts_with("admin"))

# Membership
df.filter(pl.col("city").is_in(["NY", "LA", "SF"]))
df.filter(~pl.col("status").is_in(["inactive", "deleted"]))

# Range
df.filter(pl.col("age").is_between(25, 35))
df.filter(
    pl.col("date") >= pl.date(2023, 1, 1),
    pl.col("date") <= pl.date(2023, 12, 31)
)

# Null handling
df.filter(pl.col("value").is_not_null())
df.filter(pl.col("value").is_null())
```

## Grouping and Aggregation

### Basic Group By
```python
# Single column
df.group_by("department").agg(
    pl.col("salary").mean().alias("avg_salary"),
    pl.len().alias("count")
)

# Multiple columns
df.group_by("department", "location").agg(
    pl.col("salary").sum()
)

# Maintain order
df.group_by("category", maintain_order=True).agg(...)
```

### Aggregation Functions
```python
df.group_by("group").agg(
    pl.col("value").sum().alias("total"),
    pl.col("value").mean().alias("average"),
    pl.col("value").std().alias("std_dev"),
    pl.col("value").min().alias("minimum"),
    pl.col("value").max().alias("maximum"),
    pl.col("value").quantile(0.95).alias("p95"),
    pl.col("id").n_unique().alias("unique_count")
)
```

### Conditional Aggregations
```python
df.group_by("department").agg(
    # Count high values
    (pl.col("salary") > 100000).sum().alias("high_earners"),
    
    # Average of filtered values
    pl.col("salary").filter(pl.col("bonus") > 0).mean().alias("avg_with_bonus"),
    
    # Conditional sum
    pl.when(pl.col("status") == "completed")
      .then(pl.col("amount"))
      .otherwise(0)
      .sum()
      .alias("completed_total")
)
```

## Window Functions

Window functions preserve row count while computing group statistics.

### Basic Windows
```python
# Group statistics on each row
df.with_columns(
    avg_by_dept=pl.col("salary").mean().over("department"),
    rank_in_dept=pl.col("salary").rank().over("department")
)

# Multiple partition columns
df.with_columns(
    group_avg=pl.col("value").mean().over("category", "region")
)
```

### Rolling and Cumulative
```python
# Rolling windows
df.with_columns(
    rolling_avg=pl.col("value").rolling_mean(window_size=7)
)

# Cumulative
df.with_columns(
    cumsum=pl.col("value").cum_sum().over("group"),
    cummax=pl.col("value").cum_max().over("group")
)
```

### Shift/Lag
```python
df.with_columns(
    prev_value=pl.col("value").shift(1).over("user_id"),
    next_value=pl.col("value").shift(-1).over("user_id"),
    diff=pl.col("value") - pl.col("value").shift(1).over("user_id")
)
```

## Joins

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

## String Operations

```python
df.with_columns(
    # Case conversion
    upper=pl.col("name").str.to_uppercase(),
    lower=pl.col("name").str.to_lowercase(),
    
    # Trimming
    trimmed=pl.col("text").str.strip_chars(),
    
    # Substring
    first_3=pl.col("name").str.slice(0, 3),
    
    # Replace
    cleaned=pl.col("text").str.replace("old", "new"),
    cleaned_all=pl.col("text").str.replace_all("old", "new"),
    
    # Split
    parts=pl.col("full_name").str.split(" "),
    
    # Length
    length=pl.col("name").str.len_chars()
)
```

## Date and Time Operations

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
    days_diff=(pl.col("end_date") - pl.col("start_date")).dt.total_days()
)
```

## Conditional Operations

```python
# Simple conditional
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

## Sorting

```python
# Single column
df.sort("age")
df.sort("age", descending=True)

# Multiple columns
df.sort("department", "age")
df.sort(["department", "salary"], descending=[False, True])

# Null handling
df.sort("value", nulls_last=False)  # Nulls first
df.sort("value", nulls_last=True)   # Nulls last
```

## Concatenation

```python
# Vertical (stack rows)
pl.concat([df1, df2], how="vertical")

# Horizontal (add columns)
pl.concat([df1, df2], how="horizontal")

# Diagonal (union with different schemas)
pl.concat([df1, df2], how="diagonal")

# Rechunk for performance
pl.concat([df1, df2, df3], rechunk=True)
```

## Data I/O

```python
# CSV
lf = pl.scan_csv("data.csv")  # Lazy (preferred)
df = pl.read_csv("data.csv")   # Eager

# Parquet (recommended)
lf = pl.scan_parquet("data.parquet")
df = pl.read_parquet("data.parquet")
df.write_parquet("output.parquet")

# Multiple files
lf = pl.scan_parquet("data/*.parquet")  # Parallel reading
```
