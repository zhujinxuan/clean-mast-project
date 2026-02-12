# CleanMast Documentation Hub

## Overview

CleanMast is a wind energy meteorological tower data processing toolkit built with Julia. This documentation hub provides navigation to all documentation sections for CleanMast.

## Documentation Sections

### [C4 Architecture](c4/)

System architecture documentation using the C4 model for software architecture visualization.

- **Level 1: System Context** ([c4/01-context/](c4/01-context/)) - High-level system overview, user interactions, and external system relationships
- **Level 2: Containers** ([c4/02-container/](c4/02-container/)) - Container-level architecture showing major processing modules and data flows
- **Level 3: Components** ([c4/03-component/](c4/03-component/)) - Detailed component interfaces and implementations
  - [ParseSensors](c4/03-component/parse-sensors.md) - Sensor data parsing component
  - [Data Clean](c4/03-component/data-clean.md) - Data cleaning component
  - [Reconstruction](c4/03-component/reconstruction.md) - Data reconstruction component
  - [Reporting](c4/03-component/reporting.md) - Report generation component

### [User Guide](user/)

End-user documentation for operating CleanMast effectively.

- [User Guide README](user/README.md) - Complete user guide with installation, quick start, and workflows
- **Quick Start** ([user-guide/quickstart.md](user-guide/quickstart.md)) - Get started with CleanMast in minutes
- **Workflows** ([user-guide/workflow/](user-guide/workflow/))
  - [Complete Pipeline](user-guide/workflow/complete-pipeline.md) - End-to-end data processing workflow
  - [Troubleshooting](user-guide/workflow/troubleshooting.md) - Common issues and solutions
- **Commands** ([user/commands/](user/commands/))
  - [Project Commands](user/commands/project.md) - Project initialization and parsing commands
  - [Process Steps Overview](user/commands/process/process-steps.md) - Data processing pipeline commands
  - [Process Commands](user/commands/process/) - Detailed process commands
    - [Clean](user/commands/process/clean.md) - Data cleaning
    - [Tower Shading](user/commands/process/tower-shading.md) - Tower shadow correction
    - [Reconstruct Single](user/commands/process/reconstruct-single.md) - Single-mast reconstruction
    - [Reconstruct Meso](user/commands/process/reconstruct-meso.md) - Mesoscale reconstruction
    - [Train Meso](user/commands/process/train-meso.md) - Mesoscale model training
    - [Train Reconstruct Cross](user/commands/process/train-reconstruct-cross.md) - Cross-mast training
    - [Representative Year](user/commands/process/representative-year.md) - Long-term calibration
    - [WT TimeSeries](user/commands/process/wt-timeseries.md) - Wind turbine time series
  - [Recommend Commands](user/commands/recommend.md) - Configuration generation commands
  - [Report Commands](user/commands/report-all.md) - Report generation overview
  - [Report Commands](user/commands/report/) - Detailed report commands
    - [All Reports](user/commands/report/all.md)
    - [Clean Report](user/commands/report/clean.md)
    - [Recovery Report](user/commands/report/recovery.md)
    - [Reconstruct Single Report](user/commands/report/reconstruct-single.md)
    - [Representative Year Report](user/commands/report/representative-year.md)
    - [TimeSeries Report](user/commands/report/timeseries.md)
    - [Cross Mast Report](user/commands/report/cross-mast.md)
- **Configuration** ([user/configuration/](user/configuration/))
  - [Config Files Overview](user/configuration/config-files.md)
  - [Parse Sensors Config](user/configuration/config-files/parse-sensors.md)
  - [Process Clean Config](user/configuration/config-files/process-clean.md)
  - [Tower Shading Config](user/configuration/config-files/tower-shading.md)
  - [Reconstruct Single Config](user/configuration/config-files/reconstruct-single.md)
  - [Reconstruct Meso Config](user/configuration/config-files/reconstruct-meso.md)
  - [Train Meso Config](user/configuration/config-files/train-meso.md)
  - [Reconstruct Cross Config](user/configuration/config-files/reconstruct-cross.md)
  - [Report Configs](user/configuration/report-configs.md)

### [Technical Documentation](technical/)

Detailed technical documentation on algorithms, quality control, and industry standards implementation.

- [Technical README](technical/README.md) - Technical implementation overview
- **[Algorithms](technical/algorithms/)** - Algorithm implementation details
  - [Data Cleaning](technical/algorithms/data-cleaning.md) - Range checks, icing detection
  - [Tower Shading](technical/algorithms/tower-shading.md) - Tower shadow correction
  - [Reconstruction](technical/algorithms/) - Single-mast, mesoscale, cross-mast methods
  - [Representative Year](technical/algorithms/representative-year.md) - Long-term calibration
