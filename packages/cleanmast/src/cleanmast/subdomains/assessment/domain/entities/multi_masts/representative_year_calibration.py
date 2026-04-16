"""Multi-mast representative year calibration atom.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import TypstParagraph, TypstTable
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.report_meta import (
    MultiMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.schemas import (
    MultiMastRepYearCalibrationSchema,
)


@dataclass
class MultiMastRepYearCalibrationAtom(
    ReportAtom[MultiMastRepYearCalibrationSchema, MultiMastMeta]
):
    """Renders multi-mast representative year calibration table.

    - Table: 测风代表年range, mastname, era5name, 30年气候平均基准ERA5风速,
             测风代表年ERA5风速, 距平, 是否需要订正
    - Image: No image (returns empty Path)
    - Summary: Chinese description of representative year calibration
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "各测风塔代表年订正结果"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render multi-mast representative year calibration table."""
        rows: list[list[str]] = []

        for row in self.df.iter_rows(named=True):
            year_range = cast(str, row["year_range"])
            mast_name = cast(str, row["mast_name"])
            era5_name = cast(str, row["era5_name"])
            climatology_mean_ws = cast(float, row["climatology_mean_ws"])
            rep_year_mean_ws = cast(float, row["rep_year_mean_ws"])
            anomaly_percent = cast(float, row["anomaly_percent"])
            needs_correction = cast(bool, row["needs_correction"])

            climatology_str = f"{climatology_mean_ws:.2f} (m/s)"
            rep_year_str = f"{rep_year_mean_ws:.2f} (m/s)"
            anomaly_str = f"{anomaly_percent:.2f}%"
            correction_str = "是" if needs_correction else "否"

            rows.append(
                [
                    year_range,
                    mast_name,
                    era5_name,
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
                "30年气候平均基准ERA5风速",
                "测风代表年ERA5风速",
                "距平",
                "是否需要订正",
            ],
            data=rows,
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for representative year calibration table."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary explaining representative year calibration."""
        text = (
            "代表年订正通过中尺度数据将测风年份的风速资料调整至长期气候平均水平，"
            "以反映风电场的长期风资源特征。"
            "是否需要订正取决于测风代表年与30年气候平均基准期的风速偏差是否超过2%。"
        )
        return [TypstParagraph(text=text)]
