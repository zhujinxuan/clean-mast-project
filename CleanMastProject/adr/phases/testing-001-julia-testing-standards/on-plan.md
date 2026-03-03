# Phase: on-plan - Test Strategy Design

## When to Use

Load this file when:
- Designing test strategy for a new feature or module
- Planning test directory structure for a new module
- Deciding between inline test data and fixtures
- Creating test fixture designs

## Related ADR

- [ADR-testing-001: Julia Testing Standards](../testing-001-julia-testing-standards.md)
- [ADR-types-001: Julia Type System](../types-001-julia-type-system.md) - For type-safe test design

## Test Strategy Guidance

### Inline Data vs Fixtures Planning

| Test Data Type | When to Use | Speed | Complexity |
|---------------|-------------|-------|------------|
| **Inline Data** | Simple unit tests, small arrays/scalars | <10ms | Low |
| **Fixture Files** | Complex DataFrames, time series data | 10-50ms | Medium |
| **Fixture Generators** | Parametrized test data, random data | 10-50ms | Medium |

**Decision Tree:**
```
Testing simple functions?
├── Yes → Inline data (arrays, numbers, strings)
│   └── Create: test/{Module}/test_{feature}.jl with inline @test
│
└── Testing data transformations?
    ├── Complex CSV/Parquet data → Fixture files
    │   └── Create: test/{Module}/fixtures/{scenario}/input.csv
    ├── Parametrized scenarios → Generator functions
    │   └── Create: test/{Module}/fixtures/fixtures.jl with generate_* functions
    └── Time series data → Fixture files with timestamps
        └── Create: test/{Module}/fixtures/{scenario}/input.csv
```

### Test Directory Structure Planning

Plan your test structure to mirror your source structure:

```
CleanMastProject/
├── src/
│   └── {Module}/
│       └── {feature}.jl
└── test/
    ├── runtests.jl                  # Main test runner with TEST_SETS
    └── {Module}/                    # Mirrors src/{Module}/ structure
        ├── test_{feature}.jl       # Unit tests
        └── fixtures/                # Test data (optional)
            ├── fixtures.jl          # Fixture loading utilities
            └── {scenario}/          # Individual test scenarios
                ├── input.csv
                ├── expected_output.csv
                ├── config.toml
                └── generator.jl
```

### Test Coverage Planning

Target coverage by module type:

| Module Type | Target Coverage | Test Data Strategy |
|-------------|-----------------|-------------------|
| Data cleaning functions | 100% | Mix of inline and fixtures |
| Type constructors | 100% | Inline data |
| Configuration loading | 100% | Inline + TOML fixtures |
| CLI commands | 100% | Integration-style tests |
| Data transformations | 90% | Heavy use of fixtures |
| Plotting/visualization | 50% | Manual verification acceptable |

### Fixture Planning

Plan fixtures at two levels:

1. **Module fixtures (`{Module}/fixtures/fixtures.jl`)**
   - `load_fixture(scenario::String)` - Load CSV/TOML/generator fixtures
   - `create_test_dataframe(nrows::Int)` - Generate simple test data
   - `create_test_timeseries(nrows::Int)` - Generate timestamp data

2. **Scenario directories (`{Module}/fixtures/{scenario}/`)**
   - `input.csv` - Input test data
   - `expected_output.csv` - Expected result data
   - `config.toml` - Test configuration
   - `generator.jl` - Dynamic data generation

## Checklist

Before implementation, verify:

- [ ] Test directory structure mirrors source structure
- [ ] Test set names are descriptive and hierarchical
- [ ] Inline vs fixture strategy defined for each component
- [ ] Coverage targets set (>80% business logic)
- [ ] Test file naming follows `test_{feature}.jl` pattern
- [ ] Fixture loading utilities planned if using fixtures
- [ ] Test runner entries planned (add to TEST_SETS dict)
