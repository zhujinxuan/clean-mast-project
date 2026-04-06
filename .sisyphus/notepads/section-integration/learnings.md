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
