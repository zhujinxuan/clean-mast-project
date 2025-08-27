# CleanMast Project - Implementation Patterns Guide

## 📋 How to Use This File

### Purpose
This document contains **project-wide patterns and conventions** that apply to ALL features in CleanMast. It serves as a reference for maintaining consistency across different branches, features, and developers.

### When to Reference This File
- 🆕 **Implementing a new feature**: Use as a template for structure and conventions
- 🔧 **Modifying existing features**: Ensure changes follow established patterns
- 👀 **Code reviews**: Verify implementations follow project standards
- 📚 **Onboarding**: Learn the project's architectural patterns

### Example Usage with Claude/Cursor
```
@cursor_PROJECT.md

I'm implementing a new feature for [purpose]. Please help me:
1. Set up the proper module structure
2. Follow the naming conventions
3. Implement the standard workflow pattern
```

## ⚠️ How to Maintain This File

### What BELONGS in This File ✅
1. **General patterns** that apply to multiple features
2. **Naming conventions** used project-wide
3. **Structural patterns** for modules, types, and files
4. **Workflow patterns** that features commonly follow
5. **Integration guidelines** for CLI, types, etc.
6. **Code style rules** that ensure consistency

### What DOES NOT Belong ❌
1. **Feature-specific logic** (e.g., "wind speed correlation thresholds")
2. **Implementation details** of a particular feature
3. **Specific algorithms** or business rules
4. **Feature-specific configuration examples** with actual values
5. **Branch-specific temporary patterns**

### Before Adding Content, Ask Yourself:
- ❓ "Would this pattern apply to at least 3 different features?"
- ❓ "Is this a convention or a specific implementation?"
- ❓ "Am I documenting a pattern or explaining how something works?"
- ❓ "Could another developer use this pattern for a completely different feature?"

### Examples of Good vs Bad Additions

#### ✅ GOOD - General Pattern:
```markdown
### Function Naming Patterns
- `analyze_*` - Functions that calculate statistics or analyze data
- `train_*` - Functions that train models
```

#### ❌ BAD - Feature-Specific:
```markdown
### Cross-Mast Analysis Functions
- `analyze_windspeed_correlations` - Calculates correlations above 120m
- `train_cross_mast_model` - Trains with 0.7 correlation threshold
```

#### ✅ GOOD - Structure Pattern:
```markdown
### Analysis Output Structure
./feature-output/
├── results.toml       # Machine-readable results
└── report.html        # Human-readable report
```

#### ❌ BAD - Specific Implementation:
```markdown
### Cross-Mast Output Files
./analyze-reconstruct-cross/
├── high_elevation_windspeed_correlation = 0.85
└── winddirection_std = 8.3
```

### Update Checklist
Before updating this file:
- [ ] Is this a pattern, not an implementation?
- [ ] Does it apply to multiple features?
- [ ] Am I using generic names, not feature-specific ones?
- [ ] Have I removed all feature-specific values/thresholds?
- [ ] Would this make sense to someone working on a different feature?

### Creating Feature-Specific Documentation
If you have feature-specific patterns or details:
1. Create a separate file: `feature-plans/FEATURE_NAME.md`
2. Reference this file for general patterns
3. Document feature-specific details in the feature file
4. Keep the separation clear

---

## Project Structure and Organization Patterns

## Module Organization Pattern

### Feature-Based Module Structure
Every feature should be a self-contained module following this structure:

```julia
module FeatureName
  include("./FeatureName/Core.jl")                          # Core functionality
  include("./FeatureName/CommandFeatureName.jl")           # Main processing command
  include("./FeatureName/RecommendFeatureNameCommand.jl")  # Config generation command
  export CommandFeatureName, RecommendFeatureNameCommand, Core
end
export FeatureName
```

**Example:** See how `TowerShading`, `TrainMeso`, `ReconstructMeso` modules are organized.

### Command Placement Rule
**ALWAYS place commands within their feature module directory**, not in the central `Command/` directory:
- ✅ `FeatureName/CommandFeatureName.jl`
- ✅ `FeatureName/RecommendFeatureNameCommand.jl`
- ❌ `Command/FeatureName.jl`

## Type Organization

All types must be centralized in the `Types/` module following these patterns:

### ⚠️ CRITICAL: Module vs Struct Naming Conflicts

**NEVER use the same name for a module and its main struct**. This creates naming conflicts in Julia.

