"""Per-mast 16-sector representative year calibration table atom.

Compliance: Subdomain layout | Entity | Atom Pattern
"""

from __future__ import annotations

from pathlib import Path

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.representative_year.model.report_meta import (
    RepYearSectorAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.schemas import (
    RepYearSectorSchema,
)

SECTOR_NAMES: list[str] = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]

TABLE_HEADERS: list[str] = [
    "方向",
    "参证风速气候平均",
    "参证风速代表年平均",
    "气候−代表年(m/s)",
    "斜率",
    "截距",
    "订正量(m/s)",
    "数据点",
]


def _format_value(value: float | None, precision: int = 2) -> str:
    """Format a float value to the given precision, or return "N/A" if None."""
    if value is None:
        return "N/A"
    return f"{value:.{precision}f}"


class RepYearSectorTableAtom(ReportAtom[RepYearSectorSchema, RepYearSectorAtomMeta]):
    """Renders per-mast 16-sector representative year calibration statistics table.

    - Table: 16-sector statistics with headers in Chinese
    - Image: None (returns empty Path)
    - Summary: None (returns empty list)
    """

    @property
    @override
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} ({int(self.meta.height)}m) ← {self.meta.meso_name} 16方向扇区分析"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render per-mast 16-sector calibration statistics table.

        Sorted by sector_index (1–16, clockwise from N). Sectors with zero
        data points show "N/A" for computed columns.
        """
        table_df = self.df.sort("sector_index")

        data: list[list[str]] = []
        for row in table_df.iter_rows(named=True):
            dp = row["data_points"]
            has_data = dp is not None and dp > 0

            row_data = [
                str(row["sector"]),
                _format_value(row["climatology_mean"], 2) if has_data else "N/A",
                _format_value(row["rep_year_mean"], 2) if has_data else "N/A",
                _format_value(row["meso_difference"], 2) if has_data else "N/A",
                _format_value(row["slope"], 4) if has_data else "N/A",
                _format_value(row["intercept"], 4) if has_data else "N/A",
                _format_value(row["adjustment"], 2) if has_data else "N/A",
                str(dp) if dp is not None else "0",
            ]
            data.append(row_data)

        return TypstTable(
            headers=list(TABLE_HEADERS),
            data=data,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for sector table atom."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """No summary for sector table atom."""
        return []
