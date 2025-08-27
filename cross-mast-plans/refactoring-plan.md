# Cross-Mast Reconstruction - Refactoring Plan

## 📋 Overview

This document outlines the complete refactoring plan to change the command name from `analyze reconstruct-cross` to `train reconstruct-cross` across all code files, modules, and documentation.

## 🔄 Command Naming Change

### Before (Current)
```
analyze reconstruct-cross
```

### After (Target)
```
train reconstruct-cross
```

### Rationale
- **train reconstruct-cross**: Focus on the core function of model training
- **analyze reconstruct-cross**: Reserved for future analysis/reporting command

## 📁 File and Directory Changes

### Phase 1: Directory Structure Refactoring

#### 1.1 Create New Directory Structure
```bash
# Create new directory structure
mkdir -p src/TrainReconstructCross/
```

#### 1.2 Move Files from AnalyzeReconstructCross/ to TrainReconstructCross/
```bash
# Move all files from old directory to new directory
mv src/AnalyzeReconstructCross/* src/TrainReconstructCross/
rmdir src/AnalyzeReconstructCross/
```

**Files to be moved:**
- `src/AnalyzeReconstructCross/DataCoverage.jl` → `src/TrainReconstructCross/DataCoverage.jl`
- `src/AnalyzeReconstructCross/CrossMastSpeedCorrelation.jl` → `src/TrainReconstructCross/CrossMastSpeedCorrelation.jl`
- `src/AnalyzeReconstructCross/CrossMastDirectionAnalysis.jl` → `src/TrainReconstructCross/CrossMastDirectionAnalysis.jl`
- `src/AnalyzeReconstructCross/CrossMastSummary.jl` → `src/TrainReconstructCross/CrossMastSummary.jl`
- `src/AnalyzeReconstructCross/AnalyzeReconstructCrossCommand.jl` → `src/TrainReconstructCross/TrainReconstructCrossCommand.jl`
- `src/AnalyzeReconstructCross/RecommendAnalyzeReconstructCrossCommand.jl` → `src/TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl`

### Phase 2: Type File Refactoring

#### 2.1 Rename Configuration Type File
```bash
# Rename the configuration type file
mv src/Types/AnalyzeReconstructCrossConfig.jl src/Types/TrainReconstructCrossConfig.jl
```

#### 2.2 Update Type Names in TrainReconstructCrossConfig.jl
**File:** `src/Types/TrainReconstructCrossConfig.jl`

**Changes needed:**
- `AnalyzeReconstructCrossConfiguration` → `TrainReconstructCrossConfiguration`
- `AnalyzeCrossMast` → `TrainCrossMast`
- `AnalyzeCrossSettings` → `TrainCrossSettings`
- `analyze` field → `train` field

### Phase 3: Module Names and References

#### 3.1 Update Module Names
**File:** `src/CleanMastProject.jl`

**Changes needed:**
```julia
# Old module declaration
module AnalyzeReconstructCross
  include("./AnalyzeReconstructCross/DataCoverage.jl")
  include("./AnalyzeReconstructCross/CrossMastSpeedCorrelation.jl")
  include("./AnalyzeReconstructCross/CrossMastDirectionAnalysis.jl")
  include("./AnalyzeReconstructCross/CrossMastSummary.jl")
  # ... other includes
end

# New module declaration
module TrainReconstructCross
  include("./TrainReconstructCross/DataCoverage.jl")
  include("./TrainReconstructCross/CrossMastSpeedCorrelation.jl")
  include("./TrainReconstructCross/CrossMastDirectionAnalysis.jl")
  include("./TrainReconstructCross/CrossMastSummary.jl")
  # ... other includes
end
```

**Changes needed:**
- `AnalyzeReconstructCross` module → `TrainReconstructCross` module
- Update all include paths
- Update export statements

#### 3.2 Update Command File Names and Content
**File:** `src/TrainReconstructCross/TrainReconstructCrossCommand.jl`

**Changes needed:**
- Function comments: "analyze" → "train"
- Configuration loading: `load_analyze_config` → `load_train_config`
- Output paths: `analyze-results.toml` → `train-results.toml`
- Progress messages: "Analyzing" → "Training"
- Function names: `analyze_mast_pair` → `train_mast_pair`

**File:** `src/TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl`

**Changes needed:**
- Output file: `analyze-reconstruct-cross.toml` → `train-reconstruct-cross.toml`
- Function comments and messages

### Phase 4: CLI Integration Updates

#### 4.1 Update CLI Command Registration
**File:** `src/CleanMastCli.jl`

