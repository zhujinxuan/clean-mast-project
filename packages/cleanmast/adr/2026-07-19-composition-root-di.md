# ADR: Composition Root + Dependency Injection for CLI Isolation

**Status**: ACCEPTED (implemented — see `bootstrap.py` and `application/spec.md`)
**Date**: 2026-07-19
**Completes**: archived `ddd-s-002-context-maps` (protocol + DI in bootstrap.py — prescribed, never built)
**Blocks**: `cli-isolation` contract going KEPT; package `.importlinter` joining `verify_baseline.py`

## Context

`cli-isolation` is BROKEN on 3 transitive chains: `cli → adapters → application →
dataprocessing` (×2) and `cli → adapters → configuration → dataprocessing` (×1).
These chains are the architecture's *intended* composition-root pattern; the contract
bans it. The author's dead `allowed_modules = cleanmast.application` line (no-op on
forbidden contracts) shows the intent was to allow the application path.

Evidence pack: `packages/cleanmast/adr/phases/ddd-s-004-composition-root-di/on-plan.md`.

## Decision

Adopt protocol-based DI with a single composition root:

1. **Protocols live in `shared/`** (precedent: `shared/timeseries/io/repository.py`).
   Domains associate by contract, never by implementation.
2. **`cleanmast/bootstrap.py` is the only composition root** — the single module that
   imports concrete cross-domain implementations and injects them into usecases.
3. **`cli.py` + `adapters/cli/` parse args and invoke** — no direct submodule imports.
4. **`cli-isolation` contract**: set `allow_indirect_imports = true` — polices direct
   imports only; the transitive reach through bootstrap is the sanctioned pattern.
5. Same wave family fixes `subdomain-isolation`'s last edge: move
   `recommend_fill_heights` orchestration from configuration to an application usecase.

## Constraints

- No DI framework; plain constructor injection + factory functions in bootstrap.
- No shims, aliases, or re-export facades for old paths (repo clean-cutover rule).
- Protocols are typed (no bare `Any`); realizations must structurally conform.
- Fitted shear values must still land in the fill-heights TOML at recommend time
  (review/override workflow preserved).

## Anti-patterns

- Protocol defined inside a subdomain but imported across contexts (drifts into a
  sideways dependency; killed the abandoned `TimeSeriesRepository` once already).
- "DI" that erases chains on paper but leaves cli.py importing usecases that import
  concrete services (contract still sees the chain).
- Widening `ignore_imports` instead of fixing the architecture.

## Validation

- `uv run lint-imports` (root) and package sweep: `cli-isolation` + `subdomain-isolation`
  KEPT, all contracts parseable.
- Golden pipeline diff (松原-gate master) byte-stable for rewired commands.
- Baseline 6/6 green per wave.

## Phase links

- Design + handoff: `phases/ddd-s-004-composition-root-di/on-plan.md`
