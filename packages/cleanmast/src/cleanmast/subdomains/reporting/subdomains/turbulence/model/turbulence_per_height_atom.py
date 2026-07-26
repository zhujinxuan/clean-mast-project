"""Single-height turbulence intensity report atom."""

from pathlib import Path

import polars as pl
from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.turbulence.model.report_meta import (
    TurbulenceAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.schemas import (
    TurbulenceSchema,
)

# ── SingleMastTurbulencePerHeightAtom ────────────────────────────────────────


class SingleMastTurbulencePerHeightAtom(ReportAtom[TurbulenceSchema, TurbulenceAtomMeta]):
    """Renders a turbulence intensity table for a single assigned height.

    - Table: One TypstTable for the atom's height with wind speed bin statistics
    - Image: None (returns empty Path)
    - Summary: None (returns empty list)
    """

    height: float = 0.0

    @classmethod
    def create_with_height(
        cls,
        schema: type[TurbulenceSchema],
        df: pl.DataFrame,
        meta: TurbulenceAtomMeta,
        height: float,
    ) -> "SingleMastTurbulencePerHeightAtom":
        """Factory: validates, filters to a single height, and returns typed atom."""
        validated = schema.validate(df, cast=True)
        height_df = validated.filter(pl.col("height") == height)
        instance = cls(df=height_df, schema=schema, meta=meta)
        object.__setattr__(instance, "height", height)
        return instance

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} {int(self.height)}m 各风速区间湍流强度统计"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render one TypstTable for the atom's assigned height.

        The table contains wind speed bin statistics sorted by wind_speed_bin
        ascending. Returns None if there is no data for this height.
        """
        if self.df.is_empty():
            return None

        height_data = self.df.sort("wind_speed_bin")

        rows: list[list[str]] = []
        for row in height_data.iter_rows(named=True):
            wind_speed_bin = row["wind_speed_bin"]
            rows.append([
                f"{wind_speed_bin}-{wind_speed_bin + 1}",
                f"{row['mean_ti']:.3f}",
                f"{row['std_ti']:.3f}",
                f"{row['representative_ti']:.3f}",
                row["iec_category"],
                f"{row['count']}",
            ])

        return TypstTable(
            headers=[
                "风速区间 (m/s)",
                "平均湍流强度",
                "湍流强度标准差",
                "代表湍流强度(P90)",
                "IEC类别",
                "数据点数",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Return an empty Path (no image for this atom)."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Return an empty list (no summary text for this atom)."""
        return []
