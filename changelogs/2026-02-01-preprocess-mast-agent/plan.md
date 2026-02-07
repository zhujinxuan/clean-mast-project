# Preprocess Mast Agent

An LLM-powered agent for preprocessing wind measurement tower data directly to parsed files (data CSV and sensors TOML).

---

## Project Structure

- Package location: `packages/preprocess-mast-agent/`
- New workspace member in the monorepo

---

## Coding Standards

- Same Python code standard as existing packages (pydantic, polars, click, etc.)
- Use `ty` instead of `pyright` for type checking
- Use Pydantic AI for LLM communication
- Use `.env` for OpenAI-compatible API configuration

---

## Domain Context

### Input Structure

User places raw data under `{project work dir}/pre-masts/`:

```
pre-masts/
├── mast-A/           # Each mast/lidar at different physical location
│   ├── raw1.csv
│   ├── raw2.csv
│   └── ...
├── mast-B/
│   └── ...
└── lidar-C/          # If equipment replaced at same location, same dir
    └── ...
```

### Output Structure

For each mast/lidar directory, produce:

1. **data.csv** - Merged, cleaned, normalized time series data
2. **sensors.toml** - Sensor metadata with column mappings

### sensors.toml Location Field

The output `sensors.toml` includes an optional location field:

```toml
[location]
latitude = 39.9042      # Optional
longitude = 116.4074    # Optional
geohash = "wx4g0b"      # Optional, ~meter accuracy (geohash precision 8+)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Preprocess Mast Agent                     │
└─────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Subagents    │    │     Tools     │    │   Pipeline    │
│  (LLM-powered)│    │ (Deterministic)│   │   Orchestrator│
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
• Header Recognizer    • Encoding Converter    • File discovery
• Location Extractor   • Data Range Detector   • State management
                       • Format Matcher        • Error handling
• Warning Collector    • CSV Merger            • Phase tracking
• Summary Generator    • Column Normalizer     • User interaction
                       • Type Normalizer
                       • Timestamp Normalizer
                       • Format Converter
                       • Sensors TOML Writer
```

---

## Workflow

### Overview

The agent processes each mast directory through a 7-phase pipeline:

```
Phase 1: File Discovery
    └── Scan pre-masts/{mast-name}/ for all files

Phase 2: Encoding Check & Conversion
    ├── UTF-8 files → keep in place
    ├── Non-UTF8 → move to quarantine/encoding/{charset}/, convert to UTF-8
    └── Binary → move to quarantine/binary/, log warning

Phase 3: Data Range Detection
    ├── Success → proceed with data_beginning_linenum, delimiter
    └── Fail → move to quarantine/data-range-failed/, log warning

Phase 4: Format Grouping (Iterative, max 10 iterations)
    ├── Pick random file from ungrouped
    ├── LLM Subagent: Extract format signature (header only)
    ├── Tool: Match other files by header signature
    │   └── Match criteria: header_hash + column_count + delimiter (exact)
    ├── Move matched files to groups/group-{signature}/
    └── Iterate until all grouped or max iterations reached
        └── If max iterations reached → group-manual-review/
    
    Note: Location is extracted for reference but NOT used for grouping

Phase 5: Intra-Group Merging
    └── For each group: merge files using existing tools

Phase 6: Inter-Group Merging
    └── Smart merge: analyze timestamp overlap and sensor complementarity
        ├── Same time period, different sensors → Horizontal join
        ├── Different time periods, same sensors → Vertical concat
        └── Overlapping time + different sensors → Complex merge

Phase 7: Output Generation & Summary
    ├── Generate data.parquet + data.csv
    ├── Generate sensors.toml
    ├── Move outputs to masts/{mast-name}/
    └── Generate processing report with warnings summary
```

### Directory Structure (Working + Quarantine)

```
pre-masts/{mast-name}/
├── .workflow/                    # Hidden state directory
│   ├── state.json               # Resumable state (phase tracking)
│   ├── processing.log           # Structured logs (JSONL format)
│   └── report.json              # Final summary report
├── quarantine/                  # Failed/problematic files
│   ├── encoding/
│   │   ├── gb2312/
│   │   ├── latin1/
│   │   └── ...
│   ├── binary/
│   └── data-range-failed/
├── groups/                      # Grouped files for processing
│   ├── group-{signature1}/
│   ├── group-{signature2}/
│   └── group-manual-review/     # Ungrouped after max iterations
└── [working UTF-8 files]        # Files ready for processing
```

### State Management

Each mast maintains independent state for resumability:

```json
{
  "phase": "grouping",
  "completed_phases": ["discovery", "encoding", "data-range"],
  "processed_files": ["file1.csv", "file2.csv"],
  "quarantined_files": [
    {"file": "binary.dat", "reason": "BINARY_FILE", "location": "quarantine/binary/"}
  ],
  "groups": {
    "group-abc123": ["file1.csv", "file2.csv"],
    "group-def456": ["file3.csv"]
  },
  "warnings": [],
  "start_time": "2026-02-03T10:00:00Z",
  "last_update": "2026-02-03T10:05:00Z"
}
```

### Error Handling Strategy

| Scenario | Action | Continue? |
|----------|--------|-----------|
| Binary file detected | Quarantine to `quarantine/binary/`, log warning | ✅ Yes |
| Non-UTF8 encoding | Convert to UTF-8, move original to `quarantine/encoding/{charset}/` | ✅ Yes |
| Data range detection fails | Quarantine to `quarantine/data-range-failed/`, log warning | ✅ Yes |
| Max grouping iterations reached | Create `group-manual-review/`, log error | ✅ Yes |
| Header recognition fails | Log error, skip file | ✅ Yes |
| Critical tool failure | Log error, stop mast processing | ❌ No |

### Warning Collection

