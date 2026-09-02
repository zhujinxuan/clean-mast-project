# 16 — Parallelism and performance of run-phase fit/predict

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** 13-pipeline-orchestration-config

## Question

Graduated from the map's Not-yet-specified after ticket 10 resolved the cache shape (the last dependency this fog patch was waiting on; the operator contract settled in ticket 04).

Decide the parallelism and performance model for run-phase commands (`reconstruct-single`, `reconstruct-cross`, `reconstruct-meso`, `fill-heights`, rep-year):

1. **Parallelism unit**: fits and full-series predicts span masts × reconstruction sets × target sensors. What parallelizes — process pool over masts? over sets? sequential with Polars-vectorized inner loops? What are the memory bounds of full-series predict at 10-min resolution over long planned windows?
2. **Cache interaction**: concurrent commands/processes computing the same cache key — is simultaneous train-and-write a hazard (last-writer-wins acceptable since training is deterministic?), or does the store need write discipline (temp-file-then-rename, locking)?
3. **Benchmark-phase parallelism**: fold fits are the O(candidates × folds × methods) hot spot — same model as run phase, or does the benchmark get its own (its fits are discarded, so no cache-write hazard)?

Context: cache shape and invalidation in ticket 10 `## Answer`; deterministic training (same key → same fit) is already a premise of the cache; fit-free methods (ticket 08) have no cache interaction at all.

## Acceptance

- [ ] Parallelism/performance model recorded under `## Answer`
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-02: graduated from the map's Not-yet-specified — "depends on contract + cache shape" is now satisfied (tickets 04, 10 resolved). Blocked by 13 because the commands whose parallelism is being designed are defined there.
