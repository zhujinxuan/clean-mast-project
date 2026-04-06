"""Single mast monthly wind speed analysis atom.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    MonthlyWindSchema,
)

from .report_meta import SingleMastMeta, get_height_display_name


@dataclass
class SingleMastMonthlyWindAtom(ReportAtom[MonthlyWindSchema, SingleMastMeta]):
    """Renders monthly wind speed statistics for a single mast.

    - Table: All heights with mean/max/min wind speeds
    - Image: Multi-line chart showing >100m heights only
    - Summary: Chinese description of wind patterns
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with pivoted format.

        Columns: 月份 | 10m | 50m | ... | 125m 外推 | 140m 外推 | 160m 外推
        """
        # Get unique heights and their display names
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Build the table rows
        rows = []
        months = sorted(self.df["month"].unique().to_list())

        for month in months:
            month_df = self.df.filter(pl.col("month") == month)

            # Create a lookup dict for this month's data by height
            data_by_height = {}
            for row in month_df.iter_rows(named=True):
                data_by_height[row["height"]] = row["wind_speed_mean"]

            # Add row for this month with average wind speeds
            row_cells = [f"  [{month}]"]
            for height, _ in height_cols:
                val = data_by_height.get(height, 0)
                row_cells.append(f"[{val:.2f}]")
            rows.append(", ".join(row_cells) + ",")

        # Build header with height columns
        header_cells = "[月份], " + ", ".join([f"[{h[1]}]" for h in height_cols])

        # Build column spec
        num_cols = 1 + len(height_cols)
        col_spec = ", ".join(["auto"] * num_cols)

        hashkey = self.get_or_compute_df_hashkey()
        return f"""#figure(
  table(
    columns: ({col_spec}),
    inset: 8pt,
    align: center,
    table.header(
      {header_cells}
    ),
{chr(10).join(rows)}
  ),
  caption: [{self.meta.mast_name} 月平均风速统计],
) <tbl-{hashkey}>
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate multi-line chart with >100m heights only.

        Uses Altair for declarative visualization, exports to PNG via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"monthlywind_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >100m heights for visualization and sort by month
        plot_df = self.df.filter(pl.col("height") > 100).sort("month")

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

        # Create Altair line chart
        chart = (
            alt.Chart(plot_df_pd)
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X("month:O", title="月份"),
                y=alt.Y("wind_speed_mean:Q", title="平均风速(m/s)"),
                color=alt.Color("height_display:N", title="高度"),
                tooltip=["month", "height_display", "wind_speed_mean"],
            )
            .properties(
                title=f"{self.meta.mast_name} 月平均风速",
                width=600,
                height=400,
            )
        )

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate representative year wind speed summary in Chinese.

        Format: 由图@fig-{hashkey}和表@tbl-{hashkey}可知，M1 在 120m，125m（外推），
        140m（外推）高度处年平均风速分别为5.2m/s、5.5m/s、5.8m/s，
        在7月最大为8.5m/s，在1月最小为3.2m/s。
        """
        # Get heights > 100m
        heights_df = (
            self.df.filter(pl.col("height") > 100)
            .select(["height", "interpolation_marker"])
            .unique()
            .sort("height")
        )

        height_strs = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_strs.append(display)

        # Calculate stats per height
        annual_means = []
        max_months = []
        max_values = []
        min_months = []
        min_values = []

        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            height_data = self.df.filter(pl.col("height") == height)

            # Annual mean
            annual_mean = height_data["wind_speed_mean"].mean()
            annual_means.append(f"{annual_mean:.2f}m/s")

            # Max month and value
            max_row = height_data.sort("wind_speed_mean", descending=True).head(1)
            max_month = max_row["month"].to_list()[0]
            max_value = max_row["wind_speed_mean"].to_list()[0]
            max_months.append(max_month)
            max_values.append(max_value)

            # Min month and value
            min_row = height_data.sort("wind_speed_mean").head(1)
            min_month = min_row["month"].to_list()[0]
            min_value = min_row["wind_speed_mean"].to_list()[0]
            min_months.append(min_month)
            min_values.append(min_value)

        # Build narrative
        return (
            f"由图{self.getReference()} 和表{self.getTableReference()} 可知，"
            f"{self.meta.mast_name} 在 {', '.join(height_strs)}高度处"
            f"年平均风速分别为{'、'.join(annual_means)}，"
            f"在{max_months[0]}月最大为{max_values[0]:.2f}m/s，"
            f"在{min_months[0]}月最小为{min_values[0]:.2f}m/s。"
        )
