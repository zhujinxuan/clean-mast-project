---
id: cli-001-comonicon-patterns
name: comonicon-patterns
description: Comonicon.jl CLI framework patterns for CleanMast command-line interface. Uses @cast for commands/modules and @main for entry point.
status: enforced
tags: [julia, cli, comonicon, commands, interface]
applies_when:
  - CLI command development
  - adding new commands
  - modifying command structure
  - help text documentation
---

# ADR-001: Comonicon CLI Patterns

## Status
**Enforced**

## Constraint (MUST)

1. **CLI commands MUST use Comonicon.@cast macro**
2. **Main entry point MUST use Comonicon.@main macro**
3. **Command modules MUST have docstrings for help text**
4. **Function commands MUST include # Arguments and # Options sections in docstrings**
5. **Command names MUST use snake_case (auto-converted to kebab-case by Comonicon)**
6. **Configuration paths MUST use positional arguments, not keyword arguments**
7. **Optional flags MUST use keyword arguments with defaults**

## Rationale (WHY)

- **Comonicon framework**: Provides automatic argument parsing, help generation, and command dispatching.
- **@cast macro**: Registers functions or modules as CLI commands with automatic option/argument handling.
- **@main macro**: Marks the module as the CLI entry point.
- **Docstring format**: Comonicon parses docstrings to generate help text with proper sections.
- **snake_case naming**: Comonicon automatically converts `function_name` to `function-name` in CLI.
- **Positional args for paths**: Configuration paths are always required and should be positional.
- **Keyword args for options**: Flags and optional values should use keyword arguments.

## Pattern (HOW)

### Main CLI Module Structure

```julia
module CleanMastCli

using Comonicon

"""
project

Project management commands
"""
Comonicon.@cast module Project
    using Comonicon
    using CleanMastProject.ParseSensors.CommandParseSensors

    """
    parse-sensors

    Process sensor data based on a TOML configuration file.

    # Arguments
    - `config_path`: Path to the parse-sensors.toml configuration file.

    # Example
    ```bash
    julia bin/CleanMast.jl project parse-sensors path/to/parse-sensors.toml
    ```
    """
    Comonicon.@cast function parse_sensors(config_path::String)
        CommandParseSensors.execute(config_path)
    end
end

"""
process

Data processing and reconstruction commands
"""
Comonicon.@cast module Process
    using Comonicon
    # ... command implementations
end

"""
CleanMast - Wind measurement data cleaning and analysis tool

A command-line tool for processing wind measurement data.
"""
Comonicon.@main

end # module CleanMastCli
```

### Simple Command Function

```julia
"""
clean

Clean data using configured rules.

# Arguments
- `config_path`: Path to process-clean.toml configuration file
"""
Comonicon.@cast function clean(config_path::String)
    ProcessCleanCommand.execute(config_path)
end
```

### Command with Options (Flags)

```julia
"""
reconstruct-meso

Recommend a reconstruct-meso.toml configuration file for the project.

# Arguments
- `dir`: Project directory containing train-meso.toml

# Options
- `--cluster-threshold <threshold>`: Overlap threshold for mast clustering (default: 0.8)
- `--threshold-period <days>`: Minimum intersection period for clustering (default: 120 days)

# Example
```bash
julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project
julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project --cluster-threshold 0.7 --threshold-period 90
```
"""
Comonicon.@cast function reconstruct_meso(
    dir::String;
    cluster_threshold::Float64=0.8,
    threshold_period::Int=120
)
    RecommendReconstructMesoCommand.execute(dir; cluster_threshold, threshold_period)
end
```

### Command with Optional Arguments

```julia
"""
analyze-reconstruct-cross

Recommend an analyze-reconstruct-cross.toml configuration file for cross-mast analysis.

# Arguments
- `dir`: Project directory containing mast data and configurations
"""
Comonicon.@cast function analyze_reconstruct_cross(dir::String)
    RecommendAnalyzeReconstructCrossCommand.execute(dir)
end
```

### Complex Command with Multiple Options

```julia
"""
steps

Execute processing steps with flexible control options.

# Arguments
- `dir`: Project directory containing configurations
- `--all`: Execute all processing steps (1-18)
- `--from`: Starting step number (1-18, default: 1 when --all is used)
- `--to`: Ending step number (1-18, default: 18 when --all is used)
- `--list`: List all available steps without executing

# Examples
```bash
julia bin/CleanMast.jl process steps --all ./projects/my-project
julia bin/CleanMast.jl process steps --from 5 --to 12 ./projects/my-project
julia bin/CleanMast.jl process steps --from 10 ./projects/my-project
julia bin/CleanMast.jl process steps --list
```
"""
Comonicon.@cast function steps(dir::String=""; all::Bool=false, from::Int=0,
                              to::Int=0, list::Bool=false)
    from_step = from == 0 ? nothing : from
    to_step = to == 0 ? nothing : to
    ProcessSteps.execute(dir, all=all, from_step=from_step, to_step=to_step, list_only=list)
end
```

