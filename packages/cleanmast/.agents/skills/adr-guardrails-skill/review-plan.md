# ADR Guardrails: Plan Review

Run during plan review by Momus. Check that proposed file changes and architectural plans match ADR patterns before code is written. Catches architecture drift at the design stage.

## Pre-Check

1. Scan `packages/cleanmast/adr/` for all ADRs with `enforced: true` in frontmatter
2. For each: read `## Enforcement` section to determine method
3. Skip ADRs with `enforced: false` (migration mode)

## Plan-Level Checks

For each enforced ADR:

1. Load `phases/{adr}/review-plan.md` for ADR-specific plan checks
2. Verify proposed directory structure matches allowed patterns from `structure-001`
3. Verify planned imports respect bounded context boundaries from `ddd-s-001`
4. Verify new files will have ADR-GUARDRAILS comments planned
5. If new subdomains planned → verify per-domain ADRs planned

## Output Format

```
ADR: ddd-s-003-subdomain-deepening
  Plan check 1: Proposed directory structure → PASS
  Plan check 2: Planned imports isolation → PASS
  ...
  VERDICT: APPROVE

ADR: structure-001-subdomain-layout
  ...
  VERDICT: APPROVE

Overall: 2/2 ADRs pass → APPROVE
```

## Integration

This is invoked by Momus via the skill framework. Momus loads this file, executes checks against the proposed plan, and reports results. Any ADR REJECT → plan must be revised before implementation.

Momus dispatches to per-ADR review-plan phase files for detailed checks. See the enforcement dispatch workflow in `SKILL.md` for the full dispatch protocol.
