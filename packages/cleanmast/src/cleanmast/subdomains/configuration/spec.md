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

## Anti-patterns

- **Never import `old_configuration` from outside the configuration subdomain**. The old module is deleted. All imports must target `cleanmast.subdomains.configuration`.
- **`tomli` and `tomli_w` are imported ONLY in `services/config_io.py`.** `load_config` and `save_config` are the exclusive TOML I/O surface. Enforced by the `tomli-configuration-gateway-only` import-linter contract.
- **Never add `_filename` as a class attribute on Pydantic models**. Filename-to-model mapping belongs exclusively in `ProjectConfig._FILENAMES`.

## When in doubt

- To consume a config in an execute command: `load_config(ModelType, config_path)`.
- To write a config: `save_config(model, path)`.
- Do not add a `discover_*` method to ProjectConfig unless the config must be discovered by convention (recommend/analyze series).
- If a new TOML file needs reading in a project directory, add a model + `_FILENAMES` entry + `discover_*` method rather than inline loading.
- If a config is optional, return `None` from the discover method; if required, let the caller raise `FileNotFoundError`.
- If a model is shared between two TOML files with different semantics (e.g. meso vs rep-year), create separate marker subclasses rather than a single model with a context field.
