"""Monthly wind power pattern atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)


@dataclass
class SingleMastMonthlyPowerPatternAtom(ReportAtom[TemporalPatternSchema, SingleMastMeta]):
    """Renders 12-month monthly wind power density pattern for a single mast.

    - Table: Month-by-month wind power density by height (12 rows x heights columns)
    - Image: Grouped bar chart showing average wind power density by month
    - Summary: Chinese description of seasonal power pattern characteristics
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with monthly wind power density by height.

        Rows: 12 months (1-12)
        Columns: 月份 | 各高度平均风功率密度...
        """
        # Get unique heights and their display names (sorted)
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Aggregate by month and height (mean of mean_power)
        monthly = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_power").mean().alias("avg_monthly_power"),
            ])
            .sort(["month", "height"])
        )

        # Build the table rows (12 months)
        rows = []
        for month in range(1, 13):
            month_data = monthly.filter(pl.col("month") == month)

            cells = [f"  [{month}月]"]
            for height, _ in height_cols:
                power_row = month_data.filter(pl.col("height") == height)
                if power_row.height > 0:
                    power = power_row.row(0, named=True)["avg_monthly_power"]
                    power_val = power if power is not None else 0
                    cells.append(f"[{power_val:.1f}]")
                else:
                    cells.append("[-]")
            rows.append(", ".join(cells) + ",")

        # Build header: month + one column per height
        header_cells = "[月份], " + ", ".join([f"[{display}(W/m²)]" for _, display in height_cols])

        # Build column spec
        col_spec = "auto, " + ", ".join(["auto"] * len(height_cols))

        return f"""#table(
  columns: ({col_spec}),
  inset: 8pt,
  align: center,
  table.header(
    {header_cells}
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 12-month monthly power pattern grouped bar chart with >=100m heights only.

        Uses Altair grouped bar chart, exports to PNG via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"monthly_power_pattern_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Aggregate by month and height (mean of mean_power)
        monthly_df = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_power").mean().alias("avg_power"),
            ])
            .sort(["month", "height"])
        )

        # Filter to >=100m heights for visualization and valid power values
        plot_df = monthly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_power").is_not_null())
        )

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        # Convert to pandas for Altair compatibility
        plot_df_pd = plot_df.to_pandas()

        # Create Altair grouped bar chart
        bars = alt.Chart(plot_df_pd).mark_bar().encode(
            x=alt.X(
                "month:O",
                title="月份",
                scale=alt.Scale(domain=list(range(1, 13))),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "avg_power:Q",
                title="平均风功率密度(W/m²)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "height_display:N",
                title="高度",
                legend=alt.Legend(orient="right"),
            ),
            xOffset=alt.XOffset("height_display:N"),
            tooltip=["month", "height_display", alt.Tooltip("avg_power:Q", format=".1f")],
        )

        chart = bars.properties(
            title=f"{self.meta.mast_name} 月平均风功率密度分布",
            width=700,
            height=400,
        ).interactive()

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of monthly wind power density pattern."""
        # Aggregate by month and height (mean of mean_power)
        monthly_df = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_power").mean().alias("avg_power"),
            ])
            .sort(["month", "height"])
        )

        # Filter to >=100m heights
        high_df = monthly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_power").is_not_null())
        )

        # Get unique heights for mention
        heights = (
            high_df.select(["height", "interpolation_marker"])
            .unique()
            .sort("height")
        )
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"])
            for row in heights.iter_rows(named=True)
        ]

        if high_df.height > 0:
            # Find peak and minimum months across all heights
            by_month = (
                high_df.group_by("month")
                .agg([
                    pl.col("avg_power").mean().alias("overall_avg"),
                ])
                .sort("month")
            )

            peak_month = by_month.sort("overall_avg", descending=True).row(0, named=True)
            min_month = by_month.sort("overall_avg", descending=False).row(0, named=True)

            # Calculate overall statistics
            yearly_avg = high_df["avg_power"].mean()
            yearly_max = high_df["avg_power"].max()
            yearly_min = high_df["avg_power"].min()

            # Find which height has strongest/weakest seasonal variation
            variation_stats = (
                high_df.group_by(["height", "interpolation_marker"])
                .agg([
                    pl.col("avg_power").max().alias("max_power"),
                    pl.col("avg_power").min().alias("min_power"),
                ])
                .with_columns(
                    (pl.col("max_power") - pl.col("min_power")).alias("variation")
                )
                .sort("variation", descending=True)
            )

            most_variable = variation_stats.row(0, named=True)
            most_var_str = get_height_display_name(
                most_variable["height"], most_variable["interpolation_marker"]
            )

            # Determine seasonal pattern description
            peak_month_num = peak_month["month"]
            min_month_num = min_month["month"]

            # Classify seasonal pattern
            if peak_month_num in [12, 1, 2]:
                peak_season = "冬季"
            elif peak_month_num in [3, 4, 5]:
                peak_season = "春季"
            elif peak_month_num in [6, 7, 8]:
                peak_season = "夏季"
            else:
                peak_season = "秋季"

            if min_month_num in [12, 1, 2]:
                min_season = "冬季"
            elif min_month_num in [3, 4, 5]:
                min_season = "春季"
            elif min_month_num in [6, 7, 8]:
                min_season = "夏季"
            else:
                min_season = "秋季"

            return (
                f"{self.meta.mast_name}测风塔月变化风功率密度分析。"
                f"分析高度包括{', '.join(height_strs)}。"
                f"年平均风功率密度{yearly_avg:.1f}W/m²，"
                f"全年最高月均风功率密度{yearly_max:.1f}W/m²，"
                f"全年最低月均风功率密度{yearly_min:.1f}W/m²。"
                f"风功率密度峰值出现在{peak_month_num}月({peak_month['overall_avg']:.1f}W/m²)，"
                f"属于{peak_season}；"
                f"风功率密度低谷出现在{min_month_num}月({min_month['overall_avg']:.1f}W/m²)，"
                f"属于{min_season}，"
                f"呈现明显的季节性变化规律。"
                f"{most_var_str}季节变化幅度最大({most_variable['variation']:.1f}W/m²)，"
                f"展现了风功率密度随季节变化的动态特征。"
            )
        else:
            return (
                f"{self.meta.mast_name}测风塔月变化风功率密度分析。"
                f"分析高度包括{', '.join(height_strs)}。"
                f"暂无有效风功率密度数据。"
            )