- **[Quality Control](domain/data-quality.md)** - Data quality standards and validation
- **[Standards](domain/)** - IEC 61400 series implementation

### [Development Documentation](development/)

Developer-focused documentation for contributing to CleanMast.

- [Development README](development/README.md) - Complete development guide
- **Architecture** ([development/architecture/](development/architecture/))
  - [Overview](development/architecture/overview.md)
- [Tests Documentation](development/tests.md) - Testing conventions
- [Parallel Logging](development/parallel-logging.md) - Logging system documentation
- **API Documentation** ([development/api/public-interfaces.md](development/api/public-interfaces.md)) - Public interfaces and type system
- **Code Style** - [Julia Guide](development/code-style/julia-guide.md)
- **Module Structure** ([development/architecture/patterns.md](development/architecture/patterns.md)) - Module organization and design patterns
- **Setup Guide** ([development/contributing.md](development/contributing.md)) - Development environment setup
- **Contributing Guide** - [Contribution Guidelines](development/contributing.md)

### [Architecture Decisions](architecture/decisions/)

Architecture Decision Records (ADRs) documenting significant technical decisions.

- [ADR Index](architecture/decisions/README.md)
- [001: Adopt C4 Model](architecture/decisions/001-adopt-c4-model.md)
- [002: Parquet Migration](architecture/decisions/002-parquet-migration.md)
- [ADR Template](architecture/decisions/ADR-template.md)

### [Changelog](../../changelogs/)

Historical record of significant changes and features.

- [Changelog Index](../../changelogs/)
- [2026-02-08: Parquet Migration](../../changelogs/2026-02-08-parquet-migration/)
- [2026-02-01: Preprocess Mast Agent](../../changelogs/2026-02-01-preprocess-mast-agent/)
- [2025-10-12: Parallel Logging System](../../changelogs/2025-10-12-parallel-logging-system.md)
- [2025-10-11: Meso Reconstruction Report](../../changelogs/2025-10-11-feat-meso-reconstruction-report.md)
- [2025-08-29: Cross-Mast Reconstruction System](changelog/2025-08-29-cross-mast-reconstruction-system.md)
- [Older Entries](changelog/)

### [Domain Knowledge](domain/)

Domain-specific knowledge for wind energy and meteorology.

- [Wind Energy Basics](domain/wind-energy-basics.md) - Wind speed, direction, turbulence fundamentals
- [Sensor Types](domain/sensor-types.md) - Meteorological tower sensors (IEC 61400-12-1)
- [Data Quality](domain/data-quality.md) - Data quality standards and validation
- [Reconstruction Methods](domain/reconstruction-methods.md) - Method selection guide

## Quick Links by User Type

### For New Users

