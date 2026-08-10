# 01 — Strip boilerplate from the 9 reporting leaf specs

**What to build:** Each reporting capability leaf spec keeps only Purpose, capability-specific rules, leaf-specific anti-patterns, and 业务说明. The shared block (pipeline stages, compute/assemble purity, frozen=True, sibling-import ban, compute-vs-assemble when-in-doubt) is inherited from reporting/spec.md + subdomains/spec.md and must not be restated. Files: all 9 under `packages/cleanmast/src/cleanmast/subdomains/reporting/subdomains/*/spec.md`. Details in `.scratch/spec-docs-cleanup/findings.md`.

**Blocked by:** None — 02-hub-specs-fix done 2026-08-10 (commit 7b933e25)

**Status:** ready-for-agent

- [ ] No leaf restates pipeline order, compute purity, frozen=True, sibling-import ban, or the compute-vs-assemble when-in-doubt
- [ ] The 9-way cloned lint line (`` `Any`, `# type: ignore`, `str(path)`, bare `except:` ``) appears in ZERO leaves (it now lives in reporting/spec.md per 02)
- [ ] Capability-specific rules survive intact: SECTOR_COUNT (wind_rose), stateless fitter (weibull), IEC constants (turbulence), Polars vectorization (wind_frequency), renderImage sentinel → moved to reporting (extreme_wind), 4×4 grid (representative_year)
- [ ] wind_temporal and air_density (zero capability-specific rules today) end as Purpose + 业务说明 — or gain real capability rules if the implementer identifies them
- [ ] Each leaf keeps an explicit one-line inheritance note pointing at reporting/spec.md
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review. The wind_frequency copy had already drifted from its siblings — direct evidence the copies cannot be maintained. Full quotes in `../findings.md`.
