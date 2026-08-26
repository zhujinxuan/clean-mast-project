"""Summary turbulence intensity report atom."""

from pathlib import Path
from typing import cast

import polars as pl
from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.turbulence.model.iec import (
    classify_iec_category,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.report_meta import (
    TurbulenceAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.schemas import (
    TurbulenceSchema,
)

# ── SingleMastTurbulenceSummaryAtom ──────────────────────────────────────────


class SingleMastTurbulenceSummaryAtom(ReportAtom[TurbulenceSchema, TurbulenceAtomMeta]):
    """Renders turbulence intensity summary table per height.

    - Table: Height, wind speed range, mean TI, representative TI, std TI
    - Image: No image for summary (returns empty Path)
    - Summary: Chinese description of turbulence classification results
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 湍流强度统计表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as Typst table with turbulence summary by height.

        Columns: 高度(m) | 风速范围 | 平均湍流强度 | 代表湍流强度(P90) | 湍流强度标准差 | 数据点数
        One row per interested height: the 14.5-15.5 m/s classification band
        (bins 14 and 15, bin-center membership convention).
        """
        interested_heights = self.meta.interested_heights
        filtered_df = self.df.filter(pl.col("height").is_in(interested_heights))

        rows: list[list[str]] = []
        for height in sorted(interested_heights):
            height_df = filtered_df.filter(pl.col("height") == height)
            marker = cast(str | None, height_df["interpolation_marker"].first())
            height_display = get_height_display_name(height, marker or "")

            band_df = height_df.filter(
                (pl.col("wind_speed_bin") >= 14)
                & (pl.col("wind_speed_bin") <= 15)
            )
            if len(band_df) > 0:
                mean_ti = cast(float, band_df["mean_ti"].mean())
                rep_ti = cast(float, band_df["representative_ti"].mean())
                std_ti = cast(float, band_df["std_ti"].mean())
                count = cast(int, band_df["count"].sum())
                rows.append(
                    [
                        height_display,
                        "14.5-15.5 m/s",
                        f"{mean_ti:.3f}",
                        f"{rep_ti:.3f}",
                        f"{std_ti:.3f}",
                        str(count),
                    ]
                )
            else:
                rows.append(
                    [height_display, "14.5-15.5 m/s", "-", "-", "-", "-"]
                )

        return TypstTable(
            headers=[
                "高度(m)",
                "风速范围",
                "平均湍流强度",
                "代表湍流强度(P90)",
                "湍流强度标准差",
                "数据点数",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for turbulence summary.

        Turbulence summary is displayed as a table only.
        Returns a placeholder Path.
        """
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of turbulence intensity classification results.

        Text format:
        分析 {mast_name} 测风塔，在 {h1}, {h2} ... 15m/s 附近风速区间
        P90 代表性湍流强度为 {v1}, {v2} ...；
        根据 15m/s 附近风速的代表湍流强度，暂定为 IEC {cat} 类。
        """
        interested_heights = self.meta.interested_heights
        filtered_df = self.df.filter(pl.col("height").is_in(interested_heights))

        height_strs: list[str] = []
        rep_ti_vals: list[float] = []

        for height in sorted(interested_heights):
            height_df = filtered_df.filter(pl.col("height") == height)
            range_df = height_df.filter(
                (pl.col("wind_speed_bin") >= 14) & (pl.col("wind_speed_bin") <= 15)
            )
            if len(range_df) > 0:
                marker = cast(str | None, height_df["interpolation_marker"].first())
                height_display = get_height_display_name(height, marker or "")
                rep_ti = cast(float, range_df["representative_ti"].mean())
                height_strs.append(height_display)
                rep_ti_vals.append(rep_ti)

        if not height_strs:
            return [
                TypstParagraph(
                    text=f"{self.meta.mast_name}测风塔暂无15m/s附近风速区间的有效湍流强度数据。"
                )
            ]

        mean_rep_ti = sum(rep_ti_vals) / len(rep_ti_vals)

        # Band-membership classification at 15 m/s via the shared classifier —
        # consistent with the per-bin tables and the IEC band chart.
        iec_category = classify_iec_category(mean_rep_ti, 15.0)

        height_part = ", ".join(height_strs)
        rep_ti_part = ", ".join(f"{v:.3f}" for v in rep_ti_vals)

        text = (
            f"分析 {self.meta.mast_name} 测风塔，在 {height_part} "
            f"15m/s 附近风速区间 P90 代表性湍流强度为 {rep_ti_part}；"
            f"根据 15m/s 附近风速的代表湍流强度，暂定为 IEC {iec_category} 类。"
        )
        return [TypstParagraph(text=text)]
