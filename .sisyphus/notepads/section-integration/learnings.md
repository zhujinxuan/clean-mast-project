## LEARNINGS: Section Integration Implementation

### Architecture Pattern

```
TimeSeriesReportSection (orchestrator)
├── WindRoseSubsection
├── WindTemporalSubsection  
├── WeibullSubsection
├── WindFrequencySubsection
├── TurbulenceSubsection
└── VerticalProfileSubsection
```

### Configuration Pattern
- Use dataclasses with default values
- Support YAML config loading
- Boolean toggles for each subsection
- Optional subsection-specific settings

### Subsection Pattern
```python
class Subsection:
    def __init__(self, mast_data, config):
        self.mast_data = mast_data
        self.config = config
    
    def render(self, output_dir: Path) -> str:
        # Run analysis
        # Convert to atoms
        # Render each atom
        # Return Typst content
```

### Main Section Pattern
```python
class TimeSeriesReportSection:
    def _instantiate_subsections(self):
        if self.config.windrose:
            yield WindRoseSubsection(...)
        # ... etc
    
    def render(self, output_dir):
        parts = [header]
        for subsection in self.subsections:
            parts.append(subsection.render(output_dir))
        return "\n\n".join(parts)
```

### Typst Output Pattern
```typst
= 测风塔{name}分析报告

== {subsection_title}
#figure(image("{image_path}"), caption: [...])
#table(...)

{summary_text}
```

### Key Decisions
- Each subsection responsible for its own analysis
- Atoms render independently
- Main section combines Typst content
- Config controls subsection inclusion

### Service.generate() Pattern (Phase 3 - Service Merge)
Each subsection renamed from `XxxSubsection` to `XxxService` with:
- `@classmethod generate(cls, items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]])` 
- Creates analyzer + builder inside the classmethod
- Returns `cls(atoms=AtomCollection.from_dict(collection_dict))`
- Backward compat alias: `XxxSubsection = XxxService` at module level

Pilot: `WeibullService` in `subdomains/weibull/services/weibull_section.py`
Implemented: `WindTemporalService` in `subdomains/wind_temporal/services/wind_temporal_section.py`

Key: `builder.build()` takes `time_series_result=daily_result, daily_result=daily_result` — same object
passed as both first and second parameter (orchestrator pattern preserved).
