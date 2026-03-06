<!-- NOTE: CLAUDE.md and AGENTS.md must be kept in sync! -->

# CleanMast Project Guide for Claude Code

CleanMast is a comprehensive toolkit for processing wind energy meteorological tower data.

## Quick Reference

| What | Command |
|------|---------|
| Run tests | `julia CleanMastProject/test/runtests.jl [test_set]` |
| Type check (Python) | `uv run ty check packages/cleanmast` |
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

## Critical Rules

| Rule | ADR |
|------|-----|
| Use Symbols for DataFrame columns | data-001 |
| Never pattern-match column names | domain-001 |
| Use sensor.columnName for column access | domain-001 |
| Functional style over imperative loops | data-002 |
| Type annotations on all functions | types-001 |
| Use `@with_kw` for config structs | config-001 |
| Use Comonicon `@cast` for CLI | cli-001 |

## File Path Convention (CRITICAL)

**File tools:** Use Windows backslashes  
`C:\Users\zhu_j\workspace\developing\clean-mast-project\file.txt`

**Shell commands:** Use forward slashes or escaped backslashes  
`C:/Users/zhu_j/workspace/file.txt` or `C:\\Users\\zhu_j\\workspace\\file.txt`

---

*For detailed constraints, see the relevant ADR in CleanMastProject/adr/*
