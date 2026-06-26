# Import Contracts: DDD-S-003 Subdomain Deepening

> **Phase**: code — Specification for allowed/forbidden imports.
> **Authoritative source**: `ddd-s-003-subdomain-deepening.md` + `.importlinter`
> **Purpose**: Enforcement reference for developers and automated import-linter contracts.

---

## 1. Architecture Overview

```
assessment/
├── shared/                    # Contract surface (protocols, types, utils)
│   ├── protocols/             # Section, ReportAtom, DataSetAccess (ABCs)
│   ├── adapter_protocols/     # ConfigProvider, DataLoader
│   ├── ir_types/              # TypstHeading, TypstSection, TypstBody
│   └── utils/                 # subsection_renderer, merge (pure, stateless)
├── adapters/                  # Concrete implementations (ParquetDataSet, TomlConfig, etc.)
├── domain/                    # Parent domain (ReportAssemblyService, AtomCollection)
│   ├── services/
│   ├── entities/
│   └── value_objects/
└── subdomains/                # 10 capability subdomains
    ├── wind_rose/
    ├── weibull/
    ├── turbulence/
    ├── wind_frequency/
    ├── wind_temporal/
    ├── vertical_profile/
    ├── extreme_wind/
    ├── representative_year/
    ├── air_density/
    └── iec_standards/
```

### Principle

> **Protocols gate all external access.** A subdomain never imports another subdomain's concrete type. If it needs data, it goes through a protocol in `shared/`. The protocol IS the API.

---

## 2. Allowed Imports (Subdomain Perspective)

### 2.1 shared.protocols

Protocols provide the contract surface all subdomains depend on for structural integration with the parent orchestrator.

```python
# ✅ ALLOWED: Import shared protocols
from assessment.shared.protocols import Section, ReportAtom, DataSetAccess

# ✅ ALLOWED: Subclass/implement shared protocols
from assessment.shared.protocols import Section
from assessment.shared.ir_types import TypstSection


class WindRoseSection(Section):
    @property
    def title(self) -> str:
        return "风向频率玫瑰图"

    @property
    def atoms(self) -> AtomCollection:
        return self._atoms

    def render_ir(self, images_dir: Path) -> TypstSection:
        # calculate + build + render logic
        return super().render_ir(images_dir)
```

### 2.2 shared.adapter_protocols

Adapter protocols enable dependency inversion — subdomains depend on abstractions, never on concrete adapter implementations.

```python
# ✅ ALLOWED: Import adapter protocols
from assessment.shared.adapter_protocols import ConfigProvider, DataLoader

# ✅ ALLOWED: Use adapter protocols in service constructors
class WeibullSection(Section):
    def __init__(self, dataset: DataSetAccess, loader: DataLoader):
        self._dataset = dataset
        self._loader = loader  # receives concrete via DI, NOT direct import
```

### 2.3 shared.ir_types

IR types are the rendering contract — every subdomain produces `TypstSection` / `TypstHeading` / `TypstBody` output.

```python
# ✅ ALLOWED: Import IR types
from assessment.shared.ir_types import TypstHeading, TypstSection, TypstBody

# ✅ ALLOWED: Produce IR output
def render_ir(self, images_dir: Path) -> TypstSection:
    heading = TypstHeading(level=2, title="极端风速")
    body = TypstBody(children=[...])
    return TypstSection(heading=heading, body=body)
```

### 2.4 shared.utils

Pure, stateless utility functions used by ≥2 subdomains.

```python
# ✅ ALLOWED: Import shared utilities
from assessment.shared.utils import subsection_renderer, merge

# ✅ ALLOWED: Compose utilities in service methods
from assessment.shared.utils import subsection_renderer

class TurbulenceSection(Section):
    def render_ir(self, images_dir: Path) -> TypstSection:
        body = TypstBody(children=[])
        for subsection in self.subsections:
            rendered = subsection_renderer(subsection, self._dataset)
            body.children.extend(rendered)
        return TypstSection(heading=self._heading, body=body)
```

### 2.5 Own Subdomain Entities / Value Objects / Services

A subdomain freely imports its own internal types — these are private implementation details.

