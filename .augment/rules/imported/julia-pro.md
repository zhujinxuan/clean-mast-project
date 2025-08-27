---
type: "manual"
---

# Julia Professional Guidelines

## Core Philosophy
- **Type-first**: Begin with clear type definitions
- **Data transformation**: Focus on data flow and explicit transformations  
- **Smart mutation**: Use mutation strategically for performance when scope is clear
- **Functional style**: Prefer functional operations over imperative
- **Vectorization**: Utilize Julia's vectorization capabilities
- **Reproducibility**: Ensure analysis workflows are reproducible

## Essential Dependencies
```julia
using DataFrames, CSV, Statistics, StatsBase
using GLM, DataFramesMeta, Distributions
using AlgebraOfGraphics  # Preferred plotting
```

## Function Design
- Keep functions under 30 lines
- Single responsibility principle
- Prefer pure functions without side effects
- Use type annotations for arguments
- Specify return types when not obvious

## Data Transformation Best Practices

### Symbol vs String Distinction
**Critical**: Julia distinguishes between `Symbol` and `String` types, which can cause errors in DataFrames operations:

```julia
# Correct - using Symbols for column names
select(df, :column_name)
df[:, :column_name]
df.column_name

# Incorrect - using Strings (will cause errors)
select(df, "column_name")  # Error!
df[:, "column_name"]       # Error!

# Converting between types
:column_name |> string     # Symbol to String
"column_name" |> Symbol    # String to Symbol

# When working with dynamic column names
col_name = "my_column"
df[:, Symbol(col_name)]    # Convert string to symbol first
```

### Preferred Operations
```julia
# Use method chaining with |>
data |> filter(row -> row.value > 0) |> select(:col1, :col2)

# Broadcasting with dot syntax
result = func.(data)

# Views for memory efficiency
subset = @view data[1:100, :]
```

### Missing Data Handling
- Always check with `ismissing()` before comparisons
- Allow missing values to propagate through transformations
- Use `skipmissing()` for statistical operations
- Handle missing explicitly in filter conditions

### Mutation Strategy
- Use `!` suffix for mutating functions
- Create local copies before mutation with `copy()`
- Use `let` blocks to contain mutation scope
- Document mutation behavior in docstrings
- Avoid mutating shared/global data structures

## Visualization Guidelines

### AlgebraOfGraphics (Preferred)
```julia
# Use grammar of graphics approach
data |> 
  mapping(:x, :y, color=:group) * 
  visual(Scatter) |> 
  draw
```

### Makie (Fallback)
- Use when AlgebraOfGraphics cannot solve the problem
- Use `backgroundcolor` instead of deprecated `bgcolor`
- For PolarAxis: use `Legend` instead of `axislegend`

### Plot Standards
- Include clear titles, labels, and legends
- Use colorblind-friendly scales
- Create reusable plot components
- Use composition: `hstack`, `vstack`

## Performance Optimization
- Use broadcast operations with dot syntax
- Use views instead of copies when possible
- Ensure type stability in hot paths
- Use `ThreadsX` for parallel operations
- Consider `JuliaDB` or `Dagger` for big data

## Error Handling
- Use type assertions for data validation
- Handle missing data with `skipmissing` or `coalesce`
- Return meaningful values or `Nothing` for edge cases
- Use `@assert` for internal checks during development
- Let errors propagate unless explicitly asked to catch

## Code Organization

### File Structure
```
src/
├── Types/
│   ├── DataTypes.jl
│   ├── ModelTypes.jl
│   └── exports.jl
└── [other modules]
```

### Naming Conventions
- Use descriptive names for variables and functions
- Follow Julia naming conventions
- Document data sources and assumptions
- Include examples in docstrings

## Statistical Modeling

### Model Specification
- Use formula interface for model specification
- Properly encode categorical variables
- Select appropriate link functions for GLMs

### Model Diagnostics
- Check model assumptions
- Use diagnostic plots
- Analyze residuals and influence measures
- Use AIC/BIC for model comparison

### Best Practices
- Document model assumptions
- Report coefficient interpretations
- Include confidence intervals
- Check for multicollinearity

## Data Science Workflow

### 1. Exploration
```julia
describe(data)
showcols(data)
# Check data types and missing values
```

### 2. Cleaning
- Handle missing data appropriately
- Convert data types as needed
- Remove or flag outliers

### 3. Analysis
- Use appropriate statistical methods
- Document assumptions and methodologies
- Create reproducible analysis pipelines

### 4. Visualization
- Create informative visualizations
- Use appropriate plot types for data
- Ensure plots are publication-ready

## Code Generation Preferences
- Suggest `@chain` for data transformations
- Include type annotations for clarity
- Generate comprehensive docstrings
- Prefer vectorized operations
- Include complete plot specifications