**Changes needed:**
```julia
# Old CLI structure
"recommend"
  "analyze-reconstruct-cross"
"analyze"
  "reconstruct-cross"

# New CLI structure  
"recommend"
  "train-reconstruct-cross"
"train"
  "reconstruct-cross"
```

**Specific changes:**
- Add `"train"` main command section
- Move `"reconstruct-cross"` from `"analyze"` to `"train"`
- Update `"recommend"` subcommand: `"analyze-reconstruct-cross"` → `"train-reconstruct-cross"`
- Update help text and descriptions
- Update command execution logic

#### 4.2 Update Command Export Statements
**File:** `src/CleanMastProject.jl`

**Changes needed:**
```julia
# Old exports
export AnalyzeReconstructCrossCommand, RecommendAnalyzeReconstructCrossCommand

# New exports
export TrainReconstructCrossCommand, RecommendTrainReconstructCrossCommand
```

### Phase 5: Test File Updates

#### 5.1 Move Test Directory
```bash
# Move test directory if it exists
mv test/AnalyzeReconstructCross/ test/TrainReconstructCross/
```

#### 5.2 Update Test File Names
**Files to rename:**
- `test/AnalyzeReconstructCross/*` → `test/TrainReconstructCross/*`

#### 5.3 Update Test Content
**Changes needed in test files:**
- Module references: `AnalyzeReconstructCross` → `TrainReconstructCross`
- Function names and test cases
- Configuration file names in tests

### Phase 6: Configuration and Output Updates

#### 6.1 Default Configuration File Names
**Files affected:**
- Example configuration files
- Documentation references
- Default file paths in code

**Changes needed:**
- `analyze-reconstruct-cross.toml` → `train-reconstruct-cross.toml`
- `analyze-results.toml` → `train-results.toml`
- Output directory: `./analyze-reconstruct-cross/` → `./train-reconstruct-cross/`

#### 6.2 Update Function Names in Command Files
**File:** `src/TrainReconstructCross/TrainReconstructCrossCommand.jl`

**Functions to rename:**
- `load_analyze_config` → `load_train_config`
- `save_analyze_results_toml` → `save_train_results_toml`
- `analyze_mast_pair` → `train_mast_pair`

## 🔍 Detailed File-by-File Changes

### File: `src/Types/TrainReconstructCrossConfig.jl`
```julia
# Change struct names
struct TrainReconstructCrossConfiguration  # was: AnalyzeReconstructCrossConfiguration
    masts::Vector{TrainCrossMast}          # was: AnalyzeCrossMast
    train::TrainCrossSettings              # was: analyze::AnalyzeCrossSettings
end

struct TrainCrossMast                      # was: AnalyzeCrossMast
    name::String
    input::TimeSeriesSource
end

struct TrainCrossSettings                  # was: AnalyzeCrossSettings
    output_dir::String
end
```

### File: `src/TrainReconstructCross/TrainReconstructCrossCommand.jl`
```julia
# Update module documentation
"""
TrainReconstructCrossCommand

Main command for training cross-mast reconstruction models.
"""

# Update function names and messages
function execute(config_path::String)
    println("Starting cross-mast training...")  # was: "analysis"
    
    config = load_train_config(config_path)  # was: load_analyze_config
    
    # Update output directory references
    mkpath(config.train.output_dir)  # was: config.analyze.output_dir
    
    # Update progress messages
    println("Training pair $pair_count/$total_pairs...")  # was: "Analyzing"
    
    # Update result file names
    results_path = joinpath(config.train.output_dir, "train-results.toml")  # was: "analyze-results.toml"
    save_train_results_toml(analysis_results, results_path)  # was: save_analyze_results_toml
    
    println("Cross-mast training completed!")  # was: "analysis"
end

# Update function names
function train_mast_pair(...)  # was: analyze_mast_pair
    # Implementation remains the same, just renamed
end

function load_train_config(...)  # was: load_analyze_config
    # Implementation remains the same, just renamed
end

function save_train_results_toml(...)  # was: save_analyze_results_toml
    # Implementation remains the same, just renamed
end
```

### File: `src/TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl`
```julia
# Update function to generate train-reconstruct-cross.toml
function execute(project_dir::String)
    println("Generating train-reconstruct-cross.toml configuration...")  # was: analyze-reconstruct-cross.toml
    
    # Generate configuration
    config_path = joinpath(project_dir, "train-reconstruct-cross.toml")  # was: analyze-reconstruct-cross.toml
    
    # Update output directory default
    toml_content = """
[[masts]]
name = "$(mast_name)"
input.data = "$(relative_path)"
input.sensors = "$(sensors_path)"

[train]  # was: [analyze]
output_dir = "./train-reconstruct-cross"  # was: analyze-reconstruct-cross
"""
    
    println("Generated: $config_path")
end
```

