"""Monthly wind speed atom for representative year reports.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    MonthlyWindSchema,
)

from .report_meta import SingleMastMeta, get_height_display_name


@dataclass
class MonthlyWindSpeedAtom(ReportAtom[MonthlyWindSchema, SingleMastMeta]):
    """Renders monthly wind speed statistics for representative year reports."""

    @property
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} 代表年月风速图"

    @property
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 代表年月风速表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node with monthly wind speed by height."""
        # Get unique heights and their display names
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Build the table rows
        rows: list[list[str]] = []
        months = sorted(self.df["month"].unique().to_list())

        for month in months:
            month_df = self.df.filter(pl.col("month") == month)
            data_by_height = {}
            for row in month_df.iter_rows(named=True):
                data_by_height[row["height"]] = row["wind_speed_mean"]

            row_cells: list[str] = [f"{month}"]
            for height, _ in height_cols:
                val = data_by_height.get(height, 0)
                row_cells.append(f"{val:.2f}")
            rows.append(row_cells)

        avg_row: list[str] = ["平均"]
        for height, _ in height_cols:
            height_df = self.df.filter(pl.col("height") == height)
            mean_val = height_df["wind_speed_mean"].mean()
            if mean_val is not None and not (mean_val != mean_val):
                avg_row.append(f"{mean_val:.2f}")
            else:
                avg_row.append("-")
        rows.insert(0, avg_row)

        # Build header: month + one column per height
        headers = ["月份"] + [f"{display}(m/s)" for _, display in height_cols]

        return TypstTable(headers=headers, data=rows, caption=self._resolve_table_caption())

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate multi-line chart with >100m heights only."""
        # Implementation similar to SingleMastMonthlyWindAtom
        # Use altair to create line chart
        # Filter to heights > 100m
        # Return path to generated PNG
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"monthly_wind_speed_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >100m heights
        plot_df = self.df.filter(pl.col("height") > 100).sort("month")

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        # Convert to pandas for Altair
        plot_df_pd = plot_df.to_pandas()

        # Create Altair line chart
        import altair as alt
        import vl_convert as vlc

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
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate representative year wind speed summary in Chinese."""
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
        annual_means: list[str] = []
        max_months: list[int] = []
        max_values: list[float] = []
        min_months: list[int] = []
        min_values: list[float] = []

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
        summary = (
            f"由图{self.getReference()}和表{self.getTableReference()}可知，"
            f"{self.meta.mast_name} 在 {', '.join(height_strs)}高度处"
            f"年平均风速分别为{'、'.join(annual_means)}，"
            f"在{max_months[0]}月最大为{max_values[0]:.2f}m/s，"
            f"在{min_months[0]}月最小为{min_values[0]:.2f}m/s。"
        )

        return [TypstParagraph(text=summary)]
