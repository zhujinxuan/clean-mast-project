<!-- NOTE: CLAUDE.md and AGENTS.md must be kept in sync! -->

# CleanMast Project Guide for Claude Code

CleanMast is a comprehensive toolkit for processing wind energy meteorological tower data. This guide provides essential context and quick references. For detailed constraints and patterns, see the Architecture Decision Records (ADRs).

## Project Overview

CleanMast processes wind measurement data through a multi-stage pipeline:
- **Data Parsing**: Flexible sensor data parsing with configurable column mappings
- **Data Cleaning**: Range validation, layer difference checks, icing detection, tower shading
- **Data Reconstruction**: Single-mast correlation, mesoscale data integration, representative year calibration
- **Analysis & Reporting**: Wind resource assessment, EN standard compliance, quality reports

### Key Technologies
- **CLI Framework**: Comonicon.jl for modular command structure
- **Data Processing**: DataFrames.jl, DataFramesMeta.jl, CSV.jl
- **Configuration**: TOML-based configuration system
- **Visualization**: AlgebraOfGraphics.jl (preferred), CairoMakie.jl
- **Statistical Modeling**: GLM.jl, Distributions.jl, StatsBase.jl

## Architecture Decision Records (ADRs)

This project uses ADRs to document and enforce architectural constraints. When working on code, consult the relevant ADR for detailed guidance.

### Available ADRs

| ADR | Topic | Description |
|-----|-------|-------------|
| **@adr/stack-001** | Julia Tech Stack | Required packages and versions |
| **@adr/structure-001** | Workspace Structure | Module organization and include patterns |
| **@adr/types-001** | Type System Patterns | Struct definitions and function signatures |
| **@adr/data-001** | DataFrames Patterns | Column access, filtering, transforms |
| **@adr/data-002** | Functional Programming | Filter, map, broadcasting patterns |
| **@adr/domain-001** | Wind Energy Conventions | Sensor types, intervals, physical constraints |
| **@adr/config-001** | TOML Configuration | Config loading with Parameters.jl |
| **@adr/cli-001** | Comonicon CLI Patterns | Command structure and docstrings |
| **@adr/testing-001** | Testing Standards | Test organization and patterns |
| **@adr/docs-001** | Documentation Standards | Writing style and fact-checking |

### ADR Quick Reference

```
@adr/stack-001         → Technology choices and package versions
@adr/structure-001     → Module organization and directory structure
@adr/types-001         → Type annotations, struct definitions
@adr/data-001          → DataFrames operations (Symbols, filter, transform)
@adr/data-002          → Functional programming patterns
@adr/domain-001        → Wind sensor conventions, NEVER pattern match column names
@adr/config-001        → TOML config loading with @with_kw
@adr/cli-001           → Comonicon @cast and @main patterns
@adr/testing-001       → Test file organization and @testset
@adr/docs-001          → Documentation writing standards
```

## Architecture Overview

```
CleanMastProject/
├── src/
│   ├── Types/                     # Core type definitions and configurations
│   ├── ParseSensors/             # Data parsing and column mapping
│   ├── DataClean/                # Data cleaning rules and validation
│   ├── ReconstructSingleMast/    # Single-mast data reconstruction
│   ├── ReconstructMeso/          # Mesoscale data reconstruction
│   ├── ReconstructCross/         # Cross-mast reconstruction (in development)
│   ├── AnalyzeTimeSeries/        # Wind resource analysis
│   ├── AnalyzeEN/                # EN standard compliance analysis
│   ├── RepresentativeYear/       # Long-term calibration
│   ├── TowerShading/             # Tower shadow detection/correction
│   ├── Command/                  # CLI command implementations
│   └── CleanMastUtils.jl        # Shared utilities
├── test/                         # Test suite
├── docs/                         # Documentation
└── Project.toml                  # Package dependencies
```

## Workspace Structure

The project uses Julia's workspace feature for better organization:

**Root Structure:**
```
clean-mast-project/
├── Project.toml           # Workspace configuration: [workspace] members = ["CleanMastProject"]
├── bin/
│   └── CleanMast.jl      # Entry point that activates CleanMastProject environment
└── CleanMastProject/     # The actual Julia package
    ├── Project.toml       # Package dependencies and metadata
    ├── src/               # Source code
    ├── test/              # Test suite
    └── docs/              # Documentation
```

**Key Points:**
- The root `Project.toml` defines the workspace with `CleanMastProject` as a member
- All source code, tests, and documentation live under `CleanMastProject/`
- `bin/CleanMast.jl` activates the `CleanMastProject` environment before loading the package
- When running tests, use: `julia CleanMastProject/test/runtests.jl [test_set]`
- All file paths in code should be relative to the package root (`CleanMastProject/`)

## File Path Convention (CRITICAL)

**Claude Code File Modification Bug Workaround**: Always use complete absolute Windows paths with drive letters and backslashes for ALL file operations. This applies to Read, Write, Edit, and any other file tools.

