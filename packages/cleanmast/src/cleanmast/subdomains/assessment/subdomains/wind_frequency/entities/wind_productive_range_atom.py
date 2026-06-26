"""Wind productive range atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from typing_extensions import override

from ....shared.protocols.report_atom import ReportAtom
from ....shared.ir_types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from ..value_objects.schemas import (
    WindFrequencySchema,
)


def _height_label(height: float, marker: str | None) -> str:
    base = f"{int(height)}m"
    if marker:
        return f"{base}({marker})"
    return base


@dataclass
class SingleMastWindProductiveRangeAtom(ReportAtom[WindFrequencySchema, SingleMastMeta]):
    """Renders productive wind range (3~25 m/s) summary per interested height.

    - Table: One row per interested height with summed occurrence_hours and power_hours
    - Image: No image (returns empty Path)
    - Summary: Brief Chinese description
    """

    @property
    def default_image_caption(self) -> None:
        return None

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 有效风速范围(3~25m/s)统计表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as Typst table with 3~25 m/s productive range summary."""
        productive_df = self.df.filter(
            (pl.col("bin_start") >= 3.0)
            & (pl.col("bin_end") <= 25.0)
            & (pl.col("height") > 120.0)
            & (pl.col("height") <= 160.0)
        )

        summary_df = productive_df.group_by(["height", "interpolation_marker"]).agg(
            [
                pl.col("occurrence_hours").sum().alias("occurrence_hours_sum"),
                pl.col("power_hours").sum().alias("power_hours_sum"),
            ]
        ).sort("height")

        headers = ["高度(m)", "风速出现小时数", "风能出现小时数"]
        data: list[list[str]] = []
        for row in summary_df.iter_rows(named=True):
            height_display = _height_label(
                row["height"], row["interpolation_marker"]
            )
            occurrence_hours = int(round(row["occurrence_hours_sum"]))
            power_hours = int(round(row["power_hours_sum"]))
            data.append([height_display, f"{occurrence_hours}", f"{power_hours}"])

        return TypstTable(headers=headers, data=data, caption=self.default_table_caption)

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for wind productive range table."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """No standalone summary (table-only atom)."""
        return []
