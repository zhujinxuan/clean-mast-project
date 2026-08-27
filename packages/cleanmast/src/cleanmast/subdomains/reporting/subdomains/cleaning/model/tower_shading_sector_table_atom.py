"""Per-height sector comparison table atom for 2.3.4 塔影效应处理."""

from pathlib import Path

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    TowerShadingSectorTableAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    TowerShadingSectorSchema,
)


def _format_mps(value: float | None) -> str:
    """Wind speed / signed delta in m/s, 2 decimals; N/A when null."""
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def _format_pct(value: float | None) -> str:
    """Signed relative change in %, 1 decimal; N/A when null."""
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}"


def _height_label(height: float) -> str:
    """Height as integer when whole, one decimal otherwise (Julia format)."""
    if height == round(height):
        return str(int(round(height)))
    return f"{height:.1f}"


class TowerShadingSectorTableAtom(
    ReportAtom[TowerShadingSectorSchema, TowerShadingSectorTableAtomMeta]
):
    """Renders the per-height 修正前后分扇区风速对比 table (2.3.4).

    Rows: observed 16-sector bins sorted clockwise from N, then one
    总体平均(加权) row weighted by per-sector sample counts. Deltas are
    signed 修正后 − 修正前. Table only — no summary, no image.
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return (
            f"{self.meta.mast_name} {_height_label(self.meta.height)}m "
            "塔影修正前后分扇区风速对比"
        )

    def _headers(self) -> list[str]:
        l1, l2 = self.meta.channel_1_label, self.meta.channel_2_label
        return [
            "扇区",
            "样本数",
            f"{l1}修正前均值(m/s)",
            f"{l2}修正前均值(m/s)",
            "修正后均值(m/s)",
            f"{l1}差值(m/s)",
            f"{l2}差值(m/s)",
            f"{l1}百分比(%)",
            f"{l2}百分比(%)",
        ]

    @override
    def renderTable(self) -> TypstTable | None:
        data: list[list[str]] = []
        for row in self.df.iter_rows(named=True):
            data.append([
                str(row["sector"]),
                str(row["data_points"]),
                _format_mps(row["mean_before_1"]),
                _format_mps(row["mean_before_2"]),
                _format_mps(row["mean_after"]),
                _format_mps(row["delta_1"]),
                _format_mps(row["delta_2"]),
                _format_pct(row["pct_1"]),
                _format_pct(row["pct_2"]),
            ])
        if not data:
            return None
        return TypstTable(
            headers=self._headers(),
            data=data,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []
