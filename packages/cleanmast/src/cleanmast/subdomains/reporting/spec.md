## Purpose

Produces wind resource assessment reports from time-series data.

## Rules

1. Inherits all rules from `subdomains/spec.md`.
2. One directory per capability under `reporting/subdomains/`, each with its
   own compute, assemble, and section files. The top-level compute/,
   assemble/, render/ directories hold shared helpers used across
   capabilities. (The 业务说明 lists the current capabilities.)
3. Section classes in `reporting/subdomains/{capability}/section.py` may
   import from `compute/`, `assemble/`, and `render/` helpers. This is the
   only permitted "sideways" import (parent rule 2).
4. Section input types are frozen dataclasses defined in `model/`. Sections
   with the same input kind share the same input type.
5. All section `render_ir` methods must use `render_subsection_content`
   from `render/subsection_renderer.py`. Manual atom iteration in
   `render_ir` is forbidden.
6. Each section defines a `from_inputs` classmethod accepting
   `list[SingleMastAnalysisInput]`. Sections extract what they need directly
   from the input object (e.g. air_density reads `parameters.air_density`).
7. `renderImage()` returns `Path()` for no-image, never `None` — this
   sentinel convention applies to all atoms.
8. Extreme wind section owns its compute→assemble pipeline like all other
   sections; pre-computed DataFrame inputs are forbidden.
9. Known divergence from the assessment reference or this spec is tracked
   only as a ticket under `.scratch/` (see `docs/agents/issue-tracker.md`).
   File it when found; fix order is decided on the tracker.
10. All TOML I/O MUST go through `cleanmast.subdomains.configuration.value_objects` Pydantic models.
    Never `import tomli` or `import tomli_w` directly in reporting, application, or any subdomain.
    Configuration files are loaded via Pydantic's `model_validate` in a `from_toml` classmethod.
11. Derived fields on frozen dataclasses MAY be set via `object.__setattr__` in
    `__post_init__` (see `protocols/report_atom.py`). This is the sanctioned
    pattern, not a smell — `cached_property` does not work on frozen dataclasses.

## Anti-patterns

- Cross-capability imports; share through `reporting/model/` or `reporting/protocols/`.
- `import tomli` or `import tomli_w` outside the sanctioned gateways
  (`configuration/services/config_io.py`, `infrastructure/file_repository.py`).
- Raw dict access (`mc.get("time_range")`) from TOML — use typed model attributes.
- Bare `Any`, `# type: ignore`, `str(path)`, bare `except:` — write precise
  types, use `pathlib.Path`, catch specific exceptions.

## When in doubt

- If a type is used by 2+ capabilities → `reporting/model/`.
- If a calculation is used by 2+ capabilities → `reporting/compute/`.

## 业务说明 (Business description)

### Domain context

风资源评估报告是管道的最终产出。按 IEC 61400 标准生成多维度评估结果。
Reporting 是 vertical-slice 架构: 每个评估维度 (capability) 独立完成
compute → assemble → render 流程。

### Key concepts

9 个评估维度 (capabilities):
- **weibull**: 威布尔双参数分布拟合风速概率密度和风能密度。
- **wind_rose**: 16 扇区风向频率和风速分布。高度完全由配置 `wind_rose_heights` 驱动：
  compute 仅覆盖配置的 `wind_rose_heights`（section 将配置高度直接传入
  `calculate_wind_rose`，不做计算后过滤），atoms（表/图/叙述）渲染计算帧中的
  全部高度，不做任何渲染期高度带过滤；仅当配置高度缺失同高度 WD avg 配对时
  告警（config/data 漂移防护），未配置高度不参与计算、不告警。推荐发现规则为
  同高度 WS avg + WD avg 精确配对，band-when-available：120–160m 内有配对高度
  则取之，否则回退到全部配对高度。
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
