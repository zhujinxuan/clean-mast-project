# Batch Processing with Variations: A Claude Code Tutorial

This tutorial demonstrates how to effectively use Claude Code for batch processing tasks where you have:
- **Deterministic logic**: Steps that are the same across all items
- **Variable inputs**: Parameters that differ for each item (file formats, column structures, etc.)

## Case Study: Converting TGL Mast Data to NRG Format

### Problem Overview

We had 4 meteorological mast data files that needed conversion to standardized NRG format:
- Files had different metadata structures (some had 8 header lines, one had none)
- Different sensor configurations (140m vs 120m max height)
- Different original column naming conventions
- Common goal: Convert all to standardized NRG CSV format

### Strategy: Separate Deterministic from Variable

#### ✅ What Claude Code Handles Well (Deterministic Logic)

1. **Identify the processing pattern**
   - User asks: "Can the Python tool handle different delimiters and header formats?"
   - Claude reads documentation and analyzes tool capabilities
   - Claude identifies the multi-step workflow needed

2. **Execute repetitive commands**
   - Once the logic is clear, Claude can run similar commands in parallel
   - Example: Processing 4 files with the same tool but different configs

3. **Generate configuration files systematically**
   - When patterns are identified, Claude creates configs following the same structure
   - Ensures consistency across multiple files

#### 🤔 What Requires Human Input (Variable Inputs)

1. **Domain knowledge decisions**
   - User: "Change pressure unit to hPa, not kPa" (1 mbar = 1 hPa)
   - User: "SW means sensor direction, include it in the NRG format"
   - User: "Keep Battery columns unchanged - they're system stats"

2. **Data-specific variations**
   - Different sensor heights per mast
   - Different column structures
   - Different metadata line counts

3. **Quality checks and corrections**
   - User notices empty first line in output
   - User catches missing sensor direction in mapping

## Workflow Example

### Step 1: Exploration Phase

**Human**: "Let's look at the Python preprocessing tools. Can they handle different delimiters, timestamp formats, and header line numbers?"

**Claude's Role**:
- Reads tool documentation
- Examines actual data files
- Reports capabilities and limitations
- Identifies gaps

**Output**: Clear understanding of what tools can/can't do

```
✅ Tool supports: Different delimiters (\t, ,)
✅ Tool supports: Different timestamp formats (auto, mixed)
❌ Tool limitation: Limited header skipping logic
```

### Step 2: Iterative Prototyping

**Human**: "Process the first file to remove metadata lines"

**Claude's Role**:
- Suggests bash command: `tail -n +9` to skip lines
- Creates directory structure
- Executes and verifies output

**Human Correction**: "There's an empty line at the beginning"

**Claude's Response**:
- Investigates with `od -c` to see actual bytes
- Adjusts from `tail -n +9` to `tail -n +10`
- Re-runs and verifies fix

### Step 3: Pattern Recognition

Once one file works correctly, Claude can:

1. **Apply the pattern to remaining files**
   ```bash
   # Pattern identified: skip 9 lines for files with metadata
   tail -n +10 "MinQinH2*.txt" > "step1-skip-metadata/M230014.txt"
   tail -n +10 "MinQinH3*.txt" > "step1-skip-metadata/M230015.txt"
   # Exception: M230013 has no metadata, just copy
   cp "MinQinH1*.txt" "step1-skip-metadata/M230013.txt"
   ```

2. **Generate config files following the same template**
   - Each mast gets its own TOML config
   - Same structure, different column mappings

### Step 4: Batch Execution

**Human**: "Create the step2 TOMLs and convert results to step2-nrg-format/"

**Claude's Role**:
1. Generate 4 TOML configs with appropriate mappings
2. Create output directory
3. Run 4 conversion commands in parallel
4. Verify all outputs

**Key Insight**: Claude runs commands in parallel when they're independent:
```bash
uv run col-name-normalizer M230013.toml
uv run col-name-normalizer M230014.toml
uv run col-name-normalizer M230015.toml
uv run col-name-normalizer M230017.toml
```

### Step 5: Documentation Updates

**Human**: "Update docs to clarify that Battery columns shouldn't be renamed"

**Claude's Role**:
- Updates documentation with the domain knowledge
- Ensures future users understand the exception

## Best Practices from This Session

### 1. Start with Investigation

Don't assume - let Claude read the docs and explore:
```
"Can you check the py-cleanmast-tools/docs/ to see how to normalize?"
```

### 2. Iterate on One Example First

Get one file working perfectly before scaling:
```
Step 1: Process M230014 → Fix empty line issue
Step 2: Apply fix to all other files
```

### 3. Provide Clear Domain Corrections

When Claude misses something, be specific:
```
❌ "That's wrong"
✅ "SW is the sensor direction, include it: Ch1_Anem_140.00m_SW_Avg_m/s"
```

### 4. Use Progressive Folder Names

Clear naming helps track the pipeline:
```
pre-masts/                    # Original data
├── step1-skip-metadata/      # After removing metadata
└── step2-nrg-format/         # After column renaming
```

### 5. Let Claude Handle Parallelization

Claude can run independent tasks in parallel automatically:
- Reading multiple files simultaneously
- Running multiple conversions
- Checking multiple outputs

## Common Pitfalls to Avoid

### ❌ Don't: Give All Variables Upfront

This makes the task overwhelming:
```
"Here are 4 files with different structures, different metadata,
different sensors, convert them all to NRG format..."
```

### ✅ Do: Progressive Problem Solving

```
1. "Check if the tool can handle our data format variations"
2. "Process one file to remove metadata"
3. "Fix the empty line issue"
4. "Apply to all files"
5. "Generate NRG configs for each"
6. "Run the batch conversion"
```

### ❌ Don't: Assume Claude Knows Your Domain

```
"Convert pressure to the right unit"  # Claude guesses kPa
```

### ✅ Do: Provide Domain Context

```
"Change it to hPa. The NRG supports hPa, kPa and Pa.
Update the docs to reflect this."  # Clear and actionable
```

## When to Use This Approach

This pattern works well for:

- **Data preprocessing pipelines**: Multiple files, similar transformations
- **Configuration generation**: Same structure, different parameters
- **Batch file operations**: Systematic file renaming, format conversion
- **Testing across variations**: Same test, different input scenarios

This pattern is **less suitable** for:

- Truly unique, one-off tasks
- Tasks where every item requires different logic
- Exploratory data analysis without clear patterns

## Key Takeaway

**Humans provide**: Domain knowledge, quality checks, strategic decisions
**Claude executes**: Systematic operations, parallel processing, pattern application

The most effective workflow is:
1. Explore and understand (collaborative)
2. Prototype and verify (iterative)
3. Scale and automate (Claude-driven)
4. Document and refine (collaborative)

This division of labor leverages Claude's strengths (consistency, speed, documentation reading) while keeping human judgment at decision points.
