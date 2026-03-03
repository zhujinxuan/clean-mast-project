# Phase: review-plan - Review Test Plans

## When to Use

Load this file when:
- Reviewing test strategy for a new feature
- Validating test coverage plans
- Checking fixture design
- Reviewing test set organization

## Related ADR

- [ADR-testing-001: Julia Testing Standards](../testing-001-julia-testing-standards.md)

## Review Checklist

### Test Structure Review

- [ ] Test directory mirrors source structure (`test/{Module}/` → `src/{Module}/`)
- [ ] Test files follow `test_{feature}.jl` naming
- [ ] Test runner entries added to `TEST_SETS` dict in `runtests.jl`
- [ ] No test files in `src/` directory
- [ ] Fixtures are in `{Module}/fixtures/` subdirectory

### Test Coverage Review

- [ ] All public functions have corresponding tests
- [ ] Edge cases are documented and planned
- [ ] Error conditions have test coverage
- [ ] Coverage target is defined (>80% for business logic)

### Fixture Design Review

- [ ] Fixture utilities are reusable across tests
- [ ] Complex scenarios use fixtures (CSV/TOML/generator)
- [ ] Simple tests use inline data (no file I/O)
- [ ] Fixture data is representative of real data
- [ ] Generator functions produce deterministic output (seeded random if used)

### Test Organization Review

- [ ] Test sets are nested logically
- [ ] Test set names are descriptive
- [ ] Related tests are grouped together
- [ ] No duplicate test coverage

## Common Issues to Flag

| Issue | Example | Fix |
|-------|---------|-----|
| Test in wrong directory | `test/test_parser.jl` instead of `test/ParseSensors/test_parser.jl` | Move to module subdirectory |
| Wrong file naming | `parser_test.jl` instead of `test_parser.jl` | Rename to `test_{feature}.jl` |
| Missing @testset | Direct `@test` calls without `@testset` wrapper | Add `@testset` blocks |
| Fixtures for simple data | Using CSV files for single value tests | Use inline data |
| Missing test runner entry | New test file not in `TEST_SETS` | Add to `runtests.jl` |

## Approval Criteria

Approve the test plan when:

1. **Structure**: Test directory mirrors source structure
2. **Naming**: All test files follow `test_{feature}.jl` convention
3. **Coverage**: >80% business logic coverage planned
4. **Fixtures**: Appropriate use of inline vs fixture data
5. **Organization**: Clear `@testset` hierarchy defined
