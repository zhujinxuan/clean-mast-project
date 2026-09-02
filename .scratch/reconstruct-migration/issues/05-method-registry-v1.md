# 05 — Method registry v1

**Type:** grilling

**Status:** resolved

**Blocked by:** None

## Question

Fix the v1 method registry: which methods exist, how they are identified, and the registry mechanism.

Candidates on the table:

- **Cross/meso WS**: `ols-1sector`, `ols-16sector`, `variance-ratio`
- **Cross/meso WD**: `constant-offset`, `sectorized-offset`
- **Vertical** (charted as 2×2 families, ticket 01): WS-extrapolate (time-scale × layer-scheme matrix, ticket 07), WS-interpolate (log-linear, ticket 08), WD-extrapolate (veer offset), WD-interpolate (circular)

Decide:

1. **Method id scheme / namespacing**: flat ids vs family-qualified (e.g. `vertical.ws.extrapolate.powerlaw.monthly`)? Must be stable — ids live in fit artifacts and config.
2. **Registry mechanism**: structural protocol (Python `Protocol`) vs enum + dispatch table? Where it lives (subdomain placement per spec.md).
3. **v1 cut**: which candidates make v1, which are backlog.
4. **16-sector's dual life**: it exists in Julia as a reconstruction method AND as the rep-year slope source. Does it survive as a general reconstruction method, only feed rep-year (ticket 12), or both?

Context: memory `core://agent/4`; 2026-08-28 proposal was registry via structural protocol.

## Answer

Decided 2026-09-01, user-confirmed (grilling, 2 rounds):

1. **Method id grammar**: `<scope>.<variable>.<algorithm>[.<variant>...]` — every segment from a closed enum vocabulary, validated at config load; ids are **add-only forever** (they live in fit artifacts and configs). Scope ∈ {`horizontal`, `vertical`}: horizontal = series→series across locations (cross-mast and meso share it — same algorithms, source kind is a property of the reconstruction set, not the id); vertical = across heights within one mast. Candidate-matrix dimensions are **id segments, not params**: law family, layer scheme, time scale are all visible in the id (`vertical.ws.extrapolate.powerlaw.top3.1h`); `.powerlaw` is kept explicit so `loglinear` can enter additively later. What remains as params: per-method tuning knobs only (e.g. `min_points_per_sector`). Rationale: benchmark candidates are distinct methods (the ε-group sort ranks ids), configs/artifacts are audit-readable against 规范 without decoding a params table, and each id gets a fixed payload schema.
2. **Registry mechanism**: identity and schema in `shared/reconstruction/` (forced by the import contracts — subdomains can't import siblings, so `MethodId` StrEnum + per-method Params/FitPayload Pydantic models must live in shared; justified exception to the "no context-specific types in shared" anti-pattern, models stay Pydantic-pure); behavior in `dataprocessing` as a `MethodSpec` registry — frozen dataclass binding each `MethodId` to exactly one params type, one fit-payload type, and two **stateless pure functions** (no `self`, no base class; `MethodId` is a fit/predict parameter so variant ids share one implementation). Signatures on the existing `TimeSeriesData`/`TimeRange` shared types. Clean cutover: delete the stale `services/strategies/` duplicate (phantom protocol), replace both legacy id encodings (free-text `'1-sector'`, column-suffix `:interpolated`).
3. **v1 cut**: horizontal WS {`ols-1sector`, `ols-16sector`, `variance-ratio`}, horizontal WD {`constant-offset`, `sectorized-offset`}, vertical all four families (`vertical.ws.extrapolate.powerlaw.<layers>.<time>` — layers ∈ {top3, dist-weighted, above50m, all} × time ∈ {10min, 1h, month, series}; `vertical.wd.extrapolate.<global|sector>.<1h|month|series>`; `vertical.ws.interpolate.<law>`; `vertical.wd.interpolate.circular`). **Log-law excluded from v1** — not in Chinese 规范 (GB/T 18710 prescribes the power-law kernel); backlog alongside LR2 (OLS-with-residuals), sector-conditional shear refits, ML methods.
4. **16-sector dual life**: both — first-class benchmarkable method AND rep-year slope source (Julia semantics). Rep-year declares its need by identity; the deterministic cache makes "reuse if possible" automatic — cache hit when reconstruction already produced the same (method, source, target, timerange, config hash), train-on-demand otherwise. No cross-stage coupling. `min_points_per_sector` param: default **20** (literature: ≥20 per 30° bin; our 22.5° bins are sparser), override **5** for Julia-parity fixture runs only.
5. **Deferred, logged elsewhere**: meso↔mast temporal alignment rule (train on coarser grid, interpolate meso up front for predict/fill — linear methods commute with interpolation) → ticket 06 comment; Chinese 行标 rep-year procedure (global mean delta → per-sector linear sectored by **mast** direction → reduce) as a future calibration method, and rep-year's consumption/benchmarking → ticket 12 comment; fit payload **storage layout** → ticket 10.

Veto procedure: comment on this ticket and reopen (Status: ready-for-human) if any decision needs revisiting.

## Acceptance

- [x] Registry design + v1 method list recorded under `## Answer`
- [x] Method id scheme documented in CONTEXT.md
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-01 (ticket 07 grilling, user decision): **vocabulary rename** — the id grammar segment `variable` is renamed **sensor type** (`<scope>.<sensor-type>.<algorithm>[.<variant>...]`), binding the id to the existing Sensor glossary term (`CONTEXT.md`). No method id changes: the segment values were and remain `ws`/`wd`.

- 2026-08-31 research (ticket 02, `research/mcp-benchmarking.md`): literature precedent is ≥20 points per sector bin — Julia's ≥5-point fallback is below it. Weigh when defining `ols-16sector`'s fallback rule.
- 2026-09-01 grilling round 1 (partial): **log-law (loglinear) excluded from v1** — not in Chinese 规范 (GB/T 18710 et al. prescribe the power-law kernel for vertical shear; consistent with MEASNET §9.4's power-law mandate). Backlog candidate, revisit if 规范 or project requirements change. Q1/Q2/Q4 still open.

- 2026-09-01 (ticket 08, resolved): **interpolation registry amended** — `vertical.ws.interpolate.<law>` is replaced by the blend family `vertical.ws.interpolate.powerlaw.<layer-scheme>.<scale>` (v1 scheme `brackets`, scales `{10min, 1h, month, series}`; `loglinear` never lands); `vertical.wd.interpolate.circular` is replaced by `vertical.wd.interpolate.linear.<layer-scheme>.<scale>` (`brackets` × 4 scales). Interpolation gains the explicit layer-scheme segment, mirroring the extrapolate id structure; future schemes (e.g. `dist-weighted`) enter additively.

- 2026-09-01 (user decisions, see ticket 07 amendment): **`dist-weighted` removed from the v1 cut** (target-relative weighting ⇒ per-target-height retraining — too complex/slow); WS extrapolate layer schemes are `{top3, above50m, all}` (matrix 16 → 12). WD-extrapolate gains the layer-scheme segment with v1 scheme `top3`: `vertical.wd.extrapolate.<global|sector>.top3.<1h|month|series>`, with slope semantics (deg/m veer slope from the top-3 WD layers, applied from the top-layer anchor).
