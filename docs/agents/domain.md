# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — does not exist yet; it is created lazily by `/grill-with-docs`. Proceed silently if absent.
- **`spec.md` standards docs** — this repo's equivalent of architecture standards. They live co-located with the code:
  - `packages/cleanmast/src/cleanmast/subdomains/spec.md` and per-context `spec.md` files
  - `packages/cleanmast/src/cleanmast/shared/spec.md`
  - `packages/cleanmast/src/cleanmast/application/spec.md`

  Read the `spec.md` of any context you are about to work in. When a matt skill says "respect any ADRs in the area", read these spec.md files instead — this repo has no live ADRs.
- **Historical ADRs** — archived read-only under `packages/cleanmast/adr/archived/`. Background only; do not treat as current law.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md` (once it exists) and in AGENTS.md's Terminology section ("Mast", "Sensor", "Experiment"). Don't drift to synonyms.

## Flag standards conflicts

If your output contradicts an existing `spec.md` standards doc, surface it explicitly rather than silently overriding. If the divergence is deliberate, file a ticket under `.scratch/` (see `issue-tracker.md` — drift is a ticket, not a log).
