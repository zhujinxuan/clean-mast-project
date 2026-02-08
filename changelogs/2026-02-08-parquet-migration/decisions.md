# Decision Log - Parquet Migration

## 2026-02-08: Parquet Library Selection

**Context**: Need to choose Parquet library for Julia implementation

**Decision**: Use Parquet2.jl instead of Parquet.jl

**Rationale**:
- Parquet2.jl has full write support with metadata
- Better DataFrames.jl integration
- More active development
- Supports column-level metadata

**Alternatives Considered**:
- Parquet.jl: Only read support, limited metadata
- Arrow.jl: Different format, not compatible with Parquet tools

**Consequences**:
- Need to add new dependency
- Different API than Parquet.jl
- Better long-term support

---

## 2026-02-08: Metadata Storage Strategy

**Context**: Where to store sensor metadata in Parquet files

**Decision**: Store in column-level metadata

**Rationale**:
- Self-contained files
- Metadata travels with data
- Standard Parquet feature
- Accessible from Python/R

**Alternatives Considered**:
- File-level metadata: Less granular
- Sidecar only: Loses benefits of Parquet
- Embedded JSON in column: Overly complex

**Consequences**:
- All values must be strings
- Need conversion functions
- Simpler file management

---

## 2026-02-08: Backward Compatibility Strategy

**Context**: How to handle existing CSV projects during migration

**Decision**: Auto-detect format from file extension

**Rationale**:
- No forced migration for existing projects
- Gradual adoption path
- Simple implementation
- Transparent to users

**Alternatives Considered**:
- Configuration flag: Requires user action
- Version field in config: More complex
- Complete migration tool: High effort

**Consequences**:
- Code must handle both formats
- Slightly more complex load/save functions
- Better user experience

---

## 2026-02-08: Optional Sensors Field

**Context**: TimeSeriesSource.sensors is required but Parquet files embed metadata

**Decision**: Make sensors field optional (Union{String, Nothing})

**Rationale**:
- Parquet files don't need separate sensors file
- Maintains backward compatibility for CSV
- Cleaner API for new projects

**Alternatives Considered**:
- Keep required, pass empty string: Less clear
- Create separate type for Parquet: Too much duplication

**Consequences**:
- Need to handle nothing in TOML serialization
- Must validate sensors present for CSV format
- Better type safety

---

## 2026-02-08: WTTimeSeries Output Format

**Context**: WTTimeSeries produces output for external wind tools

**Decision**: Keep CSV output for WTTimeSeries

**Rationale**:
- External tools expect CSV format
- WT compatibility is critical
- No benefit from Parquet for this use case

**Alternatives Considered**:
- Use Parquet with converter: Adds complexity
- Dual format output: Confusing

**Consequences**:
- One exception in Parquet migration
- Documented in configuration
- No impact on other features

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-08
