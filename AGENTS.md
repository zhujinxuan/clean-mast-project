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

## Architecture Decision Records (ADRs)

**Location:** `CleanMastProject/adr/` (Julia package)

This project uses ADRs as guardrails. Before working on code, identify and read relevant ADRs.

| Task | ADRs to Load |
|------|--------------|
| New Julia code | stack-001, types-001, data-002 |
| Data processing | data-001, data-002, domain-001 |
| CLI commands | cli-001, structure-001, types-001 |
| Configurations | config-001, types-001 |
| Sensor data | domain-001, data-001 |
| Tests | testing-001, data-002 |
| Documentation | docs-001, domain-001 |

**See:** `CleanMastProject/adr/README.md` for full ADR index.  
**Note:** Future Python packages will have their own ADRs under `packages/{name}/adr/`.

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

## Critical Rules (Julia)

| Rule | ADR |
|------|-----|
| Use Symbols for DataFrame columns | data-001 |
| Never pattern-match column names | domain-001 |
| Use sensor.columnName for column access | domain-001 |
| Functional style over imperative loops | data-002 |
| Type annotations on all functions | types-001 |
| Use `@with_kw` for config structs | config-001 |
| Use Comonicon `@cast` for CLI | cli-001 |

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
4. **dvc-verify** - Dataset verification

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
