"""Wind shear exponent matrix atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import altair as alt
import numpy as np
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from ....shared.protocols.report_atom import ReportAtom
from ....shared.ir_types import (
    TypstParagraph,
    TypstTable,
)
from ..value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)


@dataclass
class SingleMastWindShearExponentAtom(ReportAtom[WindShearSchema, SingleMastMeta]):
    """Renders wind shear exponent matrix between height levels.

    - Table: Square matrix showing shear exponent (α) between height pairs
    - Image: Log-log vertical profile chart
    - Summary: Chinese description of shear exponent results
    """

    profile_df: pl.DataFrame = field(default_factory=pl.DataFrame)

    @classmethod
    def create(  # type: ignore
        cls,
        profile_schema: type[VerticalProfileSchema],
        profile_df: pl.DataFrame,
        shear_schema: type[WindShearSchema],
        shear_df: pl.DataFrame,
        meta: SingleMastMeta,
    ) -> Self:
        validated_profile = profile_schema.validate(profile_df, cast=True)
        validated_shear = shear_schema.validate(shear_df, cast=True)
        instance = cls.__new__(cls)
        instance.profile_df = validated_profile
        instance.df = validated_shear
        instance.schema = shear_schema
        instance.meta = meta
        instance._df_hashkey = None
        return instance

    @property
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} 垂直风廓线图"

    @property
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 风切变指数统计表"

    @override
    def renderTable(self) -> TypstTable | None:
        heights_from = self.df.select("from_height").unique().sort("from_height")
        heights_to = self.df.select("to_height").unique().sort("to_height")

        all_heights = sorted(set(
            heights_from["from_height"].to_list() +
            heights_to["to_height"].to_list()
        ))

        alpha_lookup: dict[tuple[float, float], float] = {}
        for row in self.df.iter_rows(named=True):
            key = (row["from_height"], row["to_height"])
            alpha_lookup[key] = row["alpha_mean"]

        wind_speed_lookup: dict[float, str] = {}
        for row in self.profile_df.iter_rows(named=True):
            height = row["height"]
            wind_speed = row["wind_speed_mean"]
            wind_speed_lookup[height] = f"{wind_speed:.2f}"

        headers = ["测风高度", "平均风速(m/s)"] + [f"{int(h)}m" for h in all_heights]
        data: list[list[str]] = []
        for from_h in all_heights:
            wind_speed = wind_speed_lookup.get(from_h, "-")
            row_cells = [f"{int(from_h)}m", wind_speed]

            for to_h in all_heights:
                if from_h == to_h:
                    row_cells.append("◦")
                elif from_h < to_h:
                    alpha = alpha_lookup.get((from_h, to_h))
                    if alpha is not None:
                        row_cells.append(f"{alpha:.3f}")
                    else:
                        row_cells.append("-")
                else:
                    alpha = alpha_lookup.get((to_h, from_h))
                    if alpha is not None:
                        row_cells.append(f"{alpha:.3f}")
                    else:
                        row_cells.append("-")

            data.append(row_cells)

        return TypstTable(headers=headers, data=data, caption=self.default_table_caption)

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"vertical_profile_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        profile_df = self.profile_df.sort("height")
        first_row = profile_df.row(0, named=True)
        alpha = first_row.get("alpha")
        r_squared = first_row.get("r_squared")

        plot_data = []
        for row in profile_df.iter_rows(named=True):
            plot_data.append({
                "height": row["height"],
                "wind_speed": row["wind_speed_mean"],
                "type": "实测数据",
                "display_name": get_height_display_name(row["height"], row["interpolation_marker"] or ""),
            })

        if alpha is not None and len(plot_data) >= 2:
            heights = [r["height"] for r in plot_data]
            min_h, max_h = min(heights), max(heights)
            fit_heights = np.logspace(np.log10(min_h), np.log10(max_h), 50)
            ref_h = plot_data[0]["height"]
            ref_v = plot_data[0]["wind_speed"]

            for h in fit_heights:
                v = ref_v * (h / ref_h) ** alpha
                plot_data.append({
                    "height": h,
                    "wind_speed": v,
                    "type": "幂律拟合",
                    "display_name": "拟合曲线",
                })

        plot_df = pl.DataFrame(plot_data).to_pandas()

        scatter = alt.Chart(plot_df[plot_df["type"] == "实测数据"]).mark_point(
            size=100,
            filled=True,
        ).encode(
            x=alt.X(
                "height:Q",
                scale=alt.Scale(type="log"),
                title="高度(m)",
            ),
            y=alt.Y(
                "wind_speed:Q",
                scale=alt.Scale(type="log"),
                title="风速(m/s)",
            ),
            color=alt.value("#1f77b4"),
            tooltip=[
                alt.Tooltip("display_name:N", title="高度"),
                alt.Tooltip("height:Q", title="高度(m)", format=".1f"),
                alt.Tooltip("wind_speed:Q", title="风速(m/s)", format=".2f"),
            ],
        )

        if alpha is not None:
            fit_line = alt.Chart(plot_df[plot_df["type"] == "幂律拟合"]).mark_line(
                strokeWidth=2,
            ).encode(
                x=alt.X("height:Q", scale=alt.Scale(type="log")),
                y=alt.Y("wind_speed:Q", scale=alt.Scale(type="log")),
                color=alt.value("#ff7f0e"),
                tooltip=[
                    alt.Tooltip("height:Q", title="高度(m)", format=".1f"),
                    alt.Tooltip("wind_speed:Q", title="拟合风速(m/s)", format=".2f"),
                ],
            )
            chart = scatter + fit_line
        else:
            chart = scatter

        alpha_str = f"{alpha:.3f}" if alpha is not None else "N/A"
        r_squared_str = f"{r_squared:.3f}" if r_squared is not None else "N/A"
        title = f"{self.meta.mast_name} 垂直风廓线 (α={alpha_str}, R²={r_squared_str})"

        final_chart = chart.properties(
            title=title,
            width=500,
            height=400,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(final_chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.height == 0:
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔无风切变矩阵数据。")]

        avg_alpha = self.profile_df["alpha"].mean()
        text = f"根据 {self.meta.mast_name}，得到总体高度的风切变指数为 {avg_alpha:.3f}。"
        return [TypstParagraph(text=text)]


__all__ = ["SingleMastWindShearExponentAtom"]
