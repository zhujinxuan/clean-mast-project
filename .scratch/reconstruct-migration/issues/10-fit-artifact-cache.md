# 10 — Fit artifact and cache

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Fix the fit artifact (TOML) and its cache lifecycle (charted in ticket 01, decisions 7 and 10: train-on-demand; cache key = (method, source, target, timerange, config hash); production fits retrain on full data; fold fits are benchmark evidence only).

Decide:

1. **TOML schema**: method id, source/target refs, training timerange, parameters (incl. sectorization where applicable), provenance, cleanmast version. What per-method parameter payload shape — free-form table per method vs fixed union schema?
2. **Storage layout**: Julia precedent `meso-models/<mast>/<meso>/windspeed/{16-sector|1-sector}.jld2`. Analogous tree in the Python project dir? Per-mast or global store?
3. **Cache invalidation**: config hash covers what — method params, heights, timerange? What happens when source data is re-cleaned (data hash in key? manual invalidation command?)?
4. **Benchmark fold fits**: kept inside the benchmark record artifact (ticket 06) or discarded after metrics; never loadable as production fits.
5. **Vertical fits**: same artifact machinery for shear/veer fits (they are methods under the unified contract) — per-interval parameters (ticket 08) in the payload.

Context: `FillHeightFitResult` TOML precedent in packages/cleanmast; memory `core://agent/4`.

## Acceptance

- [ ] Artifact schema + cache lifecycle recorded under `## Answer`
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 (ticket 04): today's `fill-models/` tree is write-only (`discover_fill_height_models` has zero consumers) and execute embeds copied parameters — the new cache replaces this wholesale. The design must include the **explicit-artifact reference mode** (direct fit TOML path + column mapping, for ad-hoc cross-pair transfers) alongside identity lookup; explicit mode is flagged `fit-transferred` and never emitted by recommend. Cache key's timerange element = training overlap only.
