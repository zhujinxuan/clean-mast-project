# Python Workspace Setup Guide

This guide explains the workspace structure and setup process for CleanMast.

## Prerequisites

Install [mise](https://mise.jdx.dev/) (version manager for Julia + Python):

```bash
# macOS / Linux
curl https://mise.run | sh

# Windows (PowerShell)
winget install jdx mise
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/clean-mast-project.git
cd clean-mast-project

# Install all dependencies (Julia + Python)
mise run bootstrap
```

This command runs `uv sync --all-groups --all-packages --all-extras` for Python and `Pkg.instantiate()` for Julia.

## Creating a Project

```bash
# Initialize a new project with Justfile
mise run init:experiment projects/my-windfarm

# Enter the project directory
cd projects/my-windfarm

# See available commands
just --list

# Run the full pipeline
just run-all
```

## Running Commands

### Justfile Recipes (Primary Interface)

```bash
cd projects/my-windfarm

# Full pipeline
just run-all

# Individual steps
just recommend-parse-sensors
just parse-sensors
just process-all
just process-clean
just report-timeseries
```

### Direct Python Commands (Advanced)

```bash
uv run cleanmast --help
mise run init:experiment projects/my-windfarm
uv run cleanmast recommend fill-heights projects/my-windfarm/
uv run cleanmast fill-heights projects/my-windfarm/fill-heights-reconstruct-meso.toml
uv run cleanmast report timeseries projects/my-windfarm/rep-ts-report.toml
```

### Preprocessing Tools

```bash
uv run preprocess csv-merge config.toml
uv run preprocess col-normalizer config.toml
uv run preprocess type-normalizer config.toml
uv run preprocess timestamp config.toml
```

## Running Tests

```bash
# Python tests
uv run pytest packages/cleanmast/tests/ -v
uv run pytest packages/preprocess-tools/tests/ -v

# Julia tests
julia CleanMastProject/test/runtests.jl
julia CleanMastProject/test/runtests.jl parse_sensors
```

## Development Tools

### Type Checking

```bash
uv run ty check packages/cleanmast
uv run ty check packages/preprocess-tools
```

### Linting

```bash
uv run ruff check packages/
uv run ruff format packages/
```

## Structure Overview

```
clean-mast-project/
├── mise.toml                 # mise tasks (bootstrap)
├── Project.toml              # Julia workspace
├── pyproject.toml            # Python workspace
│
├── packages/                 # Python packages
│   ├── preprocess-tools/     # Data preprocessing tools
│   └── cleanmast/            # Main analysis package
│       └── scaffold/         # Project template (Justfile)
│
├── docs/                     # Shared documentation
├── CleanMastProject/         # Julia implementation
└── projects/                 # Project directories (each with Justfile)
```

## Workspace Dependencies

If a package depends on another workspace package:

```toml
# In packages/cleanmast/pyproject.toml
[dependencies]
preprocess-tools = "*"

[tool.uv.sources]
preprocess-tools = { workspace = true }
```

## Adding New Packages

1. Create package directory under `packages/`
2. Add to `[tool.uv.workspace] members` in root `pyproject.toml`
3. Create package `pyproject.toml`
4. Add source code under `src/{package_name}/`
5. Add tests under `tests/`
6. Run `mise run bootstrap` to install

See [Migration Status](status.md) for current migration progress.