```python
# ✅ ALLOWED: Import own entities, value objects, services
from assessment.subdomains.wind_rose.entities.wind_rose_atom import (
    SingleMastWindRoseAtom,
)
from assessment.subdomains.wind_rose.entities.wind_power_rose_atom import (
    SingleMastWindPowerRoseAtom,
)
from assessment.subdomains.wind_rose.value_objects.schemas import (
    WindRoseSchema,
    WindRoseMeta,
)
```

### 2.6 Parent Adapters via Protocols (NOT Direct Import)

The ONLY way a subdomain accesses external infrastructure is through a protocol reference — never by importing the concrete adapter class.

```python
# ✅ ALLOWED: Receive adapter via protocol type hint, never direct import
from assessment.shared.protocols import DataSetAccess
from assessment.shared.adapter_protocols import DataLoader


class WindRoseSection(Section):
    _dataset: DataSetAccess  # concrete ParquetDataSet injected at construction
    _loader: DataLoader

    def __init__(self, dataset: DataSetAccess, loader: DataLoader, ...):
        self._dataset = dataset
        self._loader = loader

    def calculate(self) -> pl.DataFrame:
        # Access data through the protocol interface
        df = self._dataset.load("wind_speed", mast_id="M1")
        return self._loader.transform(df)
```

---

## 3. Forbidden Imports

### 3.1 Cross-Subdomain Imports

Physical isolation = enforced discipline. Two subdomains are in separate directories for a reason.

```python
# ❌ FORBIDDEN: Cross-subdomain import — any other subdomain
from assessment.subdomains.weibull.entities.weibull_atom import WeibullAtom
from assessment.subdomains.turbulence.services.turbulence_calculator import (
    TurbulenceCalculator,
)
from assessment.subdomains.extreme_wind.value_objects.schemas import (
    ExtremeWindSchema,
)
```

**Why**: If `wind_rose` needs data from `weibull`, the data must flow through `shared.protocols` or be wired by the parent orchestrator. Direct imports create hidden coupling that makes refactoring, testing, and decomposition impossible.

**Correct alternative**:

```python
# ✅ Parent orchestrator wires cross-subdomain data flow:
# In ReportAssemblyService (parent domain):
from assessment.subdomains.wind_rose.services import WindRoseSection
from assessment.subdomains.weibull.services import WeibullSection

wind_rose = WindRoseSection(dataset=dataset, loader=loader)
weibull = WeibullSection(dataset=dataset, loader=loader)

# wind_rose and weibull share data through the DataSetAccess protocol,
# NOT through direct imports of each other's types.
```

### 3.2 Polars/Pandas in Entities Layer

Entities are domain objects — they must not depend on data-processing frameworks.

```python
# ❌ FORBIDDEN: polars/pandas in entities layer
# File: assessment/subdomains/wind_rose/entities/wind_rose_atom.py

import polars as pl  # ❌ NEVER in entities/

@dataclass
class SingleMastWindRoseAtom:
    df: pl.DataFrame  # ❌ Polars type in entity field
```

**Why**: The entities layer is the core of the domain. Coupling it to a specific data library prevents testing with simple Python types, blocks framework migration, and violates the dependency rule (domain must not depend on infrastructure).

**Allowed**:

```python
# ✅ polars ok in services layer (not entities)
# File: assessment/subdomains/wind_rose/services/wind_rose_section.py
import polars as pl  # ✅ OK: service layer coordinates I/O

class WindRoseSection(Section):
    def calculate(self) -> pl.DataFrame:
        return self._dataset.load("wind_speed")
```

> **Note**: The existing codebase currently has `polars` in entities (e.g., `ReportAtom.df: pl.DataFrame`). This is a known gap and must be addressed in a future phase. The import contract specifies the **target state**.

### 3.3 Concrete Adapter Implementations

Never import concrete adapter classes directly — always use the protocol type.

```python
# ❌ FORBIDDEN: Direct import of concrete adapter
from assessment.adapters.parquet_dataset import ParquetDataSet
from assessment.adapters.toml_config import TomlConfig
from assessment.adapters.time_series_loader import TimeSeriesLoader


class WindRoseSection(Section):
    def __init__(self):
        # ❌ Direct instantiation of concrete adapter
        self._dataset = ParquetDataSet("/path/to/data")
        self._config = TomlConfig("config.toml")
```

