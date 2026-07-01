"""All-mast representative year calibration summary atom.

Compliance: Subdomain layout | Entity | Atom Pattern
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.representative_year.model.report_meta import (
    RepresentativeYearAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.schemas import (
    RepYearSummarySchema,
)


class RepYearSummaryAtom(ReportAtom[RepYearSummarySchema, RepresentativeYearAtomMeta]):
    """Renders the all-mast representative year calibration summary table.

    - Table: One row per mast, with climatology vs rep-year comparison
    - Image: No image (table only)
    - Summary: Chinese description of calibration methodology
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "各测风塔代表年校正结果"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render all-mast representative year calibration summary table."""
        rows: list[list[str]] = []

        for row in self.df.iter_rows(named=True):
            year_range = cast(str, row["year_range"])
            mast_name = cast(str, row["mast_name"])
            meso_name = cast(str, row["meso_name"])
            climatology_mean_ws = cast(float, row["climatology_mean_ws"])
            rep_year_mean_ws = cast(float, row["rep_year_mean_ws"])
            anomaly_percent = cast(float, row["anomaly_percent"])
            needs_correction = cast(bool, row["needs_correction"])

            climatology_str = f"{climatology_mean_ws:.2f} (m/s)"
            rep_year_str = f"{rep_year_mean_ws:.2f} (m/s)"
            anomaly_str = f"{anomaly_percent:+.2f}%"
            correction_str = "是" if needs_correction else "否"

            rows.append(
                [
                    year_range,
                    mast_name,
                    meso_name,
                    climatology_str,
                    rep_year_str,
                    anomaly_str,
                    correction_str,
                ]
            )

        return TypstTable(
            headers=[
                "测风代表年",
                "测风塔",
                "基准数据源",
                "参证风速气候平均",
                "参证风速代表年平均",
                "距平(%)",
                "是否需要订正",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for summary table."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary explaining representative year calibration."""
        n_pairs = len(self.df)
        text = (
            f"本报告分析了{n_pairs}对测风塔-中尺度配对的代表年校正效果，"
            "通过对比测风年份与30年长期气候平均的风速差异，"
            "判断各测风塔是否需要进行代表年订正。"
            "当测风代表年与30年气候平均基准期的风速偏差超过2%时，"
            "需要进行代表年订正，以准确反映风电场的长期风资源特征。"
        )
        return [TypstParagraph(text=text)]
