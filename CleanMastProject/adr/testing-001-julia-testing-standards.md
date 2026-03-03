---
id: testing-001-julia-testing-standards
name: julia-testing-standards
description: Julia testing standards using Test.jl with @testset grouping, module-based directory structure, fixtures for complex scenarios, and inline data for unit tests
status: enforced
tags: [testing, julia, test-jl, unit-tests, fixtures, coverage]
applies_when:
  - writing tests
  - test design
  - test review
  - coverage validation
  - CI/CD setup
---

# ADR-testing-001: Julia Testing Standards

## Status

Enforced

## Constraint (MUST)

1. **ALL functions MUST have unit tests** in `CleanMastProject/test/`
2. **Test files MUST be named `test_{feature}.jl`** (not `tests_` or `{feature}_test.jl`)
3. **Tests MUST use `@testset` blocks** for logical grouping
4. **Tests MUST be organized by module** in corresponding subdirectories
5. **Complex test scenarios MUST use fixtures** in `{Module}/fixtures/`
6. **Simple unit tests SHOULD use inline data** (no external files)
7. **Test runner MUST be at `CleanMastProject/test/runtests.jl`**

## Rationale (WHY)

- **Module-based structure**: Mirrors source code organization, making tests easy to find
- **`@testset` nesting**: Clear test hierarchy, descriptive failure messages
- **Fixtures for complex data**: Reusable test data generators, consistent test environments
- **Inline data for simple cases**: Fast feedback, no file I/O overhead
- **Single test runner**: Unified entry point, selective test execution

## Pattern (HOW)

### Test Directory Structure

```
test/
├── runtests.jl              # Main test runner with TEST_SETS dict
├── {Module}/                # Mirrors src/{Module}/ structure
│   ├── test_{feature}.jl   # Unit tests for specific features
│   └── fixtures/            # Test data (optional)
│       ├── fixtures.jl      # Fixture loading utilities
│       └── {scenario}/      # Individual test scenarios
│           ├── input.csv
│           ├── expected_output.csv
│           └── generator.jl
```

### Running Tests

```bash
# Run all tests
julia CleanMastProject/test/runtests.jl

# Run specific test sets
julia CleanMastProject/test/runtests.jl parse_sensors data-clean

# List available test sets
julia CleanMastProject/test/runtests.jl --help
```

### Test File Pattern

```julia
# test/{Module}/test_{feature}.jl

using Test
using CleanMastProject.{Module}.{Feature}
using CleanMastProject.Types.{Config}

@testset "{Feature} Tests" begin
    
    @testset "Specific functionality" begin
        # Arrange
        input = [1, 2, 3]
        
        # Act
        result = process_data(input)
        
        # Assert
        @test length(result) == 3
        @test result[1] == expected_value
    end
    
    @testset "Edge cases" begin
        @test_throws DomainError process_data([])
    end
    
end
```

### Test Runner Structure

```julia
# test/runtests.jl

using Test
using Pkg

# Activate project environment
test_dir = @__DIR__
project_dir = joinpath(test_dir, "..")
Pkg.activate(project_dir)

# Define test sets
const TEST_SETS = Dict{String, Vector{String}}(
    "module_name" => [
        "ModuleName/test_feature.jl",
        "ModuleName/test_another_feature.jl"
    ]
)

# Parse arguments and run tests
# ... see runtests.jl for full implementation
```

### Fixtures for Complex Data

```julia
# test/{Module}/fixtures/fixtures.jl

using DataFrames, CSV, TOML

function load_fixture(path::String)
    fixture_dir = joinpath(@__DIR__, path)
    
    input_df = if isfile(joinpath(fixture_dir, "input.csv"))
        CSV.read(joinpath(fixture_dir, "input.csv"), DataFrame)
    elseif isfile(joinpath(fixture_dir, "generator.jl"))
        include(joinpath(fixture_dir, "generator.jl"))
        generate_input_data()
    else
        nothing
    end
    
    # Load expected_output, config, etc.
    # Return NamedTuple with all fixture components
end

# For simple inline test data
function create_test_dataframe(nrows::Int)
    timestamps = [DateTime(2024, 1, 1) + Minute(10 * (i-1)) for i in 1:nrows]
    df = DataFrame(timestamp = timestamps)
    df[!, :value] = rand(nrows) .* 10
    return df
end
```

### Using Fixtures in Tests

```julia
# test/{Module}/test_feature.jl

using Test
using CleanMastProject.{Module}

# Include fixtures if needed
include(joinpath(@__DIR__, "fixtures", "fixtures.jl"))

@testset "Feature with Complex Data" begin
    # Use fixture for complex scenario
    fixture = load_fixture("sensor_merge/zero_overlap")
    result = process_data(fixture.input, fixture.config)
    @test result == fixture.expected_output
end

@testset "Feature with Simple Data" begin
    # Use inline data for simple unit test
    data = create_test_dataframe(10)
    result = quick_process(data)
    @test length(result) == 10
end
```

