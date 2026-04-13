"""Wind distribution subgrid atom for single mast analysis.

ADR-GUARDRAILS: ddd-t-003-report-atoms, structure-001-subdomain-layout
Compliance: ReportAtom ✓ | Content-Addressable ✓ | Altair Rendering ✓
"""

from dataclasses import dataclass
from pathlib import Path

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
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindFrequencySchema,
)


def _height_label(height: float, marker: str | None) -> str:
    base = f"{int(height)}m"
    if marker:
        return f"{base}({marker})"
    return base


@dataclass
class SingleMastWindDistributionSubgridAtom(ReportAtom[WindFrequencySchema, SingleMastMeta]):
    """Renders faceted Altair chart comparing wind freq and power freq bars per interested height.

    - Table: None (image-only atom)
    - Image: Faceted grouped bar chart with occurrence_hours and power_hours
    - Summary: Brief Chinese description
    """

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 风速频率分布图"

    @property
    def default_table_caption(self) -> None:
        return None

    @override
    def renderTable(self) -> TypstTable | None:
        return None

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate faceted grouped bar chart and save as PNG.

        Each facet shows:
        - Grouped bars for frequency and power_frequency side by side
        - X-axis: wind speed bin label (integer, ordinal)
        - Y-axis: frequency as percentage
        - Different colors for each metric with legend
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"wind_freq_dist_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        interested_df = self.df.filter(
            (pl.col("height") > 120.0)
            & (pl.col("height") <= 160.0)
            & (pl.col("bin_center") <= 25.0)
        ).with_columns(
            pl.when(
                pl.col("interpolation_marker").is_null()
                | (pl.col("interpolation_marker") == "")
            )
            .then(pl.col("height").cast(pl.Utf8) + "m")
            .otherwise(
                pl.col("height").cast(pl.Utf8) + "m(" + pl.col("interpolation_marker") + ")"
            )
            .alias("height_label"),
            pl.col("bin_start").cast(pl.Int64).alias("bin_label"),
        )

        df_long = (
            interested_df.select(
                ["bin_label", "bin_center", "frequency", "power_frequency", "height_label"]
            )
            .unpivot(
                index=["bin_label", "bin_center", "height_label"],
                on=["frequency", "power_frequency"],
                variable_name="metric",
                value_name="value",
            )
            .to_pandas()
        )

        chart = alt.Chart(df_long).mark_bar(size=8).encode(
            x=alt.X(
                "bin_label:O",
                title="风速 (m/s)",
                scale=alt.Scale(domain=list(range(0, 26))),
                axis=alt.Axis(labelAngle=0, values=list(range(0, 26, 5))),
            ),
            xOffset=alt.XOffset("metric:N"),
            y=alt.Y(
                "value:Q",
                title="频率",
                axis=alt.Axis(format=".0%"),
            ),
            color=alt.Color(
                "metric:N",
                title="类型",
                scale=alt.Scale(
                    domain=["frequency", "power_frequency"],
                    range=["#1f77b4", "#ff7f0e"],
                ),
                legend=alt.Legend(
                    title="频率类型",
                    labelExpr="datum.value == 'frequency' ? '风速频率' : '风能频率'",
                ),
            ),
            tooltip=[
                alt.Tooltip("bin_center:Q", title="风速(m/s)", format=".1f"),
                alt.Tooltip("value:Q", title="频率", format=".2%"),
                alt.Tooltip("metric:N", title="类型"),
            ],
            column=alt.Column("height_label:N", title="高度"),
        ).properties(
            title=f"{self.meta.mast_name} 风频与风能分布",
            width=300,
            height=160,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of wind frequency distribution subgrid."""
        interested_df = self.df.filter(
            (pl.col("height") > 120.0) & (pl.col("height") <= 160.0)
        )
        heights_df = (
            interested_df.select(["height", "interpolation_marker"])
            .unique()
            .sort("height")
        )
        height_strs = [
            _height_label(row["height"], row["interpolation_marker"])
            for row in heights_df.iter_rows(named=True)
        ]
        summary_text = (
            f"{self.meta.mast_name}测风塔风频与风能分布分析。"
            f"关注高度层包括{', '.join(height_strs)}。"
            f"图中展示了各高度层不同风速区间的风速频率与风能频率对比。"
        )
        return [TypstParagraph(text=summary_text)]
