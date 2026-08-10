## Purpose

Application usecases orchestrate: load data via repository protocol, invoke domain
services, persist results. They are the boundary between infrastructure (I/O)
and domain (pure computation).

## Rules

- Usecases accept `TimeSeriesRepository` protocol as a parameter, injected by
  `cleanmast.bootstrap`; never construct concrete repos.
- Usecases load `TimeSeriesData` via `repo.load()`, then pass `TimeSeriesData`
  to domain functions — the boundary rule itself is owned by
  `dataprocessing/spec.md`.
- One mast at a time: usecases loop, load per mast, call domain per mast.
- Config-driven usecases never do their own TOML I/O (see
  `configuration/spec.md` for the full contract): recommend flows take
  `ProjectConfig` and call `discover_*_config()`; execute flows take an
  explicit `config_path` and parse via `load_config()`; trained models persist
  via `ProjectConfig.save_*_model()`.
- Train workflows follow one pattern: the usecase discovers input configs via
  `ProjectConfig.discover_*_config()`, loads each mast's timeseries via the
  injected `TimeSeriesRepository`, calls a dataprocessing fit service (e.g.
  `planner.fit_one_mast`), and persists results via
  `ProjectConfig.save_*_model()`. Fitting code never touches I/O.

## Anti-patterns

- `from cleanmast.infrastructure.file_repository import FileTimeSeriesRepository`
  inside an application usecase.
- Passing `TimeSeriesSource` across the boundary into dataprocessing.
- Config discovery or TOML parsing hand-rolled in a usecase body — use
  `ProjectConfig` / `load_config()`.

## When in doubt

- If a function loads data → it belongs in application, not dataprocessing.

## 业务说明 (Business description)

### Domain context

application 层是管道的编排者: 把 configuration (意图) 、dataprocessing (计算)、
infrastructure (持久化) 组合成完整工作流。五个 usecase 对应管道阶段:
reconstruct → fill-heights (recommend/train/execute) → wt-timeseries →
generate_report (最终评估报告)。

### Key concepts

- **recommend / train / execute 三态**: recommend 从项目约定生成配置;
  train 从数据学习参数并持久化为模型文件; execute 按指定配置执行。
- **编排不计算**: usecase 只做加载、调用、保存 — 所有数学在 dataprocessing,
  所有 TOML 细节在 configuration。
