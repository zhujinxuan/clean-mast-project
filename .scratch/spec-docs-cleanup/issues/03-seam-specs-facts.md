# 03 — Fix seam spec facts: shared, timeseries, dataprocessing, configuration

**What to build:** Correct factually wrong and duplicated boundary claims in the four non-reporting specs: `shared/spec.md`, `shared/timeseries/spec.md`, `subdomains/dataprocessing/spec.md`, `subdomains/configuration/spec.md`. Details in `.scratch/spec-docs-cleanup/findings.md`.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

shared/spec.md:

- [ ] Rewrite the admission rule to match reality: cross-context contract types (including the config IR models actually living in `timeseries/`) used by 2+ contexts; state the entry bar once (currently 3×); replace the timeseries concept glossary with a pointer to `shared/timeseries/spec.md`

shared/timeseries/spec.md:

- [ ] Fix the false routing claim: sensor-metadata TOML lives in `infrastructure/file_repository.py`, config TOML in `services/config_io.py`; both are whitelisted by the `tomli-configuration-gateway-only` contract
- [ ] Keep the protocol routing detail here; drop the helper-name enumeration from `io/validation.py`

dataprocessing/spec.md:

- [ ] State the public-API exception explicitly: this context exposes services via `services/__init__.py`, not `api.py` (parent rule 7 does not fit; no api.py exists)
- [ ] Drop the `## Code rules` wrapper → flat 5-section format
- [ ] Bound or drop the "prefer pure functions" wish (hard rule with escape hatch, or delete)

configuration/spec.md:

- [ ] Fix the tomli-gateway claim: `services/config_io.py` AND `infrastructure/file_repository.py` both import tomli, whitelisted by contract — name both or delegate to the contract
- [ ] Delete the dead `old_configuration` rule (module no longer exists)
- [ ] Drop the future-tense `meso-models/` line
- [ ] Delete the duplicated repository-access anti-pattern (owned by dataprocessing) and the duplicated shear-reuse business fact (pointer to dataprocessing)
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review. Full quotes per line in `../findings.md`.
