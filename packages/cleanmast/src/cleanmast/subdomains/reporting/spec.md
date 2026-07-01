## Purpose

Produces wind resource assessment reports from time-series data.

## Rules

1. Inherits all rules from `subdomains/spec.md`.
2. Pipeline stages run left-to-right: model ← protocols ← compute ← assemble ← render ← api.
3. Capabilities: `wind_rose`, `weibull`, `turbulence`, `wind_frequency`, `wind_temporal`, `vertical_profile`, `extreme_wind`, `representative_year`, `air_density`.
4. Imports are allowed from `cleanmast.shared.*` only; no imports from sibling contexts.
5. `api.py` is the sole public interface; `__init__.py` exports only model types and api functions.
6. Models default to Pydantic `frozen=True`; mutability needs `# mutable: <reason>`.
7. Each section defines a `from_inputs` classmethod accepting
   `list[SingleMastAnalysisInput]`. Sections extract `time_series`, `mast_name`,
   and `parameters.air_density` directly from the input object.
8. All section `render_ir` methods must use `render_subsection_content` 
   from `render/subsection_renderer.py`.
9. Extreme wind section owns its compute→assemble pipeline like all other 
    sections; pre-computed DataFrame inputs are forbidden.
10. Drift-log.md tracks design decisions diverging from assessment reference.
    Agent MUST ask user before appending. Max 30 items, ≤4 lines each.
    See drift-references/ for detailed writeups.
11. All TOML I/O MUST go through `cleanmast.subdomains.configuration.value_objects` Pydantic models.
    Never `import tomli` or `import tomli_w` directly in reporting, application, or any subdomain.
    Configuration files are loaded via Pydantic's `model_validate` in a `from_toml` classmethod.

## Anti-patterns

- Cross-capability imports; share through `reporting/model/` or `reporting/protocols/`.
- IO inside `compute/`; keep calculations pure.
- Infrastructure types exposed via `__init__.py`.
- `import tomli` or `import tomli_w` outside `configuration/value_objects/`.
- Raw dict access (`mc.get("time_range")`) from TOML — use typed model attributes.
- Stateful calculators; prefer pure functions with explicit inputs.

## When in doubt

- If a type is used by 2+ capabilities → `reporting/model/`.
- If a calculation is used by 2+ capabilities → `reporting/compute/`.
- If unsure between compute and assemble: produces DataFrame/number → compute; wraps atoms → assemble.