**Correct format**: `C:\Users\zhu_j\workspace\developing\clean-mast-project\file.txt`
**Incorrect formats**:
- Relative paths: `projects/file.txt`
- Forward slashes: `C:/Users/...`
- Mixed separators

Apply this rule consistently throughout the session, not just when encountering errors.

**IMPORTANT: Shell Commands with Paths**
When using paths in Bash/shell commands with double quotes, you MUST:
- Use forward slashes `/` OR
- Escape backslashes with `\\`

**Examples:**
```bash
# CORRECT - Forward slashes
ls -la "/c/Users/zhu_j/workspace/test"
ls -la "C:/Users/zhu_j/workspace/test"

# CORRECT - Escaped backslashes
ls -la "C:\\Users\\zhu_j\\workspace\\test"

# WRONG - Single backslashes in quotes
ls -la "C:\Users\zhu_j\workspace\test"  # ERROR: \U, \w, \t are escape sequences
```

**Rule of thumb:**
- **File tool parameters** (Read, Write, Edit): Use Windows backslashes `C:\path\to\file`
- **Shell command strings**: Use forward slashes `"C:/path/to/file"` or escaped backslashes `"C:\\path\\to\\file"`

## Quick Command Reference

### Running Tests

```bash
# Run all tests
julia CleanMastProject/test/runtests.jl

# Run specific test sets
julia CleanMastProject/test/runtests.jl parse_sensors data-clean

# List available test sets
julia CleanMastProject/test/runtests.jl --help
```

For detailed testing standards, see **@adr/testing-001**.

### Python Type Checking (for Python modules)

```bash
# Run type check
uv run ty check packages/cleanmast

# Check specific module
uv run ty check packages/cleanmast/src/cleanmast/fill_heights
```

### Polars Best Practices (Python)

When planning or implementing data analysis with Polars, load the skill first:

```
skill(name="polars")
```

The skill covers expression-first patterns, anti-patterns to avoid, and quick reference for common operations.

## AI Agent Guidelines

### Code Generation Priorities
1. **Domain Accuracy**: Understand meteorological constraints and wind energy physics
2. **Error Prevention**: Validate inputs and handle edge cases explicitly
3. **Performance**: Consider data size and processing efficiency
4. **Maintainability**: Follow established patterns and conventions

### Critical Rules (See ADRs for Details)

| Rule | ADR Reference |
|------|---------------|
| Use Symbols for DataFrame columns | @adr/data-001 |
| Never pattern-match column names | @adr/domain-001 |
| Use SensorColumn metadata for column access | @adr/domain-001 |
| Functional style over imperative loops | @adr/data-002 |
| Type annotations on all functions | @adr/types-001 |
| Use `@with_kw` for config structs | @adr/config-001 |
| Use Comonicon `@cast` for CLI | @adr/cli-001 |

### Testing Requirements
- Always run relevant tests after code changes: `julia CleanMastProject/test/runtests.jl [test_sets]`
- Prefer existing test patterns over creating new test structure
- Include both positive and negative test cases

### User Interaction
- Respect user modifications to generated code
- Never reintroduce deleted functions without explicit request
- Ask for clarification when user changes seem problematic
- Preserve user's configuration choices and workflow patterns

### Comments Policy
- **Minimal Comments**: Only include comments where truly necessary
- **Self-Documenting Code**: Prefer clear function/variable names
- **Docstrings**: Use for public API functions, avoid for obvious implementations
- **Domain Context**: Comment on meteorological assumptions or physical constraints

## Report Atom Pattern

When working with report generation code:

**Architecture:**
- `ReportAtom` is an abstract base class (ABC)
- Each atom implements 3 methods: `renderTable()`, `renderImage()`, `renderSummary()`
- DataFrame + Schema + Meta = Atom instance
- Use `Atom.create(schema, df, meta)` factory method

**Data Format:**
- Tables use **pivoted format**: Months/Sectors as rows, Heights as columns
- Charts use **Altair** with `.to_pandas()` conversion (required!)
- Wind roses use `mark_arc()` (not `mark_line`)
- All text in **Chinese** (月份, 外推, 风速, etc.)

**Table Column Order:**
```
[月份/风向], [10m], [50m], ..., [125m 外推], [140m 外推], [160m 外推]
```

**Typst Syntax:**
- Cells separated by **commas**: `[1], [value], [value]`
- Rows end with **trailing comma**: `[1], [value], [value],`
- Use `get_height_display_name()` for height formatting

**Testing:**
- Mock DataFrames in tests
- Test render methods return correct Typst syntax
- Skip actual compilation in unit tests (`compile_pdf=False`)

**Example Atom Structure:**
```python
@dataclass
class SingleMastMonthlyWindAtom(ReportAtom[MonthlyWindSchema, SingleMastMeta]):
    @override
    def renderTable(self) -> str:
        # Return Typst table markup

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        # Generate PNG via Altair

    @override
    def renderSummary(self) -> str:
        # Return Chinese text summary
```

---

*For detailed constraints and patterns, always consult the relevant ADR.*
