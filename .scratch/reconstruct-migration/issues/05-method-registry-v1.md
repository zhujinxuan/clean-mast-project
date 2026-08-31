# 05 — Method registry v1

**Type:** grilling

**Status:** ready-for-human

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

## Acceptance

- [ ] Registry design + v1 method list recorded under `## Answer`
- [ ] Method id scheme documented in CONTEXT.md
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)
