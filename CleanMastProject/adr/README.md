# CleanMast Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) that serve as guardrails for AI coding agents working on the CleanMast project. Each ADR documents a critical architectural decision with constraints that must be followed.

## ADR Index

| ADR ID | Title | Purpose | Load When |
|--------|-------|---------|-----------|
| [stack-001](stack-001-julia-tech-stack.md) | Julia Technology Stack | Defines the core Julia technology stack including Comonicon CLI, DataFrames, TOML configuration, AlgebraOfGraphics visualization, GLM, and statistics packages | Starting any Julia development, adding dependencies, making technology decisions |
| [structure-001](structure-001-julia-workspace-structure.md) | Julia Workspace Structure | Workspace pattern with root Project.toml, CleanMastProject package directory, module organization under src/ | Modifying module structure, creating new submodules, adding CLI commands |
| [types-001](types-001-julia-type-system.md) | Julia Type System Patterns | Struct field annotations, function signatures, abstract types, config loading with Parameters.jl | Defining structs, writing function signatures, type annotations, config loading |
| [data-001](data-001-dataframes-patterns.md) | DataFrames.jl Patterns | Column access with Symbols, filter/transform/select operations, joins, missing value handling | Data processing, DataFrames operations, column access, data transformation |
| [data-002](data-002-functional-programming.md) | Functional Programming Approach | Functional patterns using filter(), map(), broadcasting; pragmatic allowance for loops when needed | Writing Julia code, data transformations, building collections, iterating over data |
| [data-003](data-003-parquet-format.md) | Parquet Format for Time Series | Parquet2.jl for data storage, file-level metadata as JSON, auto-detection by extension | Reading/writing time series data, storing sensor metadata |
| [config-001](config-001-toml-configuration.md) | TOML Configuration System | TOML-based configs using Parameters.jl @with_kw structs for type-safe config loading | Adding new config types, loading configuration files, creating recommend commands |
| [cli-001](cli-001-comonicon-patterns.md) | Comonicon CLI Patterns | Comonicon.jl framework patterns with @cast for commands, @main for entry point | CLI command development, adding new commands, modifying command structure |
| [domain-001](domain-001-wind-energy-conventions.md) | Wind Energy Domain Conventions | Sensor types (WindSpeed, WindDirection), stat types, data intervals, physical constraints | Working with sensor data, accessing DataFrame columns, filtering sensors |
| [testing-001](testing-001-julia-testing-standards.md) | Julia Testing Standards | Test.jl with @testset grouping, module-based directory structure, fixtures | Writing tests, test design, test review, coverage validation |
| [docs-001](docs-001-documentation-standards.md) | Documentation Standards | Source-code constrained docs, fact-checking, Chinese for user-facing docs, minimal comments | Writing documentation, creating docs/*.md files, documenting configuration |

## How to Use These ADRs

### As a Developer

1. **Before starting work**, identify which ADRs apply to your task
2. **Read the relevant ADRs** to understand the constraints
3. **Follow the constraints** marked with MUST in each ADR
4. **Reference ADRs in code reviews** when enforcing standards

### As an AI Agent

When working on CleanMast code:

1. **Identify the task type** (see Loading Guide below)
2. **Load the relevant ADRs** by reading their content
3. **Apply the constraints** during code generation
4. **Validate outputs** against ADR requirements

## Loading Guide by Task

| Task Type | ADRs to Load |
|-----------|--------------|
| **New Julia development** | stack-001, types-001, data-002 |
| **Data processing** | data-001, data-002, domain-001 |
| **Adding CLI commands** | cli-001, structure-001, types-001 |
| **Creating configs** | config-001, types-001 |
| **Sensor data work** | domain-001, data-001 |
| **Writing tests** | testing-001, data-002 |
| **Writing documentation** | docs-001, domain-001 |
| **Adding dependencies** | stack-001 |
| **Module reorganization** | structure-001, types-001 |
| **Full feature development** | ALL ADRs |

## ADR Format

Each ADR follows this structure:

```yaml
---
id: adr-id
name: adr-name
description: Brief description of the decision
status: enforced|proposed|deprecated
tags: [tag1, tag2]
applies_when:
  - situation 1
  - situation 2
---
```

## Status Definitions

- **Enforced**: Currently active and must be followed
- **Proposed**: Under consideration, not yet mandatory
- **Deprecated**: No longer in effect, superseded by newer ADR

## Contributing

When proposing new architectural decisions:

1. Create a new ADR file following the naming convention: `{category}-{number}-{brief-name}.md`
2. Use the frontmatter format shown above
3. Include clear MUST/SHOULD/MAY constraints
4. Provide rationale for each constraint
5. Add examples of correct and incorrect usage
6. Update this README index

---

*Last updated: March 2026*
