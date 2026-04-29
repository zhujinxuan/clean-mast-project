"""Turbulence sector atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-report-atoms
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TurbulenceSectorSchema,
)


@dataclass
class SingleMastTurbulenceSectorAtom(ReportAtom[TurbulenceSectorSchema, SingleMastMeta]):
    """Renders turbulence intensity by direction sector for a single mast.

    - Table: All heights with sector TI values (mean and representative)
    - Image: Polar bar chart showing TI by sector (wind rose style)
    - Summary: Chinese description of dominant turbulent directions
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} 按风向扇区湍流强度图"

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 按风向扇区湍流强度表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as Typst table: 风向 | 高度 | 平均TI | 代表TI | IEC类别."""
        rows = []
        sorted_df = self.df.sort(["sector", "height"])

        for row in sorted_df.iter_rows(named=True):
            sector_name = row["sector_name"]
            height_display = get_height_display_name(
                row["height"], row.get("interpolation_marker", "")
            )
            mean_ti = row["mean_ti"] * 100
            rep_ti = row["representative_ti"] * 100
            iec_category = row["iec_category"]

            rows.append([sector_name, height_display, f"{mean_ti:.2f}", f"{rep_ti:.2f}", iec_category])

        return TypstTable(
            headers=["风向", "高度", "平均TI(%)", "代表TI(%)", "IEC类别"],
            data=rows,
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate polar chart with >100m heights, export to PNG."""
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"turbulencesector_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        plot_df = self.df.filter(pl.col("height") > 100)
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )
        plot_df = plot_df.with_columns(
            (pl.col("mean_ti") * 100).alias("mean_ti_pct"),
            (pl.col("representative_ti") * 100).alias("rep_ti_pct"),
        )

        plot_df_pd = plot_df.to_pandas()

        chart = alt.Chart(plot_df_pd).mark_arc(stroke="white").encode(
            theta=alt.Theta("sector:O", title="风向", sort=None),
            radius=alt.Radius(
                "mean_ti_pct:Q",
                title="湍流强度TI(%)",
                scale=alt.Scale(zero=True),
            ),
            radius2=alt.datum(0),
            color=alt.Color("height_display:N", title="高度"),
            tooltip=[
                "sector_name",
                "height_display",
                "mean_ti_pct",
                "rep_ti_pct",
                "iec_category",
            ],
        ).properties(
            title=f"{self.meta.mast_name} 湍流强度玫瑰图",
            width=500,
            height=500,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of dominant turbulent directions."""
        high_df = self.df.filter(pl.col("height") > 100)
        heights = (
            high_df.select(["height", "interpolation_marker"])
            .unique()
            .sort("height")
        )
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"])
            for row in heights.iter_rows(named=True)
        ]

        dominant = (
            high_df.group_by("sector_name")
            .agg(pl.col("mean_ti").mean().alias("avg_ti"))
            .sort("avg_ti", descending=True)
            .head(3)
        )
        dominant_directions = [
            row["sector_name"] for row in dominant.iter_rows(named=True)
        ]

        _ti_val = cast(float | None, high_df["mean_ti"].mean())
        avg_ti = float(_ti_val or 0)

        text = (
            f"{self.meta.mast_name}测风塔湍流强度玫瑰图分析。"
            f"图表显示{', '.join(height_strs)}高度的湍流强度分布，"
            f"主导湍流方向为{'、'.join(dominant_directions)}，"
            f"平均湍流强度为{avg_ti * 100:.2f}%，"
            f"为风机选型与载荷计算提供参考依据。"
        )
        return [TypstParagraph(text=text)]
