# 10 — Fit artifact and cache

**Type:** grilling

**Status:** resolved

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

- [x] Artifact schema + cache lifecycle recorded under `## Answer`
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)

## Answer

Decided 2026-09-02 (grilling, 2 rounds + clarifications, user-confirmed):

1. **Artifact schema — one envelope, dispatched payload.** A single `FitArtifact` envelope model for all scopes. Envelope fields: `method` (MethodId), `source` (typed ref), `target` (typed ref), `training_overlap` (TimeRange), `params` (verbatim copy of the tuning params that trained the fit — self-description, never used for lookup), `created_by` (command name), `cleanmast_version`. The `parameters` section is the method's `FitPayload` model (ticket 05, `shared/reconstruction/`) serialized; load-time dispatch on `method` id via the registry. Fit evidence (`n_points`, `r_squared`, per-sector fallback counts) lives in the payload, per method, only where produced. No screen/forced markers in the fit — those describe a benchmark decision and live in the benchmark artifact + run manifest (this keeps a `fit-transferred` artifact free of verdicts belonging to a different pair).
   - **Refs are qualified.** Target = `{mast, sensor}`; source = `{kind: meso, dataset, point}` | `{kind: mast, mast, sensor}`. Sensor names are unique per mast, so `(mast, sensor)` is unique project-wide. Target mast is a *component* of the target ref, never a separate cache-key element (a sensor belongs to exactly one mast entity — the two could never vary independently).
   - **Granularity.** Horizontal: one artifact per (method × source × target sensor) — each target sensor has its own training overlap, so the cache key maps 1:1 to a file. Vertical: one artifact per (mast × sensor type × method); per-interval bucket tables are payload rows (ticket 08).

2. **Cache key** = (method id, source ref, target ref, training overlap, config hash). The **config hash covers the method's `params` only** — refs and overlap are already separate key elements. Computed at run time from the run-phase strategy config: the method id selects the params type from the registry, the config's params block is validated into it (recommend materializes all defaults as required fields), canonical serialization → hash. The params that produce the hash are the params that train the fit on a miss — same config block, same run; they cannot drift apart.

3. **Storage layout — identity-derived tree, overwrite-on-retrain.** Replaces the write-only `fill-models/` tree wholesale (ticket 04 comment):
   - horizontal: `fits/horizontal/<target-mast>/<source-slug>/<method-id>/<target-sensor>-fit.toml`, source-slug = `meso-<dataset>-<point>` / `mast-<mast>-<sensor>`
   - vertical: `fits/vertical/<mast>/<method-id>/<sensor-type>-fit.toml`
   Retraining on a new overlap or new params overwrites the same path: the cache is a cache, not an archive; the per-run provenance manifest (ticket 04) is the audit trail. Explicit-artifact mode bypasses the store entirely — direct path, flagged `fit-transferred`, no key computed.

4. **Invalidation is explicit.** The key deliberately does not watch source data: if clean re-runs rewrite a source parquet with unchanged config, the old fit is reused. Retraining after a data change is the user's explicit act: `cleanmast fits clear [--mast …]` or a `--retrain` run flag. Rationale: fits are cheap to retrain (train-on-demand), and data stamps/content hashes would read the training data on every cache lookup.

5. **Where the cache is consulted.** Run-phase commands only (`reconstruct-single`, `reconstruct-cross`, `reconstruct-meso`, `fill-heights`, rep-year), at fit lookup: hit → load, miss → train on the full training overlap + write. Cross-stage reuse is automatic via identical keys (rep-year consuming the 16-sector fit's slopes hits the reconstruction-produced fit when params match — ticket 05). NOT consulted by: the benchmark commands (fold fits are discarded evidence, never cached), recommend (metadata-only), fit-free methods (`…interpolate.*.brackets.10min` — no artifact exists, ticket 08).

6. **Benchmark isolation.** The benchmark artifact is metrics-only: screen table, fold metrics, winner summary — zero serialized parameters, nothing in it loadable as a fit. Production fits exist only via run-phase train-on-demand (ticket 01 §10).

7. **16-sector per-sector fallback** (surfaced mid-grilling). A sector with fewer than `min_points_per_sector` points falls back to the overall (all-sector) OLS fit trained on the full training overlap; hard error only when the overall fit itself is untrainable — guarded upstream by the feasibility screen, so the error path is a guard, not a normal flow. The payload records per-sector `n_points` and fallback flags. Julia semantics preserved (≥5 → per-sector else overall); default 20 = literature, 5 = parity override (ticket 05). Same coarser-estimate fallback pattern as ticket 08's time buckets: fall back to the coarser, better-populated estimate; never fabricate, never silently null.

## Comments

- 2026-09-01 (ticket 08, resolved): fit-free methods exist — `…interpolate.*.brackets.10min` trains nothing, so the cache handles only training methods; the provenance manifest's fit-key applies only where a fit exists; strategy config carries the method id alone for fit-free methods. Interpolation training fits (`1h`/`month`/`series`) carry per (adjacent interval × time bucket) $\bar\alpha$ / veer-offset tables — one fit per (mast × sensor type × method), intervals as rows. Principle: a method is fit-free iff predict re-derives everything from observed data at predict time.

- 2026-08-31 (ticket 04): today's `fill-models/` tree is write-only (`discover_fill_height_models` has zero consumers) and execute embeds copied parameters — the new cache replaces this wholesale. The design must include the **explicit-artifact reference mode** (direct fit TOML path + column mapping, for ad-hoc cross-pair transfers) alongside identity lookup; explicit mode is flagged `fit-transferred` and never emitted by recommend. Cache key's timerange element = training overlap only.
