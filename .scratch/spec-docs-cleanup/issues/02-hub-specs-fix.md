# 02 — Fix hub specs: subdomains + reporting

**What to build:** Make the two hub specs accurate and non-redundant, so leaf specs (01) and the application spec (05) can safely defer to them. Edits to `packages/cleanmast/src/cleanmast/subdomains/spec.md` and `.../reporting/spec.md` only. Details in `.scratch/spec-docs-cleanup/findings.md`.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

subdomains/spec.md:

- [ ] Move reporting-only rules 9–12 (capabilities, section.py, `from_inputs`, `render_subsection_content`) into reporting/spec.md
- [ ] Fix capability path to `reporting/subdomains/{capability}/` (real layout)
- [ ] Qualify rule 2 "never sideways" with the rule-10 render exception
- [ ] Bound or delete rule 8 ("fits one file" wish)
- [ ] Drop the code-default claim from the 业务说明 fill-heights line (keep the business fact)
- [ ] Reduce rule 13 routing detail to a one-line pointer at shared/timeseries/spec.md (which owns the protocol)

reporting/spec.md:

- [ ] Delete rules 2/4/5/6 and rule 8 (verbatim or weakened restatements of parent rules; rule 1 already declares inheritance)
- [ ] Delete anti-patterns/when-in-doubt duplicated from the parent (IO-in-compute, infrastructure types, compute-vs-assemble)
- [ ] Drop the capability enumeration from rule 3 (descriptive list stays in 业务说明)
- [ ] Rule 7: make `parameters.air_density` an example, not a universal claim
- [ ] Rule 10: drop the "never in a drift-log" clause → "tracked only as a ticket under `.scratch/`"
- [ ] Hoist the orphaned lint anti-pattern (`` `Any`, `# type: ignore`, `str(path)`, bare `except:` ``) here ONCE, paired with positive targets (precise types, `pathlib.Path`, specific exceptions)
- [ ] Hoist the `renderImage()` `Path()`-as-no-image-sentinel convention here from extreme_wind (applies to all atoms)
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review (4 reviewers, writing-for-agents rubric). Full quotes per line in `../findings.md`.