❌ **WRONG:**
```julia
module AnalyzeReconstructCrossConfiguration
struct AnalyzeReconstructCrossConfiguration  # CONFLICT!
    # fields
end
end
```

✅ **CORRECT:**
```julia
module AnalyzeReconstructCrossConfig  # Different from struct name
struct AnalyzeReconstructCrossConfiguration  # Main struct
    # fields
end
end
```

### Configuration Types
```julia
# Location: Types/FeatureNameConfig.jl (note: Config, not Configuration)
module FeatureNameConfig
struct FeatureNameConfiguration
    # Configuration fields
end
end
```

### Model/Data Types
```julia
# Location: Types/FeatureModels.jl (note: plural Models)
module FeatureModels
struct FeatureModel
    # Data model fields
end
end
```

### Complex Type Hierarchies
For features with multiple related types, create nested modules:
```
Types/
├── FeatureModel/
│   ├── SubType1.jl
│   └── SubType2.jl
```

**Example:** `Types/DirectionReferenceModel/`, `Types/SpeedReferenceModel/`

### Required Type Methods

**ALL types must implement serialization methods:**
```julia
import ..Utils: from_dict, to_dict

# Required for every struct
function from_dict(::Type{YourStruct}, dict::Dict{String, Any})::YourStruct
    # Implementation
end

function to_dict(obj::YourStruct)::Dict{String, Any}
    # Implementation  
end
```

**Purpose:** Enables TOML configuration loading/saving and data persistence across the system.

## Three-Command Workflow Pattern

Most analysis/reconstruction features follow this standardized workflow:

### 1. Recommend Command
- **Purpose:** Generate simple configuration from existing data
- **Naming:** `recommend feature-name`
- **File:** `FeatureName/RecommendFeatureNameCommand.jl`
- **Function:** Scans project directory and creates initial config

### 2. Process/Analyze Command
- **Purpose:** Perform main processing, analysis, or training
- **Naming:** `process feature-name` or `analyze feature-name`
- **File:** `FeatureName/CommandFeatureName.jl`
- **Function:** Executes core functionality using config

### 3. Intelligent Recommend Command
- **Purpose:** Generate optimized configuration based on analysis results
- **Naming:** `recommend next-step`
- **File:** `NextFeature/RecommendNextFeatureCommand.jl`
- **Function:** Reads analysis outputs and creates intelligent config

**Workflow Example:**
```bash
julia bin/CleanMast.jl recommend train-meso ./project
julia bin/CleanMast.jl process train-meso ./project/train-meso.toml
julia bin/CleanMast.jl recommend reconstruct-meso ./project
```

## Configuration Patterns

### Simple Input Configuration
For initial recommend commands:
```toml
[[data_sources]]
name = "Source1"
input.data = "./path/to/data.csv"
input.sensors = "./path/to/sensors.yaml"

[settings]
output_dir = "./output-directory"
```

### Complex Generated Configuration
For intelligent recommend commands:
```toml
[[targets]]
name = "Target1"
input.data = "./input/data.csv"
input.sensors = "./input/sensors.yaml"
output.data = "./output/data.csv"
output.sensors = "./output/sensors.yaml"

[[targets.models]]
# Model references or parameters
model_path = "./models/trained_model.jld2"
parameters = { threshold = 0.7 }
```

## Code Style and Naming Conventions

### Function Naming Patterns
- `analyze_*` - Functions that calculate statistics or analyze data
- `train_*` - Functions that train models
- `process_*` - Functions that transform or process data
- `get_best_*` - Functions that select optimal values
- `create_*` - Functions that construct new objects
- `save_*` - Functions that persist data to disk
- `load_*` - Functions that read data from disk
- `validate_*` - Functions that check data integrity

### Struct Naming Patterns
- `*Configuration` - Configuration types for commands
- `*Model` - Model types (especially those implementing AbstractMastReferenceModel)
- `*Pair` - Types representing relationships between two entities
- `*Result` - Types containing analysis or processing results
- `*Settings` - Types containing parameters or options

### File Naming

#### Commands
- `CommandFeatureName.jl`, `RecommendFeatureNameCommand.jl`

#### Core Logic
- `Core.jl`, `Analysis.jl`, `Training.jl`

#### Utilities
- `Utils.jl`, `Helpers.jl`

#### Types Directory Naming Conventions

