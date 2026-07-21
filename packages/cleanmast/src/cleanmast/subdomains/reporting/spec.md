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

## 业务说明 (Business description)

### Domain context

风资源评估报告是管道的最终产出。按 IEC 61400 标准生成多维度评估结果。
Reporting 是 vertical-slice 架构: 每个评估维度 (capability) 独立完成
compute → assemble → render 流程。

### Key concepts

9 个评估维度 (capabilities):
- **weibull**: 威布尔双参数分布拟合风速概率密度和风能密度。
- **wind_rose**: 16 扇区风向频率和风速分布。
- **turbulence**: 湍流强度 (TI) 分析，按 IEC 61400-1 分级。
- **wind_frequency**: 风速频率直方图。
- **wind_temporal**: 风速/风向日变化和月变化统计。
- **vertical_profile**: 垂直风廓线 — 风切变幂律拟合。
- **extreme_wind**: 极端风速重现期分析 (Gumbel 分布)。
- **representative_year**: 代表年选取，匹配长期气候平均值。
- **air_density**: 空气密度计算 (温度、气压、海拔校正)。

### Business constraints

- 评估结果直接影响风机选型和项目融资 — 准确性是硬约束。
- IEC 61400 标准定义了湍流类别 (A/B/C)、参考风速、极端风模型。
- 代表年 (representative year) 选取影响所有后续评估的参考基线。
