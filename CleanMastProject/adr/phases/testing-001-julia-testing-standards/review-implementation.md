# Phase: review-implementation - Testing Compliance

## When to Use

Load this file when:
- Reviewing test implementations
- Validating test coverage
- Checking fixture usage
- Verifying ADR compliance

## Related ADR

- [ADR-testing-001: Julia Testing Standards](../testing-001-julia-testing-standards.md)

## Compliance Checklist

### File Location Compliance

- [ ] All test files in `test/` directory (not `src/`)
- [ ] Test files in module subdirectories (`test/{Module}/`)
- [ ] Fixtures in `{Module}/fixtures/` subdirectory
- [ ] No test code in production files

### Naming Compliance

- [ ] Test files named `test_{feature}.jl` (not `tests_*.jl` or `*_test.jl`)
- [ ] Test sets have descriptive names
- [ ] Nested test sets use specific scenario names

### Test Pattern Compliance

- [ ] All tests wrapped in `@testset` blocks
- [ ] Tests use `@test` or `@test_throws` for assertions
- [ ] Tests include both success and failure cases
- [ ] No tests without assertions

### Fixture Compliance

- [ ] Complex scenarios use fixtures from `fixtures/` directory
- [ ] Simple unit tests use inline data (no file I/O)
- [ ] Fixture loading utilities are reusable
- [ ] Generator fixtures produce consistent output

### Test Runner Compliance

- [ ] New test files added to `TEST_SETS` dict in `runtests.jl`
- [ ] Test set names are consistent with module names
- [ ] Test runner can execute new tests

## Review Script

```bash
#!/bin/bash

echo "=== Testing ADR Compliance Review ==="

# Check for tests in src/
echo "Checking for tests in src/..."
if find CleanMastProject/src -name "test_*.jl" -o -name "*_test.jl" 2>/dev/null | grep -q .; then
    echo "  FAIL: Found test files in src/"
    find CleanMastProject/src -name "test_*.jl" -o -name "*_test.jl"
else
    echo "  PASS: No test files in src/"
fi

# Check test file naming
echo "Checking test file naming..."
bad_names=$(find CleanMastProject/test -name "*_test.jl" -o -name "tests_*.jl" 2>/dev/null)
if [ -n "$bad_names" ]; then
    echo "  FAIL: Incorrect test file naming:"
    echo "$bad_names"
else
    echo "  PASS: All test files follow naming convention"
fi

# Check for @testset usage (basic check)
echo "Checking @testset usage..."
for file in CleanMastProject/test/**/*.jl; do
    if [[ "$file" == *"runtests.jl"* ]] || [[ "$file" == *"fixtures.jl"* ]] || [[ "$file" == *"TestUtils.jl"* ]]; then
        continue
    fi
    if ! grep -q "@testset" "$file" 2>/dev/null; then
        echo "  WARNING: $file may be missing @testset"
    fi
done
echo "  Check complete"

# Check TEST_SETS entries
echo "Checking test runner entries..."
for dir in CleanMastProject/test/*/; do
    module_name=$(basename "$dir")
    if [ "$module_name" == "fixtures" ] || [ "$module_name" == "deprecated" ]; then
        continue
    fi
    if [ -d "$dir" ]; then
        # Check if module has test files
        test_files=$(find "$dir" -name "test_*.jl" 2>/dev/null)
        if [ -n "$test_files" ]; then
            # Check if module is in TEST_SETS
            if ! grep -q "\"$module_name\"" CleanMastProject/test/runtests.jl 2>/dev/null; then
                echo "  WARNING: Module '$module_name' may be missing from TEST_SETS"
            fi
        fi
    fi
done
echo "  Check complete"

# Run tests
echo "Running tests..."
if julia CleanMastProject/test/runtests.jl > /dev/null 2>&1; then
    echo "  PASS: All tests pass"
else
    echo "  FAIL: Some tests failed"
fi

echo "=== Review Complete ==="
```

## Common Violations

| Violation | Severity | Fix |
|-----------|----------|-----|
| Test files in `src/` | **Critical** | Move to `test/{Module}/` |
| Wrong file naming | **High** | Rename to `test_{feature}.jl` |
| Missing `@testset` | **High** | Wrap tests in `@testset` blocks |
| Tests without assertions | **High** | Add `@test` or `@test_throws` |
| Missing TEST_SETS entry | **Medium** | Add to `runtests.jl` |
| Using fixtures for simple data | **Low** | Use inline data instead |
| Missing edge case tests | **Medium** | Add tests for boundaries and errors |

## Approval Criteria

Approve the implementation when:

1. **Location**: All tests are in `test/` directory
2. **Naming**: All test files follow `test_{feature}.jl` convention
3. **Structure**: All tests use `@testset` blocks
4. **Assertions**: All tests have proper assertions
5. **Coverage**: Business logic has >80% coverage
6. **Runner**: All tests pass via `runtests.jl`
