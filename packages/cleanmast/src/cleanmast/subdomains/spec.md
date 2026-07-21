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
14. Cross-subdomain workflows live in ``cleanmast.application.usecases``.
    A usecase may import ``configuration`` and ``dataprocessing`` in the same
    function; a subdomain never imports a sibling (enforced by the
    ``subdomain-isolation`` and ``repository-access`` import-linter
    contracts).
15. Train workflows follow one pattern: the usecase discovers input configs
    via ``ProjectConfig.discover_*_config()``, calls a dataprocessing fit
    service (e.g. ``planner.fit_all_masts``), and persists results via
    ``ProjectConfig.save_*_model()``. Fitting code never touches TOML I/O.

## Anti-patterns

- Cross-context imports; use shared contracts instead.
- A subdomain service that discovers configs, calls a sibling subdomain, and
  writes files — that is a usecase; move it to ``application/usecases/``.
- IO inside compute; keep compute pure math.
- String paths (`str(path)`); use `pathlib.Path`.
- Unfrozen model without a `# mutable: <reason>` justification.
- Infrastructure types exposed through `__init__.py`.

## When in doubt

- If a type is used by 2+ contexts → put it in `shared/`.
- If a function needs configs from one subdomain AND services from another →
  it is an application usecase, not a subdomain service.
- If a function needs math AND file access → split it into compute + render.
- If unsure whether compute or assemble: produces DataFrame/number → compute; wraps in atoms → assemble.

## 业务说明 (Business description)

### Domain context

测风塔 (meteorological mast) 风资源评估数据流经多个管道阶段:
原始传感器数据 → 清洗 → 单塔/交叉/中尺度重建 → 目标高度补全 → 风机时序 → 报告。
每个阶段消费前一阶段的产出，通过 `shared/` 中的契约类型传递。
Bounded context 对应管道阶段: `configuration` (定义处理什么)、
`dataprocessing` (执行处理)、`reporting` (生成评估报告)。

### Key concepts

- **Mast**: 测风塔，一个物理地点的多高度、多传感器安装。
- **Sensor**: 单个测量通道 (风速/风向，安装高度，统计类型)。
- **Reconstruct**: 利用参考数据源补全缺失时段或扩展低质量数据。
- **Fill heights**: 利用风切变模型将已知高度数据推算至目标高度 (如轮毂高度)。
- **Pipeline stage**: 阶段之间无直接依赖；编排由 application usecases 完成。

### Business constraints

- 数据完整性是报告可信度的前提: 缺失时段必须重建，目标高度必须补全。
- 风机轮毂高度典型值: 125 m, 140 m, 160 m — 因此 fill-heights 默认目标高度为这三个。
