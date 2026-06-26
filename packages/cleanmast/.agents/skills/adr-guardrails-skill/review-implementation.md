# Implementation Verification — Atlas Entry Point

## Purpose

Run during final verification by Atlas. Hard Block — REJECT if any enforced ADR fails. Verifies actual code against ADR constraints.

## Pre-Check

1. Scan for ADRs with `enforced: true` frontmatter
2. For each: check if `{adr}.version.json` needs update (hash changed?)
3. If hash unchanged and `last_result = "pass"`: skip (no re-check needed)
4. If hash changed or `last_result != "pass"`: run full check

## Enforcement Dispatch

For each ADR with `enforced: true`, read `## Enforcement.method` and dispatch:

### method: import-linter

1. Run: `import-linter` with contracts specified in `## Enforcement.import_linter_contracts`
2. Report violations

### method: ast-grep

1. Run: `ast-grep search` with patterns specified in `## Enforcement.ast_grep_patterns`
2. Report matches (violations)

### method: agentic-lint

1. Spawn subagent with:
   - ADR full content
   - `phases/{adr}/review-implementation.md` (check script)
   - Code files to check
2. Subagent executes each check from the script
3. Subagent returns: pass/fail per check

## Manifest Update

After each ADR check:

```
Update {adr}.version.json:
  - adr_hash: recompute sha256 of ADR content
  - last_check: current timestamp
  - last_result: "pass" or "fail"
  - checked_files: list of files examined
```

## Output Format

```
ADR: ddd-s-003-subdomain-deepening (method: agentic-lint)
  Check 1: import-isolation → PASS
  Check 2: shared-purity → PASS
  ...
  VERDICT: APPROVE

ADR: structure-001-subdomain-layout (method: agentic-lint)
  ...
  VERDICT: APPROVE

Overall: 2/2 ADRs pass → APPROVE
```

## Hard Block Policy

If ANY enforced ADR returns FAIL:

- REJECT the changes
- Report which ADR(s) failed and which check(s)
- Do NOT let code proceed
