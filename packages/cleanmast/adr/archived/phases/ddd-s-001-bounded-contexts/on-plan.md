# Phase: On-Plan - Bounded Contexts

## When to Use
Load this file during the planning/design phase when defining CleanMast context boundaries.

## Related ADR
- Main ADR: `adr/ddd-s-001-bounded-contexts.md` (load first for constraints)

## Design Guidance

### The Six CleanMast Contexts

| Context | Responsibility | Key Models | Output |
|---------|---------------|------------|--------|
| **Configuration** | Generate config recommendations | MastConfig, SensorPlacement | Config files |
| **PipelineContext** | Orchestrate workflow | PipelinePhase, PipelineRunner | Coordinates all |
| **DataIngestion** | Parse and load raw data | SensorColumn, TimeSeriesData | Parsed data |
| **DataProcessing** | Clean and reconstruct | DataCleaner, Reconstructor | Cleaned data |
| **Analysis** | Calculate statistics | WindRose, Weibull, TI | Analysis results |
| **Reporting** | Generate reports | ReportAtom, ReportBuilder | Final reports |

### Key Considerations
- Each context owns its own vocabulary - "Sensor" means something different in Ingestion vs Configuration
- TimeSeriesData is a DTO, not owned by any context
- PipelineContext is the only context that knows about all others
- Configuration context is upstream, Reporting is downstream

### Common Pitfalls
- Creating too many contexts - stick to 6
- Allowing contexts to share implementation details
- Putting business logic in the shared kernel (TimeSeriesData)

## Checklist
Before proceeding to implementation, verify:
- [ ] All 6 contexts are clearly defined with boundaries
- [ ] Each context has distinct responsibilities
- [ ] Shared kernel is limited to TimeSeriesData DTO
- [ ] Context names use PascalCase
- [ ] ADR constraints are respected
