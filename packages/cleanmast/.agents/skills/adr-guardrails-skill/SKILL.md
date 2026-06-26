---
name: adr-guardrails-skill
description: Enforces ADR constraints during plan review (Momus) and implementation review (Atlas). Triggers on ADR enforcement, plan review, implementation review, and architecture validation. Hard Block policy — non-compliant code is REJECTED.
license: MIT
compatibility:
  python: ">=3.12"
  uv: ">=0.4"
metadata:
  category: architecture
  tier: foundational
  tags: [adr, guardrails, constraints, architecture, enforcement, agent, ai]
  scope: project-level
---

## Overview

Enforces ADR constraints during plan review (Momus) and implementation review (Atlas). Hard Block — non-compliant code is REJECTED. This is a framework skill — specific check rules live in each ADR's phase files.

## When to Use

Triggers: ADR enforcement, plan review, implementation review, architecture validation

Load this skill when:
- Momus is reviewing a plan against architecture constraints
- Atlas is verifying implementation against ADR rules
- An agent needs to determine which ADRs apply to a given change
- Enforcement status needs to be checked or updated

## Enforcement Model

Each ADR declares its enforcement in two ways:

1. **Frontmatter**: `enforced: true` or `enforced: false`
2. **## Enforcement section**: For enforced ADRs, declares `method` (import-linter | ast-grep | agentic-lint)

Example ADR frontmatter:

```yaml
---
id: ddd-s-003
status: accepted
enforced: true
---
```

Example Enforcement section:

```markdown
## Enforcement

method: import-linter
contracts:
  - contract_name: no-cross-subdomain-imports
    modules:
      - cleanmast.subdomains.assessment
      - cleanmast.subdomains.processing
    forbidden_imports:
      - cleanmast.subdomains.assessment.*
```

## Dispatch Workflow

```
Atlas/Momus loads this skill → scans ADR directory → for each ADR with enforced:true:
  - Reads ## Enforcement.method
  - import-linter → runs specified contracts
  - ast-grep → runs specified patterns
  - agentic-lint → spawns subagent with ADR + review-implementation.md
  - Updates {adr}.version.json (hash, timestamp, result)
  - Any failure → Hard Block REJECT
```

### Enforcement Methods

| Method | When Used | How It Works |
|--------|-----------|--------------|
| import-linter | Import rules, dependency direction, forbidden modules | Runs import-linter contracts against the codebase |
| ast-grep | Structural patterns, naming conventions, code shape | Runs ast-grep rules against matching files |
| agentic-lint | Complex semantic checks, design intent, cross-file reasoning | Spawns a subagent with the ADR and review phase file |

## Manifest Format

Each enforced ADR has `{adr}.version.json`:

```json
{
  "adr_hash": "sha256 of ADR content",
  "last_check": "ISO timestamp or null",
  "last_result": "pass" | "fail" | null,
  "checked_files": ["file1.py", "..."]
}
```

When `adr_hash` changes, the ADR content has been updated and must be re-checked.

## Entry Points

- **review-plan.md**: Momus entry — checks proposed changes against ADRs
- **review-implementation.md**: Atlas entry — verifies actual code against ADRs

## Phase-Based Loading

| Phase | Purpose | File |
|-------|---------|------|
| Plan | Design planning | `phases/{adr}/on-plan.md` |
| Code | Implementation | `phases/{adr}/code.md` |
| Review Plan | Plan review checks | `phases/{adr}/review-plan.md` |
| Review Impl | Implementation checks | `phases/{adr}/review-implementation.md` |

## Migration Mode

ADRs with `enforced: false` or without `## Enforcement` section are skipped during enforcement. This supports gradual migration where old ADRs are not yet enforced.

## Override

This project-level skill overrides the user-level `adr-guardrails-skill`. Checks here take precedence during Momus/Atlas invocation.