1. Start with the [User Guide](user/README.md)
2. Follow the [Quick Start](user/README.md#快速开始) section
3. Learn about [Commands](user/commands/) as needed
4. Reference [Configuration](user/configuration/) for detailed settings

### For Power Users

1. Understand the [System Architecture](c4/)
2. Explore [Technical Documentation](technical/)
3. Review [Configuration Options](user/configuration/)
4. Check [Changelog](changelog/) for latest features

### For Developers

1. Read the [Development Guide](development/README.md)
2. Review [Architecture Decisions](architecture/decisions/)
3. Check [C4 Components](c4/03-component/) for implementation details
4. Follow [Coding Standards](development/) when contributing

### For Architects

1. Review [C4 Level 1-3](c4/) for system understanding
2. Read [Architecture Decisions](architecture/decisions/) for key choices
3. Understand [Data Flows](c4/02-container/) for integration patterns

## Data Processing Pipeline

CleanMast processes wind measurement data through a multi-stage pipeline:

```
Raw Sensor Data → Parse → Clean → Tower Shading → Reconstruct → Report
                  ↓         ↓         ↓            ↓           ↓
             parse-    process-  tower-     reconstruct-  report
             sensors   clean     shading    single/meso   all
```

### Pipeline Stages

1. **ParseSensors** - Convert raw CSV/TXT to structured data
   - [User Guide](user/commands/project.md)
   - [Config Reference](user/configuration/config-files/parse-sensors.md)

2. **DataClean** - Apply validation rules
   - [User Guide](user/commands/process/clean.md)
   - [Config Reference](user/configuration/config-files/process-clean.md)

3. **TowerShading** - Detect and correct tower effects
   - [User Guide](user/commands/process/tower-shading.md)
   - [Config Reference](user/configuration/config-files/tower-shading.md)

4. **ReconstructSingle** - Single-mast correlation reconstruction
   - [User Guide](user/commands/process/reconstruct-single.md)
   - [Config Reference](user/configuration/config-files/reconstruct-single.md)

5. **TrainMeso / ReconstructMeso** - Mesoscale data integration
   - [User Guide](user/commands/process/train-meso.md)
   - [Config Reference](user/configuration/config-files/train-meso.md)
   - [User Guide](user/commands/process/reconstruct-meso.md)
   - [Config Reference](user/configuration/config-files/reconstruct-meso.md)

6. **RepresentativeYear** - Long-term calibration
   - [User Guide](user/commands/process/representative-year.md)

7. **Report Generation** - Analysis and reporting
   - [User Guide](user/commands/report-all.md)
   - [All Reports](user/commands/report/all.md)

## Command Reference

| Category | Command | Documentation |
|----------|---------|---------------|
| **Project** | `project parse-sensors` | [User Guide](user/commands/project.md) |
| **Process** | `process steps` | [Guide](user/commands/process/process-steps.md) |
| **Process** | `process clean` | [Guide](user/commands/process/clean.md) |
| **Process** | `process tower-shading` | [Guide](user/commands/process/tower-shading.md) |
| **Process** | `process reconstruct-single` | [Guide](user/commands/process/reconstruct-single.md) |
| **Process** | `process train-meso` | [Guide](user/commands/process/train-meso.md) |
| **Process** | `process reconstruct-meso` | [Guide](user/commands/process/reconstruct-meso.md) |
| **Process** | `process representative-year` | [Guide](user/commands/process/representative-year.md) |
| **Recommend** | `recommend <stage>` | [Guide](user/commands/recommend.md) |
| **Report** | `report all` | [Guide](user/commands/report/all.md) |
| **Report** | `report clean` | [Guide](user/commands/report/clean.md) |
| **Report** | `report timeseries` | [Guide](user/commands/report/timeseries.md) |

## Configuration Files

| Config File | Purpose | Documentation |
|-------------|---------|---------------|
| `parse-sensors.toml` | Sensor column mapping | [Reference](user/configuration/config-files/parse-sensors.md) |
| `process-clean.toml` | Data cleaning rules | [Reference](user/configuration/config-files/process-clean.md) |
| `tower-shading.toml` | Tower shadow correction | [Reference](user/configuration/config-files/tower-shading.md) |
| `reconstruct-single.toml` | Single-mast reconstruction | [Reference](user/configuration/config-files/reconstruct-single.md) |
| `train-meso.toml` | Mesoscale model training | [Reference](user/configuration/config-files/train-meso.md) |
| `reconstruct-meso.toml` | Mesoscale reconstruction | [Reference](user/configuration/config-files/reconstruct-meso.md) |
| `representative-year.toml` | Long-term calibration | [Reference](user/configuration/config-files.md) |
| `wt-timeseries.toml` | Wind turbine time series | [Reference](user/configuration/config-files.md) |

## External Dependencies

- **Julia 1.6+** - Core language runtime
- **Comonicon.jl** - CLI framework
- **DataFrames.jl** - Data processing
- **GLM.jl** - Statistical modeling
- **Typst** - Report generation
- **Meteodyn WT** - Turbulence analysis (optional)

## Related Documentation

- [Project README](../../README.md) - Main project overview
- [CLAUDE.md](../../CLAUDE.md) - AI assistant guidelines
- [Test Documentation](development/tests.md) - Testing conventions

---

## Documentation Status

✅ **All core documentation completed (2026-02-12)**

The documentation project has been completed with the following deliverables:

### Completed Sections

- **Domain Knowledge** - 4 documents covering wind energy fundamentals, sensors, data quality, and reconstruction methods
- **Technical/Algorithms** - 8 algorithm documents with conceptual descriptions and source references
- **User Guides** - Quick start, complete pipeline workflow, and preprocessing guides
- **Developer Docs** - Julia code style guide and contribution guidelines
- **C4 Architecture** - Level 1-3 component documentation

### Optional Enhancements

The following sections are available for future expansion:

- **technical/quality-control/** - Detailed quality metrics documentation
- **technical/standards/** - Extended standards reference documentation  
- **development/api/** - Auto-generated API documentation
- **development/testing/** - Extended testing guide
- **architecture/patterns/** - Design patterns documentation
- **c4/04-code/** - Code-level documentation (auto-generated)

## Contributing to Documentation

When adding documentation:

1. Place user-facing docs in `user/`
2. Place technical/algorithmic docs in `technical/`
3. Place developer docs in `development/`
4. Update this hub README with new sections
5. Follow the [writing guidelines](how-to-write-in-docs.md)

See [how-to-write-in-docs.md](how-to-write-in-docs.md) for documentation standards.
