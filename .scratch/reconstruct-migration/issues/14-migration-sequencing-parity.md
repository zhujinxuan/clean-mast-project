# 14 — Migration sequencing and Julia parity validation

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Fix the migration order into `packages/cleanmast` and the parity-validation strategy against Julia outputs.

2026-08-28 proposal (memory `core://agent/4`): train-meso (fit IR + TOML artifact) → reconstruct-meso → representative-year (dependency chain), cross-mast after; the charted unified contract may reorder this.

Decide:

1. **Sequencing**: in what order do the pieces land (contract + registry first? vertical unification before or after cross/meso?), given the charted decisions?
2. **Parity fixtures**: which real projects serve as parity fixtures vs Julia outputs; what tolerance counts as parity (exact, ε on RMSE of reconstructed series, statistical)? Julia is frozen — parity targets are fixed files.
3. **"Migration done" per subdomain**: what observable marks each piece migrated (Julia path removed from experiment configs? Python output replaces Julia artifact in projects?).
4. **Cutover mechanics**: do old JLD2 model artifacts get a one-time converter, or are fits retrained in Python and JLD2 abandoned?

## Acceptance

- [ ] Sequencing + parity strategy recorded under `## Answer`
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)
