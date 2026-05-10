"""Flat report configuration model.

ADR-GUARDRAILS: ddd-vo-001-value-objects, types-001-strict-type-safety
Compliance: Value Object ✓ | Strict types ✓ | Validation ✓
"""

from __future__ import annotations

from pathlib import Path

import tomli
import tomli_w
from pydantic import BaseModel, model_validator

from .dataset_config import DatasetConfig
from .flat_subsection_config import FlatSubsectionConfig
from .tree_builder import SectionNode, build_section_tree


class FlatReportConfig(BaseModel):
    """Flat (non-recursive) report configuration.

    Uses flat arrays for datasets and subsections, with hierarchy
    represented by dot-separated indices.
    """

    datasets: list[DatasetConfig]
    subsections: list[FlatSubsectionConfig]

    @model_validator(mode="after")
    def validate_datasets(self) -> "FlatReportConfig":
        """Validate dataset names are unique and subsection references exist."""
        # Validate unique dataset names
        names = [ds.name for ds in self.datasets]
        seen = set()
        for name in names:
            if name in seen:
                raise ValueError(f"Duplicate dataset name '{name}' in catalog")
            seen.add(name)

        # Validate subsection dataset references
        catalog = {ds.name for ds in self.datasets}
        for sub in self.subsections:
            if sub.datasets is not None:
                for ds_name in sub.datasets:
                    if ds_name not in catalog:
                        raise ValueError(
                            f"Subsection {sub.index} references unknown dataset '{ds_name}'"
                        )

        return self

    @property
    def tree(self) -> list[SectionNode]:
        """Build hierarchical section tree from flat subsections."""
        return build_section_tree(self.subsections)

    @classmethod
    def from_toml(cls, path: Path) -> "FlatReportConfig":
        """Load config from TOML file.

        Expected TOML format:
        [[datasets]]
        name = "repyear"
        [[datasets.masts]]
        name = "M6002"
        air_density = 1.225
        [datasets.masts.input]
        data = "./data/repyear.parquet"

        [[subsections]]
        index = "1"
        type = "wind_rose"
        datasets = ["repyear"]
        """
        with open(path, "rb") as f:
            data = tomli.load(f)

        return cls.model_validate(data)

    def to_toml(self, path: Path) -> None:
        """Serialize config to TOML file."""
        data = {
            "datasets": [ds.model_dump(exclude_none=True) for ds in self.datasets],
            "subsections": [sub.model_dump(exclude_none=True) for sub in self.subsections],
        }
        toml_str = tomli_w.dumps(data)
        path.write_text(toml_str, encoding="utf-8")
