"""Summary turbulence intensity report atom."""

from pathlib import Path
from typing import cast

import polars as pl
from typing_extensions import override

from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
def _select_interested_heights(
    heights: list[float],
    min_height: float = 120.0,
    max_height: float = 160.0,
    min_count: int = 2,
) -> list[float]:
    """Select heights within the target range, falling back to top heights.

    Returns all heights where ``min_height <= h <= max_height``, sorted
    ascending. If fewer than ``min_count`` heights fall within the range,
    returns the ``min_count`` highest heights from the full set.
    """
    filtered = [h for h in heights if min_height <= h <= max_height]
    filtered.sort()

    if len(filtered) >= min_count:
        return filtered

    sorted_heights = sorted(heights, reverse=True)
    fallback = sorted_heights[:min_count]
    fallback.sort()
    return fallback


from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.subdomains.turbulence.model.report_meta import (
    TurbulenceAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.schemas import (
    TurbulenceSchema,
)


# ── IEC reference constants/helpers (duplicated to avoid model→compute import) ─

_IEC_CATEGORIES: dict[str, float] = {
    "A+": 0.18,
    "A": 0.16,
    "B": 0.14,
    "C": 0.12,
}


def _compute_iec_ti(wind_speed: float, i_ref: float) -> float | None:
    """Compute IEC reference turbulence intensity.

    TI_IEC = I_ref * (0.75 + 5.6/V)
    Returns None for wind_speed ≤ 0.
    """
    if wind_speed <= 0:
        return None

    return i_ref * (0.75 + 5.6 / wind_speed)


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

        Columns: 高度(m) | 风速范围 | 平均湍流强度 | 代表湍流强度(P90) | 湍流强度标准差
        Rows per interested height: >3 m/s, 14.5-16.5 m/s, 9.5-10.5 m/s
        """
        interested_heights = _select_interested_heights(
            self.df["height"].unique().to_list()
        )
        filtered_df = self.df.filter(pl.col("height").is_in(interested_heights))

        rows: list[list[str]] = []
        for height in sorted(interested_heights):
            height_df = filtered_df.filter(pl.col("height") == height)
            marker = cast(str | None, height_df["interpolation_marker"].first())
            height_display = get_height_display_name(height, marker or "")

            ranges = [
                (
                    ">3 m/s",
                    height_df.filter(pl.col("wind_speed_bin") > 3),
                ),
                (
                    "14.5-16.5 m/s",
                    height_df.filter(
                        (pl.col("wind_speed_bin") >= 14)
                        & (pl.col("wind_speed_bin") <= 16)
                    ),
                ),
                (
                    "9.5-10.5 m/s",
                    height_df.filter(
                        (pl.col("wind_speed_bin") >= 9)
                        & (pl.col("wind_speed_bin") <= 10)
                    ),
                ),
            ]

            for range_label, range_df in ranges:
                if len(range_df) > 0:
                    mean_ti = cast(float, range_df["mean_ti"].mean())
                    rep_ti = cast(float, range_df["representative_ti"].mean())
                    std_ti = cast(float, range_df["std_ti"].mean())
                    rows.append(
                        [
                            height_display,
                            range_label,
                            f"{mean_ti:.3f}",
                            f"{rep_ti:.3f}",
                            f"{std_ti:.3f}",
                        ]
                    )
                else:
                    rows.append(
                        [height_display, range_label, "-", "-", "-"]
                    )

        return TypstTable(
            headers=[
                "高度(m)",
                "风速范围",
                "平均湍流强度",
                "代表湍流强度(P90)",
                "湍流强度标准差",
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
        interested_heights = _select_interested_heights(
            self.df["height"].unique().to_list()
        )
        filtered_df = self.df.filter(pl.col("height").is_in(interested_heights))

        height_strs: list[str] = []
        rep_ti_vals: list[float] = []

        for height in sorted(interested_heights):
            height_df = filtered_df.filter(pl.col("height") == height)
            range_df = height_df.filter(
                (pl.col("wind_speed_bin") >= 14) & (pl.col("wind_speed_bin") <= 16)
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

        # IEC reference TI at 15 m/s for each category
        # _compute_iec_ti(15.0, ...) always returns float (15.0 > 0)
        ti_a_plus = _compute_iec_ti(15.0, _IEC_CATEGORIES["A+"]) or 0.0
        ti_a = _compute_iec_ti(15.0, _IEC_CATEGORIES["A"]) or 0.0
        ti_b = _compute_iec_ti(15.0, _IEC_CATEGORIES["B"]) or 0.0
        if mean_rep_ti > ti_a_plus:
            closest_cat = "A+"
        elif mean_rep_ti > ti_a:
            closest_cat = "A"
        elif mean_rep_ti > ti_b:
            closest_cat = "B"
        else:
            closest_cat = "C"

        height_part = ", ".join(height_strs)
        rep_ti_part = ", ".join(f"{v:.3f}" for v in rep_ti_vals)

        text = (
            f"分析 {self.meta.mast_name} 测风塔，在 {height_part} "
            f"15m/s 附近风速区间 P90 代表性湍流强度为 {rep_ti_part}；"
            f"根据 15m/s 附近风速的代表湍流强度，暂定为 IEC {closest_cat} 类。"
        )
        return [TypstParagraph(text=text)]