**Configuration Files:**
- Pattern: `***Config.jl` (not `***Configuration.jl`)
- Example: `AnalyzeReconstructCrossConfig.jl`
- Reason: Avoids module/struct naming conflicts

**Model Files:**
- Pattern: `***Models.jl` (plural Models)
- Example: `CrossMastSpeedModels.jl`, `CrossMastDirectionModels.jl`
- Reason: Files typically contain multiple related model types

**Analysis Result Files:**
- Pattern: `***Results.jl` or `***AnalysisResults.jl`
- Example: `CrossMastAnalysisResults.jl`
- Reason: Contains multiple result struct types

#### Examples from CleanMast Project
```
Types/
├── AnalyzeReconstructCrossConfig.jl     # Configuration types
├── CrossMastSpeedModels.jl              # Speed model types  
├── CrossMastDirectionModels.jl          # Direction model types
├── CrossMastAnalysisResults.jl          # Analysis result types
├── ProcessCleanConfig.jl                # Process configuration
├── ReconstructMesoConfig.jl             # Reconstruction configuration
└── SpeedReferenceModel/                 # Complex model hierarchy
    └── SectorizedRegression.jl
```

## Module Integration

### Adding to CleanMastProject.jl
```julia
module NewFeature
  include("./NewFeature/Core.jl")
  include("./NewFeature/Analysis.jl")  # Additional components
  include("./NewFeature/CommandNewFeature.jl")
  include("./NewFeature/RecommendNewFeatureCommand.jl")
  export CommandNewFeature, RecommendNewFeatureCommand, Core, Analysis
end
export NewFeature
```

### Order of Includes
1. Core functionality files first
2. Analysis/processing components
3. Command files last
4. Export all public interfaces

## Output Structure Standards

### Analysis/Processing Output
```
./feature-output/
├── results.toml           # Machine-readable results for downstream commands
├── report.html           # Human-readable report
├── models/               # Trained models or processed data
│   └── model_files.jld2
└── visualizations/       # Charts, plots, or other visuals
    └── chart_files.png
```

### Key Files
- **results.toml**: Machine-readable summary for intelligent recommendations
- **report.html**: Comprehensive human-readable analysis
- **models/**: Directory for any generated models or large data files

## CLI Integration

### Registering Commands
In `CleanMastCli.jl`, add entries following this pattern:
```julia
"command-name feature-name" => Module.CommandModule.execute,
"recommend feature-name" => Module.RecommendCommandModule.execute,
```

### Command Naming Convention
- Use kebab-case for multi-word commands
- Start with verb (process, analyze, recommend, etc.)
- Be consistent with existing commands

## General Design Principles

### 1. Feature Cohesion
Keep all related code within the feature module directory. This improves:
- Code organization
- Maintainability
- Feature independence

### 2. Data-Driven Decisions
- Use configuration files for all inputs
- Generate intelligent recommendations based on analysis results
- Store intermediate results for traceability

### 3. Consistent Interfaces
- Follow established function signatures
- Use existing types where applicable
- Implement standard interfaces (like AbstractMastReferenceModel)

### 4. Progressive Workflow
- Simple → Complex configurations
- Analysis → Recommendations
- Each step builds on previous results

### 5. Extensibility
- Design for future additions
- Use modular components
- Avoid hard-coding assumptions

## Implementation Checklist

When implementing a new feature:

- [ ] Create feature directory under `src/`
- [ ] Implement core functionality in `Core.jl`
- [ ] Create configuration type in `Types/` using `***Config.jl` naming
- [ ] ⚠️ **CRITICAL:** Ensure module name ≠ struct name (avoid naming conflicts)
- [ ] Implement `from_dict` and `to_dict` for all custom types
- [ ] Implement main command in feature directory
- [ ] Implement recommend command(s)
- [ ] Add module to `CleanMastProject.jl`
- [ ] Register commands in `CleanMastCli.jl`
- [ ] Follow three-command workflow if applicable
- [ ] Use established naming conventions (`***Config.jl`, `***Models.jl`)
- [ ] Create proper output structure
- [ ] Generate both machine and human-readable outputs

## Examples from Existing Features

Study these existing features for reference:
- **TowerShading**: Simple process + recommend pattern
- **TrainMeso + ReconstructMeso**: Full three-command workflow
- **AnalyzeReconstructSingle**: Complex analysis with reporting
- **ParseSensors**: Data transformation pattern

This guide ensures consistency across all features while allowing flexibility for feature-specific requirements. 