## Phase Links

This ADR uses phase-based implementation guidance:

| Phase | File | Purpose |
|-------|------|---------|
| **on-plan** | [phases/testing-001-julia-testing-standards/on-plan.md](phases/testing-001-julia-testing-standards/on-plan.md) | Test strategy design |
| **review-plan** | [phases/testing-001-julia-testing-standards/review-plan.md](phases/testing-001-julia-testing-standards/review-plan.md) | Review test plans |
| **code** | [phases/testing-001-julia-testing-standards/code.md](phases/testing-001-julia-testing-standards/code.md) | Julia test patterns |
| **review-implementation** | [phases/testing-001-julia-testing-standards/review-implementation.md](phases/testing-001-julia-testing-standards/review-implementation.md) | Testing compliance |

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Test file in wrong location
# test/test_all.jl  # Don't put all tests in one file

# ❌ WRONG: Test file naming
# tests_column_parser.jl   # Use test_ prefix, not tests_
# column_parser_test.jl    # Use test_{feature}.jl, not {feature}_test.jl

# ❌ WRONG: No @testset blocks
using Test
@test process_data([1, 2, 3]) == [2, 3, 4]  # Missing @testset!

# ❌ WRONG: Tests outside test/ directory
# src/MyModule.jl
function my_function()
end
@test my_function() == 42  # NEVER! Move to test/

# ❌ WRONG: Tests at wrong level (e.g., in src/)
# src/ParseSensors/test_parser.jl  # Tests must be in test/

# ❌ WRONG: Test in test root instead of module subdir
# test/test_column_parser.jl  # Should be test/ParseSensors/test_column_parser.jl

# ❌ WRONG: Missing test for error case
@testset "process_data success" begin  # ❌ Where's the failure test?
    @test process_data([1, 2, 3]) == expected
end

# ❌ WRONG: Using external files for simple unit tests
@testset "basic arithmetic" begin
    data = CSV.read("test/data/simple.csv", DataFrame)  # ❌ Use inline data
    @test sum(data.value) == 100
end

# ❌ WRONG: Tests without assertions
@testset "data processing" begin  # ❌ No @test!
    result = process_data(input)
end

# ❌ WRONG: Testing multiple things in one @testset
@testset "process_data" begin  # ❌ Split into focused @testsets
    # Test with integers
    @test process_data([1, 2, 3]) == [2, 4, 6]
    # Test with floats
    @test process_data([1.5, 2.5]) == [3.0, 5.0]
    # Test edge case
    @test process_data([]) == []
end
```

## Test Naming Conventions

| What | Convention | Example |
|------|------------|---------|
| Test file | `test_{feature}.jl` | `test_column_parser.jl` |
| Test set | Descriptive string | `@testset "Column parsing with regex"` |
| Nested test set | Specific scenario | `@testset "Placeholder extraction"` |
| Fixture directory | `{scenario_name}` | `fixtures/sensor_merge/` |
| Fixture loader | `load_fixture()` | Standard fixture loading function |

## Validation

```bash
#!/bin/bash

echo "=== ADR-testing-001 Julia Testing Standards Validation ==="

# Check test directory exists
if [ ! -d "CleanMastProject/test" ]; then
    echo "FAIL: Missing test/ directory"
    exit 1
fi

# Check runtests.jl exists
if [ ! -f "CleanMastProject/test/runtests.jl" ]; then
    echo "FAIL: Missing runtests.jl"
    exit 1
fi

# Check for tests outside test/ directory
if find CleanMastProject/src -name "test_*.jl" -o -name "*_test.jl" | grep -q .; then
    echo "FAIL: Found test files in src/ directory"
    exit 1
fi

# Check test file naming
bad_names=$(find CleanMastProject/test -name "*_test.jl" -o -name "tests_*.jl" 2>/dev/null)
if [ -n "$bad_names" ]; then
    echo "FAIL: Test files with incorrect naming:"
    echo "$bad_names"
    exit 1
fi

# Run all tests
echo "Running all tests..."
if ! julia CleanMastProject/test/runtests.jl; then
    echo "FAIL: Tests failed"
    exit 1
fi

echo "✓ Testing standards validation passed"
```

## References

- [CleanMastProject/test/runtests.jl](../../CleanMastProject/test/runtests.jl) - Test runner implementation
- [CleanMastProject/AGENTS.md](../../CleanMastProject/AGENTS.md) - Coding standards and conventions
- Julia Test.jl documentation: https://docs.julialang.org/en/v1/stdlib/Test/
