# Spec: report-cleaning-section polish

Follow-up fixes for report section 2.3 数据清洗与插补 (merged in `9c9922a0` +
`c62f4f7d`), from review of the generated PDF for
`projects/2026-08-27-松原查干花镇1.2GW/` (3 masts: M3142/M5057/M5972).

Scope: presentation-only changes in
`packages/cleanmast/src/cleanmast/subdomains/reporting/subdomains/cleaning/`
(atoms, assemble, section). No pipeline/config changes. Report wording stays
Chinese, engineer style, no quality judgement.

Tickets: `issues/01`–`04`, all independent.

Context facts (verified 2026-08-27 against the project parquets):
- All 3 masts are single-channel at EVERY height (no tower-shading merge ever
  fires for this project) — drives ticket 04 wording.
- Violations YAMLs exist at `process-stats/process-clean-<mast>.yaml`.
- The 2.3.2 coverage table and 2.3.3 violations table currently render raw
  column names and (2.3.3) one long all-mast table.
