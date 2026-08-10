# 06 — Format unification and sediment sweep

**What to build:** Final pass after the content tickets: delete leftover sediment and verify the flat 5-section format (Purpose / Rules / Anti-patterns / When in doubt / 业务说明) holds across all 16 spec.md files — the format decision taken 2026-08-10.

**Blocked by:** 01-leaf-boilerplate-dedup, 05-application-spec-deepen (03-seam-specs-facts done 2026-08-10)

**Status:** done

- [x] Delete `packages/cleanmast/src/cleanmast/subdomains/spec-template.md` (stray template from the deleted spec-guardrails system)
- [x] Archive or delete `reporting/anti-pattern.md` (self-declared closed 2026-07-26; sediment beside the spec)
- [x] Verify all 16 spec.md files use the flat 5-section skeleton; no `## Code rules` wrappers remain (application, dataprocessing converted by their tickets)
- [x] Verify 业务说明 subsection usage is deliberate per leaf (Business constraints present where genuine content exists, consciously minimal elsewhere — note the choice in each file)
- [x] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review. Full quotes in `../findings.md`.
- Resolved 2026-08-10: `subdomains/spec-template.md` and `reporting/anti-pattern.md` deleted (git history preserves both). Format sweep: zero `## Code rules` wrappers or h3 section headings remain across all 16 spec.md files. 业务说明 subsection variance across leaves is deliberate — Business constraints present only where genuine content exists (weibull, turbulence, vertical_profile, extreme_wind); minimal elsewhere.