### Command with Union Types for Nullable Options

```julia
"""
en

Analyze wind data for EN standard (civil engineering load calculations).

# Arguments
- `config_path`: Path to analyze-en.yaml configuration file

# Options
- `--output, -o`: Output directory for results

# Example
```bash
julia bin/CleanMast.jl analyze en path/to/analyze-en.yaml
julia bin/CleanMast.jl analyze en path/to/analyze-en.yaml --output results/
```
"""
Comonicon.@cast function en(config_path::String; output::Union{String, Nothing}=nothing)
    AnalyzeEN.execute(config_path, output)
end
```

### Module-Based Commands (Subcommands)

```julia
"""
train

Model training commands
"""
Comonicon.@cast module Train
    using Comonicon
    using CleanMastProject.TrainReconstructCross.TrainReconstructCrossCommand

    """
    reconstruct-cross

    Train cross-mast relationships and reconstruction models.

    # Arguments
    - `config_path`: Path to train-reconstruct-cross.toml configuration file
    """
    Comonicon.@cast function reconstruct_cross(config_path::String)
        TrainReconstructCrossCommand.execute(config_path)
    end
end
```

### Standalone Command Module Pattern

```julia
module ProcessSteps

using ...DataClean.ProcessCleanCommand
using ...TowerShading.CommandTowerShading
# ... more imports

export execute, list_steps

struct ProcessingStep
    number::Int
    name::String
    description::String
    execute_func::Function
    config_file::Union{String, Nothing}
    output_check::Union{String, Nothing}
    conditional::Bool
end

function execute(dir::String; all::Bool = false, from_step::Union{Int, Nothing} = nothing,
                to_step::Union{Int, Nothing} = nothing, list_only::Bool = false)
    # Implementation
end

end # module
```

## Docstring Format Standards

### Required Sections

1. **First line**: Command name (auto-converted from function name)
2. **Blank line**
3. **Description**: Brief explanation of what the command does
4. **# Arguments**: List of positional arguments with descriptions
5. **# Options**: List of keyword arguments (flags) with descriptions
6. **# Example**: Bash examples showing usage

### Optional Sections

- **# Examples**: Multiple example invocations
- **Notes**: Implementation details or requirements

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Using ArgParse or other CLI frameworks
using ArgParse  # NEVER - use Comonicon

# ❌ WRONG: Manual argument parsing
function main(args)
    config_path = args[1]  # NEVER - use @cast
end

# ❌ WRONG: Missing docstrings
@cast function my_command(path::String)  # NEVER - always include docstring
    execute(path)
end

# ❌ WRONG: Using kebab-case in function names
@cast function my-command(path::String)  # NEVER - use snake_case: my_command

# ❌ WRONG: Configuration path as keyword argument
@cast function clean(; config_path::String)  # NEVER - use positional for required paths

# ❌ WRONG: Missing type annotations
@cast function process(path)  # NEVER - always type annotate

# ❌ WRONG: Direct command implementation in CLI module
@cast function clean(config_path::String)
    # Implementation here  # NEVER - delegate to Command module
    df = CSV.read(config_path, DataFrame)
    # ... processing logic
end
```

## Phase Links

This ADR uses **phase-based documentation**. Load the appropriate phase file for your role:

| Phase | File | When to Load |
|-------|------|--------------|
| **on-plan** | [`phases/cli-001-comonicon-patterns/on-plan.md`](phases/cli-001-comonicon-patterns/on-plan.md) | Designer: CLI design and command structure |
| **review-plan** | [`phases/cli-001-comonicon-patterns/review-plan.md`](phases/cli-001-comonicon-patterns/review-plan.md) | Reviewer: Validating CLI designs |
| **code** | [`phases/cli-001-comonicon-patterns/code.md`](phases/cli-001-comonicon-patterns/code.md) | Coder: Implementing commands |
| **review-implementation** | [`phases/cli-001-comonicon-patterns/review-implementation.md`](phases/cli-001-comonicon-patterns/review-implementation.md) | Reviewer: Code review |

### Quick Compliance Check

```bash
# Validate ADR compliance - check for @cast usage
grep -rn "Comonicon.@cast" CleanMastProject/src/CleanMastCli.jl || echo "ERROR: No @cast found"
grep -rn "Comonicon.@main" CleanMastProject/src/CleanMastCli.jl || echo "ERROR: No @main found"

# Check for anti-patterns
grep -rn "using ArgParse" CleanMastProject/src/ && echo "WARNING: Found ArgParse usage"
grep -rn "@cast function.*-$" CleanMastProject/src/ && echo "WARNING: Possible kebab-case function names"
```

## References

- [CleanMastCli.jl](../src/CleanMastCli.jl) - Main CLI module with @cast and @main usage
- [ProcessSteps.jl](../src/Command/ProcessSteps.jl) - Standalone command module pattern
- Comonicon.jl documentation: https://comonicon.org/
