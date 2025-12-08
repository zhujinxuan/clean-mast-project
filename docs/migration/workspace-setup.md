# Python Workspace Setup Guide

This guide explains the Python workspace structure created for the CleanMast migration.

## Structure Overview

```
clean-mast-project/
├── Project.toml               # Julia workspace (coexists)
├── pyproject.toml             # Python workspace (new)
│
├── packages/                  # Python packages
│   ├── preprocess-tools/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/preprocess_tools/
│   │   ├── tests/
│   │   └── docs/
│   └── cleanmast/
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/cleanmast/
│       ├── tests/
│       └── docs/
│
├── docs/                      # Shared documentation
│   ├── README.md              # Documentation hub
│   ├── migration/             # Migration guides
│   └── python/                # Python-specific docs
│
├── CleanMastProject/          # Julia implementation (unchanged)
└── .venv/                     # Python virtual environment (auto-generated)
```

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync

# Install packages in editable mode
uv pip install -e packages/cleanmast -e packages/preprocess-tools
```

## Running Commands

### CleanMast

```bash
# Show help
uv run cleanmast --help

# Run commands (not yet implemented)
uv run cleanmast parse-sensors --config config.toml
```

### Preprocess Tools

```bash
# Currently using separate script names
uv run preprocess-csv-merge config.toml
uv run preprocess-type-normalizer config.toml
uv run preprocess-col-normalizer config.toml
uv run preprocess-timestamp config.toml

# Future: unified CLI (see todos)
uv run preprocess csv-merge config.toml
```

## Running Tests

```bash
# Run tests for specific package
uv run pytest packages/cleanmast/tests/ -v
uv run pytest packages/preprocess-tools/tests/ -v

# Run all tests (currently has import issues - use per-package)
# TODO: Fix pytest discovery for multiple packages
```

## Development Tools

### Type Checking

```bash
# Using pyright
uv run pyright packages/cleanmast
uv run pyright packages/preprocess-tools

# Using mypy
uv run mypy packages/cleanmast/src
uv run mypy packages/preprocess-tools/src
```

### Linting

```bash
# Using ruff
uv run ruff check packages/
uv run ruff format packages/
```

## Package Structure

### preprocess-tools

**Status**: ✅ Ready to use (migrated from `py-preprocess-tools`)

Contains preprocessing utilities:
- CSV merging with duplicate detection
- Encoding conversion
- Column name normalization (NRG, Lidar formats)
- Timestamp normalization
- Type conversion

### cleanmast

**Status**: 🚧 Scaffold created, features pending

Will contain the main CleanMast functionality:
- Sensor parsing
- Data cleaning
- Reconstruction algorithms
- Analysis modules
- Report generation

## Configuration Files

### Root `pyproject.toml`

Defines the workspace and shared dev dependencies:
- pytest, pytest-cov
- ruff (linting)
- mypy, pyright (type checking)

### Package `pyproject.toml`

Each package has its own:
- Dependencies
- Entry points (CLI scripts)
- Build configuration
- Optional dependencies (e.g., `[analysis]`, `[visualization]`)

## Adding New Packages

1. Create package directory under `packages/`
2. Add to `[tool.uv.workspace] members` in root `pyproject.toml`
3. Create package `pyproject.toml`
4. Add source code under `src/{package_name}/`
5. Add tests under `tests/`
6. Install in editable mode: `uv pip install -e packages/{package_name}`

## Workspace Dependencies

If a package depends on another workspace package:

```toml
# In packages/cleanmast/pyproject.toml
[dependencies]
preprocess-tools = "*"  # Version doesn't matter for workspace deps

[tool.uv.sources]
preprocess-tools = { workspace = true }
```

## Known Issues

1. **pytest discovery**: Running `pytest` at root has import conflicts
   - **Workaround**: Run tests per-package
   - **TODO**: Configure pytest namespace packages properly

2. **CLI naming**: preprocess-tools uses separate scripts
   - **TODO**: Migrate to unified CLI with subcommands

## Next Steps

See [Migration Status](status.md) for what needs to be implemented next.