**Why**: Direct adapter imports prevent testability (cannot mock adapters), create hidden infrastructure dependencies, and violate Dependency Inversion (high-level modules depend on low-level modules).

**Correct alternative**:

```python
# ✅ Adapters received via protocol at construction time
from assessment.shared.protocols import DataSetAccess
from assessment.shared.adapter_protocols import ConfigProvider


class WindRoseSection(Section):
    def __init__(self, dataset: DataSetAccess, config: ConfigProvider):
        self._dataset = dataset  # concrete injected by DI container
        self._config = config
```

### 3.4 Parent Domain Internals

Subdomains must NOT import the parent domain's internal implementation.

```python
# ❌ FORBIDDEN: Import parent domain internals
from assessment.domain.services.report_assembly import ReportAssemblyService
from assessment.domain.entities.atom_collection import AtomCollection
from assessment.domain.value_objects.report_config import ReportConfig
```

**Exception**: `shared/` and `adapters/` (outer layers) are NOT parent internals — they are contract surfaces. Importing from `assessment.domain/` (inner layer) is forbidden for subdomains.

| Can subdomain import from... | Allowed? |
|------------------------------|----------|
| `assessment.shared/*` | ✅ Yes (contract surface) |
| `assessment.adapters/*` | ✅ Via protocols only |
| `assessment.domain/*` | ❌ Never (parent internals) |
| `assessment.subdomains/other/*` | ❌ Never (peer subdomain) |

---

## 4. Parent Domain Rules

The **assessment parent domain** (`assessment/domain/`) has orchestrator privileges. It is the SOLE entity that may import from ALL subdomains.

```python
# ✅ ALLOWED: Parent domain imports from all subdomains
# File: assessment/domain/services/report_assembly.py

from assessment.shared.protocols import Section, DataSetAccess
from assessment.shared.adapter_protocols import ConfigProvider, DataLoader

# Parent orchestrator CAN import from all subdomains:
from assessment.subdomains.wind_rose.services import WindRoseSection
from assessment.subdomains.weibull.services import WeibullSection
from assessment.subdomains.turbulence.services import TurbulenceSection
from assessment.subdomains.wind_frequency.services import WindFrequencySection
from assessment.subdomains.wind_temporal.services import WindTemporalSection
from assessment.subdomains.vertical_profile.services import VerticalProfileSection
from assessment.subdomains.extreme_wind.services import ExtremeWindSection
from assessment.subdomains.representative_year.services import (
    RepresentativeYearSection,
)
from assessment.subdomains.air_density.services import AirDensitySection
from assessment.subdomains.extreme_wind.services import ExtremeWindSection


class ReportAssemblyService:
    """Sole orchestrator — calls all 10 subdomains and wires their outputs."""

    def __init__(self, dataset: DataSetAccess, config: ConfigProvider, loader: DataLoader):
        self._dataset = dataset
        self._config = config
        self._loader = loader

    def assemble(self) -> AtomCollection:
        """Wire all subdomains into a unified TypstSection tree.

        The parent doesn't compute — it composes.
        """
        sections: list[Section] = [
            WindRoseSection(self._dataset, self._loader),
            WeibullSection(self._dataset, self._loader),
            TurbulenceSection(self._dataset, self._loader, self._config),
            # ... all 10 subdomains
        ]
        return AtomCollection(sections=list(sections))
```

### Parent Domain Constraints

| Parent Can... | Parent Cannot... |
|---------------|------------------|
| ✅ Import from all subdomains | ❌ Perform subdomain-specific computation |
| ✅ Wire subdomain outputs together | ❌ Directly instantiate subdomain entities |
| ✅ Inject adapters via DI | ❌ Access subdomain private internals |
| ✅ Own `AtomCollection` + `ReportAssemblyService` | ❌ Bypass `Section` protocol when calling subdomains |

> **Principle**: The parent doesn't compute — it composes. If `ReportAssemblyService` starts calculating wind rose bins, that logic belongs in `wind_rose/`.

---

## 5. Violation Matrix

