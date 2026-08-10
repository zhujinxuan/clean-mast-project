# 06 — Format unification and sediment sweep

**What to build:** Final pass after the content tickets: delete leftover sediment and verify the flat 5-section format (Purpose / Rules / Anti-patterns / When in doubt / 业务说明) holds across all 16 spec.md files — the format decision taken 2026-08-10.

**Blocked by:** 01-leaf-boilerplate-dedup, 05-application-spec-deepen (03-seam-specs-facts done 2026-08-10)

**Status:** ready-for-agent

- [ ] Delete `packages/cleanmast/src/cleanmast/subdomains/spec-template.md` (stray template from the deleted spec-guardrails system)
- [ ] Archive or delete `reporting/anti-pattern.md` (self-declared closed 2026-07-26; sediment beside the spec)
- [ ] Verify all 16 spec.md files use the flat 5-section skeleton; no `## Code rules` wrappers remain (application, dataprocessing converted by their tickets)
- [ ] Verify 业务说明 subsection usage is deliberate per leaf (Business constraints present where genuine content exists, consciously minimal elsewhere — note the choice in each file)
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review. Full quotes in `../findings.md`.
