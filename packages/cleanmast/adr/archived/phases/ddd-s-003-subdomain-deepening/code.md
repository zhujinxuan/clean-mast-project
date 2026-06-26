# Phase: Code - Subdomain Deepening

## When to Use

Load this file during the implementation phase when creating nested subdomains, shared protocols, and adapter implementations.

## Related ADR

- Main ADR: `adr/ddd-s-003-subdomain-deepening.md` (follow constraints strictly)

## Implementation Guidance

### Section Protocol Implementation Pattern

Each subdomain exposes exactly one public service class that implements the `Section` protocol. This service combines calculation, atom building, and IR rendering:

```python
# subdomains/wind_rose/services/wind_rose_section.py
from typing import Protocol

from assessment.shared.ir_types import TypstSection
from assessment.shared.protocols import DataSetAccess, ReportAtom


class Section(Protocol):
    """Protocol for report sections."""

    def render_ir(self) -> TypstSection:
        """Render this section to Typst IR."""
        ...


class WindRoseSection:
    """Wind rose section: calculates, builds atoms, renders IR."""

    def __init__(
        self,
        dataset: DataSetAccess,
        mast_name: str,
    ) -> None:
        self._dataset = dataset
        self._mast_name = mast_name
        self._atoms: list[ReportAtom] = []

    def calculate(self) -> None:
        """Fetch data and compute wind rose frequencies."""
        df = self._dataset.load(self._mast_name)
        # ... compute 16-sector frequencies ...
        self._atoms = [WindRoseAtom(data=df)]

    def render_ir(self) -> TypstSection:
        """Render section to Typst IR."""
        if not self._atoms:
            self.calculate()
        return TypstSection(
            heading=f"Wind Rose — {self._mast_name}",
            body=[atom.render_ir() for atom in self._atoms],
        )
```

### shared/ Protocol Definition Pattern

Define protocols in `shared/protocols/` using Python `Protocol` classes. These are the ONLY types subdomains may import from outside their own directory:

```python
# assessment/shared/protocols/section.py
from typing import Protocol

from assessment.shared.ir_types import TypstSection


class Section(Protocol):
    """Protocol for all report sections across subdomains."""

    def render_ir(self) -> TypstSection:
        """Render this section to Typst IR tree."""
        ...
```

```python
# assessment/shared/protocols/dataset_access.py
from typing import Protocol

import polars as pl


class DataSetAccess(Protocol):
    """Protocol for dataset loading. Implemented by adapters."""

    def load(self, key: str) -> pl.DataFrame:
        """Load dataset by key."""
        ...
```

### ReportAssemblyService Orchestration Pattern

The parent domain orchestrates subdomains through a single service. It owns `AtomCollection` and wires subdomain outputs into the final report:

```python
# assessment/domain/services/report_assembly.py
from assessment.shared.protocols import Section
from assessment.subdomains.wind_rose.services.wind_rose_section import WindRoseSection
from assessment.subdomains.weibull.services.weibull_section import WeibullSection


class ReportAssemblyService:
    """Orchestrates all subdomain services into a unified report."""

    def __init__(self, dataset: DataSetAccess) -> None:
        self._dataset = dataset

    def build_report(self, mast_names: list[str]) -> list[Section]:
        """Build all report sections for given masts."""
        sections: list[Section] = []
        for mast in mast_names:
            sections.append(WindRoseSection(self._dataset, mast))
            sections.append(WeibullSection(self._dataset, mast))
            # ... more subdomains ...
        return sections
```

### Import Patterns

**Correct** — Via shared protocols only:

```python
# ✅ Correct: subdomain imports from shared/
from assessment.shared.protocols import Section, DataSetAccess
from assessment.shared.ir_types import TypstSection
from assessment.shared.utils import subsection_renderer

# ✅ Correct: parent domain imports subdomains
from assessment.subdomains.wind_rose.services.wind_rose_section import WindRoseSection
```

**Incorrect** — Cross-subdomain or concrete adapter imports:

```python
# ❌ NEVER: cross-subdomain concrete import
from ..weibull.entities.weibull_atom import WeibullAtom

# ❌ NEVER: concrete adapter import in subdomain
from ...adapters.parquet_dataset import ParquetDataSet  # Use DataSetAccess protocol

# ❌ NEVER: importing another subdomain's service
from assessment.subdomains.turbulence.services.turbulence_section import TurbulenceSection
```

### Import Rule Matrix

| From | To shared/ | To parent adapters/ | To own entities/ | To other subdomains |
|------|-----------|--------------------|--------------------|--------------------|
| subdomain | ✅ (protocols) | ✅ (via protocols) | ✅ | ❌ |
| parent domain | ✅ | ✅ | ✅ | ✅ (orchestrates all) |

## Checklist

Before marking implementation complete, verify:
- [ ] Each subdomain has exactly one public service implementing `Section`
- [ ] `shared/` contains only Protocols, IR types, and pure utils
- [ ] `adapters/` contains only concrete implementations of shared protocols
- [ ] No subdomain imports another subdomain's concrete types
- [ ] No subdomain imports from `adapters/` directly
- [ ] `ReportAssemblyService` wires subdomains without domain logic
- [ ] Per-domain ADRs follow Role → Concrete Structure → Principles format
- [ ] Per-domain ADRs are under ~40 lines
