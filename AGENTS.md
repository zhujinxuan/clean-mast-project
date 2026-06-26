<!-- NOTE: CLAUDE.md and AGENTS.md must be kept in sync! -->

# CleanMast Project Guide for Claude Code

CleanMast is a comprehensive toolkit for processing wind energy meteorological tower data.

## Quick Reference

| What | Command |
|------|---------|
| Run tests | `julia CleanMastProject/test/runtests.jl [test_set]` |
| Type check (Python) | `uv run ty check packages/cleanmast` |
| Run verification baseline | `uv run python scripts/verify_baseline.py` |
| Load Polars skill | `skill(name="polars")` |

## Spec-Driven Architecture

Each context and capability has a co-located `spec.md` with rules, anti-patterns, and guidance.

| When | Load |
|------|------|
| New code in a context | Read `subdomains/spec.md` + the context's `spec.md` |
| Cross-context integration | Read `shared/spec.md` |
| Verification | Use `skill(name="spec-guardrails")` |

## Workspace Structure

```
clean-mast-project/
├── CleanMastProject/     # Julia package (production)
│   ├── src/              # Source code
│   ├── test/             # Test suite
│   └── adr/              # Architecture Decision Records
└── packages/             # Python packages (in development)
    ├── preprocess-tools/
    └── cleanmast/
```

## Critical Rules (Python)

| Rule | Rationale |
|------|-----------|
| **Always specify `encoding="utf-8"`** when reading/writing text files | Windows defaults to `gbk` (Chinese locale) or `cp1252` (Western), causing `UnicodeDecodeError` on JSON, typst source, and log files. Never rely on system default. |
| Use Pydantic `BaseModel` for all IR types | Type safety, JSON round-trip, validation |
| Use `pathlib.Path` for all file operations | Cross-platform compatibility |

## Critical Rules (Julia)

| Rule | Rationale |
|------|-----------|
| Use Symbols for DataFrame columns | Required by the DataFrames.jl column API |
| Never pattern-match column names | Use sensor metadata instead of fragile string matching |
| Use sensor.columnName for column access | Column names may change during preprocessing |
| Functional style over imperative loops | Prefer filter/map over imperative `push!` loops |
| Type annotations on all functions | Catch errors early and document interfaces |
| Use `@with_kw` for config structs | Standardize keyword-based construction |
| Use Comonicon `@cast` for CLI | Consistent modular CLI structure |

## Verification Baseline

Run after every implementation task, before committing:

```bash
uv run python scripts/verify_baseline.py  # All packages
uv run python scripts/verify_baseline.py --package cleanmast  # Single package
```

**What it does:** Runs 4 checks sequentially:
1. **ty** - Type checking
2. **ruff** - Linting  
3. **pytest** - Unit tests
4. **dvc-verify** - Dataset verification (10 min timeout for DVC experiments)

**Output:** Per-package baseline files at `packages/{package}/baseline-{timestamp}.md`
- Small errors (<500 chars): Inline in markdown
- Large errors (≥500 chars): Written to `baseline-refs/{timestamp}-{tool}.json`

**When to run:** After completing implementation, before git commit.

### Baseline-Driven Development Workflow

**Skill available:** `skill(name="baseline-driven-dev")`

Use this skill when:
- Planning implementation with verification requirements
- Setting up waves that must pass baseline checks  
- Analyzing ty/ruff/pytest errors from baseline reports

**Quick workflow:**
1. **Prometheus** (planning): Generate baseline → Design waves → Set targets
2. **Atlas** (orchestration): Run wave → Regenerate baseline → Verify improvement → Commit
3. **Key principle:** *"If the baseline doesn't improve, the wave isn't done."*

**Wave targets:**

| Wave | ty | ruff | pytest |
|------|-----|------|--------|
| 1 (Cleanup) | Maintain | **PASS** | Maintain |
| 2 (Types) | **Improved** | PASS | Maintain |
| 3 (Tests) | Improved | PASS | **Improved** |
| 4 (Polish) | **PASS** | PASS | Improved |

For detailed workflow, load the skill with `skill(name="baseline-driven-dev")`
