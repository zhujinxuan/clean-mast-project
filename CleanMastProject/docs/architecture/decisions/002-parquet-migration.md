# ADR-002: Migrate from CSV+TOML to Parquet Format

## Status

Accepted

## Context

The project historically stored time series data in CSV format with separate TOML files for metadata. This approach had limitations:
- No native support for column-level metadata in CSV
- Separate files increase risk of data/metadata mismatch
- CSV files are larger and slower to read/write
- Limited schema evolution capabilities

## Decision

Migrate to Apache Parquet format with embedded column-level metadata, while maintaining backward compatibility with existing CSV projects.

### Key Decisions

#### Parquet Library Selection

**Decision**: Use Parquet2.jl (Julia) and pyarrow (Python)

- Full write support with metadata
- Better DataFrames.jl integration
- More active development than Parquet.jl
- Supports column-level metadata

**Alternatives Considered**:
- Parquet.jl: Only read support, limited metadata
- Arrow.jl: Different format, not compatible with Parquet tools

#### Metadata Storage Strategy

**Decision**: Store sensor metadata in column-level metadata

- Self-contained files
- Metadata travels with data
- Standard Parquet feature
- Accessible from Python/R

**Alternatives Considered**:
- File-level metadata: Less granular
- Sidecar only: Loses benefits of Parquet
- Embedded JSON in column: Overly complex

#### Backward Compatibility Strategy

**Decision**: Auto-detect format from file extension

- No forced migration for existing projects
- Gradual adoption path
- Simple implementation
- Transparent to users

**Alternatives Considered**:
- Configuration flag: Requires user action
- Version field in config: More complex
- Complete migration tool: High effort

#### Optional Sensors Field

**Decision**: Make `TimeSeriesSource.sensors` field optional (`Union{String, Nothing}`)

- Parquet files don't need separate sensors file
- Maintains backward compatibility for CSV
- Cleaner API for new projects

**Alternatives Considered**:
- Keep required, pass empty string: Less clear
- Create separate type for Parquet: Too much duplication

#### WTTimeSeries Output Format

**Decision**: Keep CSV output for WTTimeSeries

- External tools expect CSV format
- WT compatibility is critical
- No benefit from Parquet for this use case

**Alternatives Considered**:
- Use Parquet with converter: Adds complexity
- Dual format output: Confusing

## Consequences

**Positive**:
- Reduced file sizes (typically 10x smaller)
- Faster read/write operations
- Self-contained data files
- Better interoperability with data science tools

**Negative**:
- Additional dependency (Parquet2.jl, pyarrow)
- Different API than CSV handling
- Slightly more complex load/save functions

**Neutral**:
- Code must handle both formats
- WTTimeSeries remains CSV exception

## References

- Migration plan: [.sisyphus/plans/parquet-migration.md](../../../../.sisyphus/plans/parquet-migration.md)
- Original decisions: [changelogs/2026-02-08-parquet-migration/decisions.md](changelogs/2026-02-08-parquet-migration/decisions.md)
- Migration status: [changelogs/2026-02-08-parquet-migration/README.md](changelogs/2026-02-08-parquet-migration/README.md)