Structured warning format (JSONL):

```json
{"timestamp": "2026-02-03T10:00:00Z", "level": "WARNING", "category": "BINARY_FILE", "file": "mast-A/data.bin", "message": "Binary file detected, moved to quarantine"}
{"timestamp": "2026-02-03T10:00:01Z", "level": "ERROR", "category": "MAX_GROUPING_ITERATIONS", "file": "mast-A/", "message": "10 iterations reached, 3 files require manual review"}
```

Categories:
- `BINARY_FILE`: Binary files detected
- `ENCODING_CONVERSION`: Non-UTF8 files converted
- `DATA_RANGE_FAILED`: Could not detect data boundaries
- `MAX_GROUPING_ITERATIONS`: Grouping did not converge
- `HEADER_RECOGNITION_FAILED`: Could not parse header
- `LOCATION_EXTRACTION_LOW_CONFIDENCE`: Location found but low confidence
- `MULTIPLE_LOCATIONS`: Different locations found in file group

---

## Components

### Subagents (LLM-powered)

Intelligent agents that analyze and interpret data:

| Subagent | Purpose | Status |
|----------|---------|--------|
| [Header & Sensor Format Recognizer](subagents.md#header--sensor-format-recognizer) | Extract column names and sensor metadata from headers | ✅ Defined |
| [Location Extractor](subagents.md#location-extractor) | Extract geographic coordinates | ⏳ To be defined |
| [Warning Collector](subagents.md#warning-collector) | Aggregate and categorize warnings | ⏳ To be defined |
| [Summary Generator](subagents.md#summary-generator) | Generate final processing report | ⏳ To be defined |

**→ See [subagents.md](subagents.md) for detailed specifications**

### Tools (Deterministic)

Reliable CLI tools for data transformation:

| Tool | Purpose | Status |
|------|---------|--------|
| [Encoding Converter](tools.md#encoding-converter) | Convert files to UTF-8 | ✅ Defined |
| [Data Range Detector](tools.md#data-range-detector) | Detect data boundaries | ✅ Defined |
| [Format Matcher](tools.md#format-match) | Group files by format signature | ✅ Defined |
| [CSV Merger](tools.md#csv-merger) | Merge multiple CSV files | ✅ Exists in preprocess-tools |
| [Column Name Normalizer](tools.md#column-name-normalizer) | Standardize column names | ✅ Exists in preprocess-tools |
| [Type Normalizer](tools.md#type-normalizer) | Convert to numeric types | ✅ Exists in preprocess-tools |
| [Timestamp Normalizer](tools.md#timestamp-normalizer) | Normalize timestamps | ✅ Exists in preprocess-tools |
| [Format Converter](tools.md#format-converter) | Convert to standard format | ⏳ To be defined |
| [Sensors TOML Writer](tools.md#sensors-toml-writer) | Generate sensors.toml | ⏳ To be defined |
| [Smart Group Merger](tools.md#smart-group-merger) | Merge groups based on time/sensor analysis | ⏳ To be defined |

**→ See [tools.md](tools.md) for detailed specifications**

### Test Data

**→ See [test-data-reference.md](test-data-reference.md) for test files and projects**

---

## Integration with Existing Tools

Four tools are already implemented in [`packages/preprocess-tools/`](../packages/preprocess-tools/):

- CSV Merger
- Column Name Normalizer
- Type Normalizer
- Timestamp Normalizer

**Strategy:** Import and wrap these tools rather than reimplementing. See [tools.md](tools.md#tool-integration-strategy) for integration options.

---

## Design Decisions

### Grouping Strategy

**Approach**: Iterative random sampling with convergence detection

1. Randomly select file from ungrouped set
2. LLM extracts format signature (header columns + location fingerprint)
3. Deterministic tool matches remaining files
4. Repeat until all grouped or max iterations (10) reached
5. Ungrouped files after max iterations → `group-manual-review/`

**Rationale**: 
- Random sampling avoids bias toward dominant format
- Max iterations prevents infinite loops
- Manual review group allows human intervention without failing workflow

### Output Format

**Primary**: Parquet (efficient, typed, compressed)
**Secondary**: CSV (compatibility with external tools)
**Metadata**: TOML (human-readable sensor configuration)

### Parallelization

**Per mast**: Sequential (maintain state, handle errors gracefully)
**Across masts**: Parallel (independent processing)

### Resumability

Resume from last completed **phase**, not individual files:
- If interrupted during Phase 4 (grouping), restart from Phase 4
- Don't re-run completed phases (encoding, data-range detection)

---

## Next Steps

### Design Phase (Current)

- [x] Define workflow phases and directory structure
- [x] Define state management approach
- [x] Define error handling and quarantine strategy
- [x] Define warning collection format
- [ ] Define Location Extractor subagent
- [ ] Define Warning Collector subagent
- [ ] Define Summary Generator subagent
- [ ] Define Smart Group Merger tool
- [ ] Define Format Converter tool
- [ ] Define Sensors TOML Writer tool
- [ ] Design Pydantic AI agent integration patterns

### Implementation Phase (Future)

- [ ] Create `packages/preprocess-mast-agent/` structure
- [ ] Implement Encoding Converter
- [ ] Implement Data Range Detector
- [ ] Implement Format Matcher
- [ ] Set up Pydantic AI agent configuration
- [ ] Implement Header & Sensor Format Recognizer
- [ ] Implement Location Extractor
- [ ] Implement Warning Collector
- [ ] Implement Summary Generator
- [ ] Implement Smart Group Merger
- [ ] Implement Sensors TOML Writer

### Polish Phase (Future)

- [ ] Error handling and retry logic
- [ ] User interaction points (confirmation, manual override)
- [ ] Testing strategy
- [ ] Documentation and examples
