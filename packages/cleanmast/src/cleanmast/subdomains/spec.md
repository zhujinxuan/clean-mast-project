## Purpose

Bounded-context constitution for the pipeline-stage DDD structure inside `cleanmast`.

## Rules

1. Pipeline stages run left-to-right: model ← protocols ← compute ← assemble ← render ← api.
2. Each stage imports from the LEFT only; never right, never sideways.
3. Contexts import from `cleanmast.shared.*` or external packages; never from a sibling context.
4. Entities and value objects live together under `model/`; default Pydantic config is `frozen=True`.
5. Mutability is allowed only with an inline comment: `# mutable: <reason>`.
6. Keep contexts flat: no `domain/` or `application/` nesting.
7. `api.py` is the sole public interface; `__init__.py` exports only model types and api functions.
8. Use a single file (e.g. `compute.py`) when content fits one file; use a folder (e.g. `compute/`) otherwise.
9. Each capability lives under `subdomains/{capability}/` with its own 
   compute, assemble, and section files. The top-level compute/, assemble/, 
   render/ directories hold shared helpers used across capabilities.
10. Section classes in `subdomains/{capability}/section.py` may import from 
    `compute/`, `assemble/`, and `render/` helpers. This is the only case 
    where a "sideways" import (to render/) is permitted.
11. Section input types are frozen dataclasses defined in `model/`. Sections 
    with the same input kind share the same input type.
12. All section `render_ir` methods must use `render_subsection_content` 
    from `render/subsection_renderer.py`. Manual atom iteration in 
    `render_ir` is forbidden.
13. Timeseries loading (``load_timeseries``, ``TimeSeriesRepository``, and
    validation) lives in ``cleanmast.shared.timeseries.io`` — subdomains
    import timeseries data through this shared I/O layer.

## Anti-patterns

- Cross-context imports; use shared contracts instead.
- IO inside compute; keep compute pure math.
- String paths (`str(path)`); use `pathlib.Path`.
- Unfrozen model without a `# mutable: <reason>` justification.
- Infrastructure types exposed through `__init__.py`.

## When in doubt

- If a type is used by 2+ contexts → put it in `shared/`.
- If a function needs math AND file access → split it into compute + render.
- If unsure whether compute or assemble: produces DataFrame/number → compute; wraps in atoms → assemble.
