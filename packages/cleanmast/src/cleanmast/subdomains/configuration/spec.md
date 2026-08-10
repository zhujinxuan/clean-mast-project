## Purpose

Centralized configuration discovery and management for wind energy project directories. The configuration subdomain is the single source of truth for locating, parsing, and validating TOML configuration files.

## Rules

- **Config models live in `model/` and are Pydantic `BaseModel` subclasses**. Every config model imported from the configuration subdomain must be defined in `configuration/model/` and subclass `pydantic.BaseModel`. Models are pure data schemas without filesystem awareness.
- **`ProjectConfig` is the single entry point for config discovery**. Consumers never construct `project_dir / "name.toml"` or call `tomli.load` directly. All TOML I/O is encapsulated in `ProjectConfig` methods.
- **New config types must update three locations**: (1) a new model file in `model/`, (2) a `_FILENAMES` entry in `ProjectConfig._FILENAMES`, (3) a corresponding `discover_*_config()` method on `ProjectConfig`.
- **Recommend usecases take `ProjectConfig`, never do their own TOML I/O**. A recommend function's first parameter is `ProjectConfig`. It calls `project_config.discover_*_config()` methods and receives `DiscoveredConfig[T] | None`.
- **Execute usecases take an explicit `config_path` and parse that exact file** via `load_config(ModelType, config_path)`. They MUST NOT call `ProjectConfig.discover_*_config()`.
- **`DiscoveredConfig[T]` wraps all loaded/generated configs**. A config is either `None` (file did not exist) or `DiscoveredConfig[T]` (parsed successfully). Malformed TOML propagates as `TOMLDecodeError` or `ValidationError` — never silently swallowed.
- **Missing configs return `None` from discovery methods**. The caller (recommend function) decides whether a missing config is an error. Required configs should trigger `raise FileNotFoundError` based on the `None` return.
- **Recommend functions return `DiscoveredConfig[T]` without writing to disk**. Writing is delegated to CLI adapters via `DiscoveredConfig.write_to(project_dir)`.
- **Trained model files live under `{domain}-models/{mast}/{strategy}/` subdirectories**, one TOML per mast × strategy × variable (e.g. `fill-models/M5057/remove-top-layer/ws-fit.toml`). Subdirectory discovery uses `discover_*_models()` (walks two levels: mast, then strategy; inner key `"{strategy}/{variable}"`); root-level single-file discovery uses `discover_*_config()` + `_FILENAMES`.
- **Trained model types live in `model/` alongside config models** (e.g. `fill_height_fit_result.py`). They are loaded and persisted through the same `config_io` gateway as configs.
- **`save_*_model()` methods own the model directory layout**. Consumers never construct `{domain}-models/` paths themselves; the save method returns the written path and updates the discovery cache.
- **`ProjectConfig` discovers, caches, and persists — it never computes**. Model fitting lives in `dataprocessing`; the application usecase calls the fit service and hands results to `save_*_model()`.

## Anti-patterns

- All imports must target `cleanmast.subdomains.configuration`.
- **`tomli` and `tomli_w` are imported only in the two sanctioned gateways**:
  `services/config_io.py` (project config) and
  `infrastructure/file_repository.py` (sensor metadata). `load_config` and
  `save_config` are the TOML I/O surface. Enforced by the
  `tomli-configuration-gateway-only` import-linter contract.
- **Never add `_filename` as a class attribute on Pydantic models**. Filename-to-model mapping belongs exclusively in `ProjectConfig._FILENAMES`.

## When in doubt

- To consume a config in an execute command: `load_config(ModelType, config_path)`.
- To write a config: `save_config(model, path)`.
- Do not add a `discover_*` method to ProjectConfig unless the config must be discovered by convention (recommend/analyze series).
- If a new TOML file needs reading in a project directory, add a model + `_FILENAMES` entry + `discover_*` method rather than inline loading.
- If a config is optional, return `None` from the discover method; if required, let the caller raise `FileNotFoundError`.
- If a model is shared between two TOML files with different semantics (e.g. meso vs rep-year), create separate marker subclasses rather than a single model with a context field.
- If a TOML is one-per-project, use `discover_*_config()`; if it is one-per-mast/strategy under a subdirectory, use `discover_*_models()`.

## 业务说明 (Business description)

### Domain context

项目配置是风资源评估管道的"总控": 定义哪些测风塔、用什么模型、
输出到哪里。配置本身不执行计算 — 它描述意图。

### Key concepts

- **reconstruct-meso.toml**: 定义中尺度重建的输入测风塔、模型规格、输出目标。
  是 fill-heights 和 wt-timeseries 等下游步骤的必要前提。
- **fill-heights-reconstruct-meso.toml**: 描述每个测风塔的目标补全高度及策略。
- **train vs recommend**: `recommend` 从项目约定和现有数据生成配置文件；
  `train` 从数据学习参数 (如风切变指数 shear, 风向变化率 deg_diff_per_m)
  并持久化为模型文件。两者互补: train 产出模型，recommend 消费模型生成配置。
- **fill-models/{mast}/{strategy}/*.toml**: 训练好的补全模型参数。
  风切变指数和风向变化率的站点物理属性依据见 dataprocessing/spec.md。

### Business constraints

- 推荐配置必须可审查/可覆盖: `recommend` 生成的是预测，人工可通过
  `just-override/` 调整。
- 配置类型与文件名一对一映射 (`_FILENAMES`)，不允许歧义。
