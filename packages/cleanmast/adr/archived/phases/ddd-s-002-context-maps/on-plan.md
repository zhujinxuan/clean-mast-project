# Phase: On-Plan - Context Maps

## When to Use
Load this file during the planning/design phase when defining context relationships.

## Related ADR
- Main ADR: `adr/ddd-s-002-context-maps.md` (load first for constraints)

## Design Guidance

### Relationship Patterns

```
Configuration (Customer) 
    ↓ Customer-Supplier
PipelineContext (Supplier - orchestrates all)
    ↓
    ├── DataIngestion (Customer-Supplier via Repository)
    ├── DataProcessing (Customer-Supplier)
    └── Analysis (Customer-Supplier) 
            ↓ Conformist
        Reporting
```

### Key Considerations
- Configuration drives PipelineContext
- PipelineContext owns the workflow
- Repository Protocol decouples DataIngestion from DataProcessing
- Reporting accepts Analysis output format (Conformist)

### Integration Points
1. **Configuration → PipelineContext**: Config object passed at start
2. **DataIngestion → DataProcessing**: TimeSeriesRepository protocol
3. **DataProcessing → Analysis**: Transformed TimeSeriesData
4. **Analysis → Reporting**: ReportAtoms (Analysis defines format)

### Common Pitfalls
- Circular dependencies between contexts
- Direct service calls instead of protocols
- Analysis trying to change Reporting format
- PipelineContext knowing implementation details

## Checklist
Before proceeding to implementation, verify:
- [ ] All 6 context relationships documented
- [ ] Repository protocol defined
- [ ] No circular dependencies
- [ ] Integration points are clear
- [ ] ADR constraints are respected