### File: `src/CleanMastCli.jl`
```julia
# Add new train command section
@add_arg_table! s begin
    "recommend"
        action = :command
        help = "Recommend configuration for various commands"
        @add_arg_table! begin
            "train-reconstruct-cross"  # was: "analyze-reconstruct-cross"
                action = :command
                help = "Generate train-reconstruct-cross.toml configuration"  # was: analyze-reconstruct-cross.toml
        end
    "train"  # NEW: was under "analyze"
        action = :command
        help = "Train models for various purposes"
        @add_arg_table! begin
            "reconstruct-cross"
                action = :command
                help = "Train cross-mast relationships and models"  # was: "Analyze cross-mast relationships"
                "config"
                    arg_type = String
                    required = true
                    help = "Path to train-reconstruct-cross.toml configuration file"  # was: analyze-reconstruct-cross.toml
        end
end

# Update command execution logic
if parsed_args["train"]["reconstruct-cross"] !== nothing  # was: ["analyze"]["reconstruct-cross"]
    config_path = parsed_args["train"]["reconstruct-cross"]["config"]  # was: ["analyze"]["reconstruct-cross"]["config"]
    TrainReconstructCrossCommand.execute(config_path)  # was: AnalyzeReconstructCrossCommand.execute
end

if parsed_args["recommend"]["train-reconstruct-cross"] !== nothing  # was: ["analyze-reconstruct-cross"]
    project_dir = parsed_args["recommend"]["train-reconstruct-cross"]["project_dir"]  # was: ["analyze-reconstruct-cross"]["project_dir"]
    RecommendTrainReconstructCrossCommand.execute(project_dir)  # was: RecommendAnalyzeReconstructCrossCommand.execute
end
```

### File: `src/CleanMastProject.jl`
```julia
# Update module includes
include("TrainReconstructCross/DataCoverage.jl")  # was: AnalyzeReconstructCross/DataCoverage.jl
include("TrainReconstructCross/CrossMastSpeedCorrelation.jl")  # was: AnalyzeReconstructCross/CrossMastSpeedCorrelation.jl
include("TrainReconstructCross/CrossMastDirectionAnalysis.jl")  # was: AnalyzeReconstructCross/CrossMastDirectionAnalysis.jl
include("TrainReconstructCross/CrossMastSummary.jl")  # was: AnalyzeReconstructCross/CrossMastSummary.jl
include("TrainReconstructCross/TrainReconstructCrossCommand.jl")  # was: AnalyzeReconstructCross/AnalyzeReconstructCrossCommand.jl
include("TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl")  # was: AnalyzeReconstructCross/RecommendAnalyzeReconstructCrossCommand.jl

# Update module declaration
module TrainReconstructCross  # was: AnalyzeReconstructCross
  include("./TrainReconstructCross/DataCoverage.jl")  # was: ./AnalyzeReconstructCross/DataCoverage.jl
  include("./TrainReconstructCross/CrossMastSpeedCorrelation.jl")  # was: ./AnalyzeReconstructCross/CrossMastSpeedCorrelation.jl
  include("./TrainReconstructCross/CrossMastDirectionAnalysis.jl")  # was: ./AnalyzeReconstructCross/CrossMastDirectionAnalysis.jl
  include("./TrainReconstructCross/CrossMastSummary.jl")  # was: ./AnalyzeReconstructCross/CrossMastSummary.jl
  # ... other includes
end

# Update exports
export TrainReconstructCrossCommand, RecommendTrainReconstructCrossCommand  # was: AnalyzeReconstructCrossCommand, RecommendAnalyzeReconstructCrossCommand
export TrainReconstructCross  # was: AnalyzeReconstructCross
```

## 🧪 Testing Strategy

### Phase 1: Compilation Testing
```bash
# Test that package compiles after refactoring
julia --project -e "using CleanMastProject"
```

### Phase 2: CLI Testing
```bash
# Test new CLI commands
julia --project bin/CleanMast.jl recommend train-reconstruct-cross
julia --project bin/CleanMast.jl train reconstruct-cross config.toml
```

### Phase 3: Unit Testing
```bash
# Run specific tests if they exist
julia --project -e "using Pkg; Pkg.test()"
```

## 📝 Documentation Updates

