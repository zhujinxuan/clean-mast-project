# Anti-Patterns — Reporting Subdomain

Audit date: 2026-06-26. Updated: 2026-07-26. Checked against `reporting/spec.md` and `subdomains/spec.md`.

> All entries resolved. (V1–V6, S2, S11, D1) removed 2026-07-21; the remainder
> (V7, V8, S13, S6; S8, S9, S12, S7; S10; S4; S14; S3) resolved 2026-07-26
> across waves 1–5, each with the baseline gate green and the kp-202603-report
> `report.typ` regenerated to confirm impact.
> S3 (final entry): untyped `list[dict[str, Any]]` / bare `list[dict]`
> accumulators replaced with TypedDicts mirroring each capability's existing
> dataframely schemas (extreme_wind, wind_temporal, turbulence,
> representative_year), plus missing parameter annotations. Typing-only —
> report.typ byte-identical.
> This audit is now closed; reopen entries only for newly discovered issues.

---

## VIOLATIONS

None open.

---

## SMELLS

None open.