| # | Violation | Severity | Detection | Existing `.importlinter` Contract |
|---|-----------|----------|-----------|-----------------------------------|
| 1 | Subdomain imports another subdomain | **BLOCKER** | `independence` / `forbidden` | `subdomain-isolation` |
| 2 | Entities layer imports polars/pandas | **BLOCKER** | `forbidden` | `domain-purity` |
| 3 | Subdomain imports concrete adapter | **BLOCKER** | `forbidden` | Not yet — add `forbidden` contract for `cleanmast.subdomains.*` → `cleanmast.adapters` |
| 4 | Subdomain imports parent domain internals | **BLOCKER** | `forbidden` | Not yet — add `forbidden` contract for `cleanmast.subdomains.*` → `cleanmast.subdomains.assessment.domain` |
| 5 | Cross-subdomain service call | **WARNING** | Manual review | Covered by `subdomain-isolation` + `independence` |
| 6 | Direct circular import between subdomains | **BLOCKER** | `no_circular_imports` | `no-circular-imports` |
| 7 | Import from `entities/` package marker (`__init__.py`) | **WARNING** | `forbidden` | `entities-package-marker-banned` |
| 8 | Import of `cleanmast.db` or `cleanmast.infrastructure` in domain | **BLOCKER** | `forbidden` | `domain-purity` |
| 9 | CLI layer imports subdomain directly | **BLOCKER** | `forbidden` | `cli-isolation` |
| 10 | `Shared.ir_types` depends on subdomain code | **BLOCKER** | `independence` | `layer-hierarchy` layers ordering |

### Enforcement Priority

```
BLOCKER  → Must be enforced by .importlinter contract. CI fails on violation.
WARNING  → Best practice; enforced by code review. Should have .importlinter contract.
```

### Mapping to `.importlinter` Contracts

| Contract | Type | Existing? | Covers Violation(s) |
|----------|------|-----------|---------------------|
| `subdomain-isolation` | `independence` | ✅ Yes | #1, #5 |
| `domain-purity` | `forbidden` | ✅ Yes | #2, #8 |
| `layer-hierarchy` | `layers` | ✅ Yes | #10 |
| `repository-access` | `allowed` | ✅ Yes | (cross-domain repo access) |
| `no-circular-imports` | `no_circular_imports` | ✅ Yes | #6 |
| `entities-package-marker-banned` | `forbidden` | ✅ Yes | #7 |
| `cli-isolation` | `forbidden` | ✅ Yes | #9 |
| TBD: `adapter-protocol-isolation` | `forbidden` | ❌ TBD | #3 |
| TBD: `parent-internals-forbidden` | `forbidden` | ❌ TBD | #4 |

> **Note**: This specification defines the RULES; the `.importlinter` file defines the CONFIG. Adding missing contracts (#3, #4) is a separate implementation task. Do NOT encode import-linter config syntax in this document — describe the rule, not the tool.

---

## 6. Quick Reference Card

### Subdomain Developer Checklist

Before committing code in `assessment/subdomains/{name}/`:

- [ ] All external imports are from `assessment.shared.*` (protocols, ir_types, utils)
- [ ] No `import polars` or `import pandas` in `entities/` directory
- [ ] Adapter dependencies received via constructor protocol types (never directly imported)
- [ ] No imports from `assessment.subdomains/{other_subdomain}/`
- [ ] No imports from `assessment.domain/{services,entities,value_objects}/` (parent internals)
- [ ] All own imports use the subdomain's own `entities/`, `value_objects/`, `services/`
- [ ] If importing from `assessment.adapters/` — STOP. Use `shared.adapter_protocols` instead.

### Parent Domain Developer Checklist

Before committing code in `assessment/domain/`:

- [ ] May import from `assessment.subdomains/*/services/` — this is the orchestrator's privilege
- [ ] Must not import subdomain `entities/` or `value_objects/` — access via `Section` protocol
- [ ] Must not perform calculations that belong in subdomains
- [ ] `ReportAssemblyService` is the SOLE entry point for orchestrating all 10 subdomains

---

## 7. References

| Reference | Location |
|-----------|----------|
| Main ADR | `adr/ddd-s-003-subdomain-deepening.md` |
| Design Rationale | `.sisyphus/design-rationale.md` |
| Existing Contracts | `packages/cleanmast/.importlinter` |
| Subdomain Layout | `adr/structure-001-subdomain-layout.md` |
| Context Maps | `adr/ddd-s-002-context-maps.md` |