### Files to Update
- `README.md` - Update command examples
- `docs/quick-tutorial.md` - Update command references
- `cross-mast-plans/overall-plan.md` - ✅ Already updated
- `cross-mast-plans/plan-train-reconstruct-cross.md` - ✅ Already updated

### Example Configuration Files
- `example_project/train-reconstruct-cross.toml` - Create new example
- Remove old `analyze-reconstruct-cross.toml` examples

## 🚀 Execution Order

### Step 1: Preparation
1. Create backup of current codebase
2. Ensure all changes are committed to git

### Step 2: Directory and File Moves
1. Create `src/TrainReconstructCross/` directory
2. Move files from `src/AnalyzeReconstructCross/` to `src/TrainReconstructCross/`
3. Remove empty `src/AnalyzeReconstructCross/` directory
4. Rename `src/Types/AnalyzeReconstructCrossConfig.jl` to `src/Types/TrainReconstructCrossConfig.jl`

### Step 3: Content Updates
1. Update `src/Types/TrainReconstructCrossConfig.jl` - struct names and fields
2. Update `src/TrainReconstructCross/TrainReconstructCrossCommand.jl` - function names and messages
3. Update `src/TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl` - output file names
4. Update `src/CleanMastProject.jl` - module includes and exports
5. Update `src/CleanMastCli.jl` - CLI command structure

### Step 4: Testing and Validation
1. Test compilation: `julia --project -e "using CleanMastProject"`
2. Test CLI help: `julia --project bin/CleanMast.jl --help`
3. Test command registration: `julia --project bin/CleanMast.jl train --help`
4. Run any existing tests

### Step 5: Documentation Updates
1. Update example configuration files
2. Update README and documentation
3. Update any remaining references in other files

## 🎯 Success Criteria

### Functional Requirements
- [ ] `julia --project bin/CleanMast.jl recommend train-reconstruct-cross` works
- [ ] `julia --project bin/CleanMast.jl train reconstruct-cross config.toml` works
- [ ] Package compiles without errors
- [ ] All module exports work correctly

### Code Quality Requirements
- [ ] No broken import statements
- [ ] No orphaned references to old names
- [ ] Consistent naming throughout codebase
- [ ] All tests pass (if they exist)

### Documentation Requirements
- [ ] All documentation updated with new command names
- [ ] Example configuration files updated
- [ ] Help text displays correctly

## 📋 Refactoring Checklist

### Pre-Refactoring
- [ ] Backup current codebase
- [ ] Commit all current changes
- [ ] Document current working state

### Directory Structure
- [ ] Create `src/TrainReconstructCross/` directory
- [ ] Move all files from `src/AnalyzeReconstructCross/` to `src/TrainReconstructCross/`
- [ ] Remove empty `src/AnalyzeReconstructCross/` directory
- [ ] Rename `src/Types/AnalyzeReconstructCrossConfig.jl` to `src/Types/TrainReconstructCrossConfig.jl`

### Type Definitions
- [ ] Update struct names in `TrainReconstructCrossConfig.jl`
- [ ] Change `analyze` field to `train` field
- [ ] Update type names: `AnalyzeCrossMast` → `TrainCrossMast`
- [ ] Update type names: `AnalyzeCrossSettings` → `TrainCrossSettings`

### Command Files
- [ ] Update `TrainReconstructCrossCommand.jl` function names
- [ ] Update progress messages and output file names
- [ ] Update `RecommendTrainReconstructCrossCommand.jl` output file names
- [ ] Update all comments and documentation strings

### Module Integration
- [ ] Update `CleanMastProject.jl` module includes
- [ ] Update `CleanMastProject.jl` module exports
- [ ] Update `CleanMastProject.jl` module declarations

### CLI Integration
- [ ] Update `CleanMastCli.jl` command structure
- [ ] Add `train` main command
- [ ] Update `recommend` subcommand
- [ ] Update command execution logic
- [ ] Update help text and descriptions

### Testing
- [ ] Test package compilation
- [ ] Test CLI help commands
- [ ] Test command registration
- [ ] Run unit tests if they exist
- [ ] Test example configuration generation

### Documentation
- [ ] Update README.md
- [ ] Update tutorial documentation
- [ ] Update example configuration files
- [ ] Update plan documents (already done)

### Post-Refactoring
- [ ] Verify all functionality works
- [ ] Commit refactored code
- [ ] Create pull request/merge if needed
- [ ] Update project documentation

This refactoring plan ensures a systematic and thorough transition from the `analyze reconstruct-cross` command to the `train reconstruct-cross` command while maintaining all existing functionality and code quality standards. 