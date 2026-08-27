"""Per-mast height correlation-matrix table atom (2.3.5 同塔插补)."""

from __future__ import annotations

from pathlib import Path

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    CorrelationMatrixAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    CorrelationLongSchema,
)

_MISSING = "—"


def _format_r(value: float | None) -> str:
    """Correlation coefficient at 3 decimals; em-dash when uncomputable."""
    if value is None:
        return _MISSING
    return f"{value:.3f}"


class CorrelationMatrixAtom(
    ReportAtom[CorrelationLongSchema, CorrelationMatrixAtomMeta]
):
    """Renders the heights × heights Pearson correlation matrix.

    - Table: full square, rows and columns in ``meta.labels`` order,
      diagonal 1.000, em-dash for uncomputable pairs
    - Image: none
    - Summary: none
    """

    @property
    @override
    def default_table_caption(self) -> str:
        return self.meta.caption

    @override
    def renderTable(self) -> TypstTable:
        r_lookup: dict[tuple[str, str], float | None] = {
            (row["x_label"], row["y_label"]): row["r"]
            for row in self.df.iter_rows(named=True)
        }
        labels = self.meta.labels
        data: list[list[str]] = []
        for y_label in labels:
            row = [y_label]
            for x_label in labels:
                row.append(_format_r(r_lookup.get((x_label, y_label))))
            data.append(row)
        return TypstTable(
            headers=["高度", *labels],
            data=data,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image for the correlation-matrix atom."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []
