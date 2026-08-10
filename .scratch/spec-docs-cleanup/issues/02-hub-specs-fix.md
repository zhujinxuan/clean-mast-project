# 02 — Fix hub specs: subdomains + reporting

**What to build:** Make the two hub specs accurate and non-redundant, so leaf specs (01) and the application spec (05) can safely defer to them. Edits to `packages/cleanmast/src/cleanmast/subdomains/spec.md` and `.../reporting/spec.md` only. Details in `.scratch/spec-docs-cleanup/findings.md`.

**Blocked by:** None — can start immediately

**Status:** done

subdomains/spec.md:

- [x] Move reporting-only rules 9–12 (capabilities, section.py, `from_inputs`, `render_subsection_content`) into reporting/spec.md
- [x] Fix capability path to `reporting/subdomains/{capability}/` (real layout)
- [x] Qualify rule 2 "never sideways" with the rule-10 render exception
- [x] Bound or delete rule 8 ("fits one file" wish)
- [x] Drop the code-default claim from the 业务说明 fill-heights line (keep the business fact)
- [x] Reduce rule 13 routing detail to a one-line pointer at shared/timeseries/spec.md (which owns the protocol)

reporting/spec.md:

- [x] Delete rules 2/4/5/6 and rule 8 (verbatim or weakened restatements of parent rules; rule 1 already declares inheritance)
- [x] Delete anti-patterns/when-in-doubt duplicated from the parent (IO-in-compute, infrastructure types, compute-vs-assemble)
- [x] Drop the capability enumeration from rule 3 (descriptive list stays in 业务说明)
- [x] Rule 7: make `parameters.air_density` an example, not a universal claim
- [x] Rule 10: drop the "never in a drift-log" clause → "tracked only as a ticket under `.scratch/`"
- [x] Hoist the orphaned lint anti-pattern (`` `Any`, `# type: ignore`, `str(path)`, bare `except:` ``) here ONCE, paired with positive targets (precise types, `pathlib.Path`, specific exceptions)
- [x] Hoist the `renderImage()` `Path()`-as-no-image-sentinel convention here from extreme_wind (applies to all atoms)
- [x] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review (4 reviewers, writing-for-agents rubric). Full quotes per line in `../findings.md`.
- Resolved 2026-08-10: rules 9–12 moved to reporting/spec.md with the corrected `reporting/subdomains/{capability}/` path; rule 2 qualified with the render exception; rule 8 bounded; rule 13 reduced to a pointer; reporting rules 2/4/5/6/8 and duplicated anti-patterns deleted; lint anti-pattern and renderImage sentinel hoisted to reporting/spec.md; baseline 6/6 green.
