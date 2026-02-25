"""Wind rose atoms for single mast analysis."""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from ...atom import ReportAtom
from ...meta import SingleMastMeta, get_height_display_name
from .schemas import WindRoseSchema


@dataclass
class SingleMastMonthlyWindFrequencyRoseAtom(ReportAtom[WindRoseSchema, SingleMastMeta]):
    """Renders wind frequency rose for a single mast.

    - Table: All heights with sector frequencies
    - Image: Polar chart showing >100m heights only
    - Summary: Chinese description of wind direction patterns
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with pivoted format.

        Columns: 风向 | 10m | 50m | ... | 125m 外推 | 140m 外推 | 160m 外推
        """
        # Get unique heights and their display names
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Build the table rows - one row per sector
        rows = []
        sectors = sorted(self.df["sector"].unique().to_list())

        for sector in sectors:
            sector_df = self.df.filter(pl.col("sector") == sector)
            sector_name = sector_df["sector_name"].first()

            # Create a lookup dict for this sector's data by height
            data_by_height = {}
            for row in sector_df.iter_rows(named=True):
                data_by_height[row["height"]] = row["frequency"] * 100

            # Add row for this sector with frequencies
            row_cells = [f"  [{sector_name}]"]
            for height, _ in height_cols:
                val = data_by_height.get(height, 0)
                row_cells.append(f"[{val:.2f}]")
            rows.append(", ".join(row_cells) + ",")

        # Build header with height columns
        header_cells = "[风向], " + ", ".join([f"[{h[1]}]" for h in height_cols])

        # Build column spec
        num_cols = 1 + len(height_cols)
        col_spec = ", ".join(["auto"] * num_cols)

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
        """Generate wind frequency rose polar chart with >100m heights only.

        Uses Altair polar coordinates, exports to PNG via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"windfreqrose_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >100m heights for visualization
        plot_df = self.df.filter(pl.col("height") > 100)

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        # Convert frequency to percentage for display
        plot_df = plot_df.with_columns(
            (pl.col("frequency") * 100).alias("frequency_pct")
        )

        # Convert to pandas for Altair compatibility
        plot_df_pd = plot_df.to_pandas()

        # Create Altair polar chart (wind rose) using mark_arc
        # Each sector is a bar extending from center to frequency value
        chart = alt.Chart(plot_df_pd).mark_arc(stroke="white").encode(
            theta=alt.Theta(
                "sector:O",
                title="风向",
                sort=None,
            ),
            radius=alt.Radius(
                "frequency_pct:Q",
                title="频率(%)",
                scale=alt.Scale(zero=True),
            ),
            radius2=alt.datum(0),  # Start from center
            color=alt.Color("height_display:N", title="高度"),
            tooltip=["sector_name", "height_display", "frequency_pct"],
        ).properties(
            title=f"{self.meta.mast_name} 风向频率玫瑰图",
            width=500,
            height=500,
        )

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of wind direction frequency patterns."""
        # Filter to >100m heights
        high_df = self.df.filter(pl.col("height") > 100)

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

        # Find dominant wind directions (top 3 by frequency averaged across heights)
        dominant = (
            high_df.group_by("sector_name")
            .agg(pl.col("frequency").mean().alias("avg_freq"))
            .sort("avg_freq", descending=True)
            .head(3)
        )
        dominant_directions = [row["sector_name"] for row in dominant.iter_rows(named=True)]

        return (
            f"{self.meta.mast_name}测风塔风向频率玫瑰图分析。"
            f"图表显示{', '.join(height_strs)}高度的风向频率分布，"
            f"主导风向为{'、'.join(dominant_directions)}，"
            f"反映了该测风塔的风能资源方向特征。"
        )


@dataclass
class SingleMastWindPowerRoseAtom(ReportAtom[WindRoseSchema, SingleMastMeta]):
    """Renders wind power rose for a single mast.

    - Table: All heights with sector frequencies and power density
    - Image: Polar chart showing >100m heights only
    - Summary: Chinese description of wind power patterns
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with pivoted format.

        Columns: 风向 | 10m | 50m | ... | 125m 外推 | 140m 外推 | 160m 外推
        Shows wind power density values.
        """
        # Get unique heights and their display names
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Build the table rows - one row per sector
        rows = []
        sectors = sorted(self.df["sector"].unique().to_list())

        for sector in sectors:
            sector_df = self.df.filter(pl.col("sector") == sector)
            sector_name = sector_df["sector_name"].first()

            # Create a lookup dict for this sector's data by height
            data_by_height = {}
            for row in sector_df.iter_rows(named=True):
                power = row["wind_power_density"]
                data_by_height[row["height"]] = f"{power:.2f}" if power is not None else "-"

            # Add row for this sector with power density values
            row_cells = [f"  [{sector_name}]"]
            for height, _ in height_cols:
                val = data_by_height.get(height, "-")
                row_cells.append(f"[{val}]")
            rows.append(", ".join(row_cells) + ",")

        # Build header with height columns
        header_cells = "[风向], " + ", ".join([f"[{h[1]}]" for h in height_cols])

        # Build column spec
        num_cols = 1 + len(height_cols)
        col_spec = ", ".join(["auto"] * num_cols)

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
        """Generate wind power rose polar chart with >100m heights only.

        Uses Altair polar coordinates with frequency as radius,
        wind power density represented by point size.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"windpowerrose_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >100m heights for visualization
        plot_df = self.df.filter(pl.col("height") > 100)

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        # Convert frequency to percentage for display
        plot_df = plot_df.with_columns(
            (pl.col("frequency") * 100).alias("frequency_pct")
        )

        # Convert to pandas for Altair compatibility
        plot_df_pd = plot_df.to_pandas()

        # Create Altair polar chart (wind power rose) using mark_arc
        # Each sector is a bar with color representing power density
        chart = alt.Chart(plot_df_pd).mark_arc(stroke="white").encode(
            theta=alt.Theta(
                "sector:O",
                title="风向",
                sort=None,
            ),
            radius=alt.Radius(
                "frequency_pct:Q",
                title="频率(%)",
                scale=alt.Scale(zero=True),
            ),
            radius2=alt.datum(0),  # Start from center
            color=alt.Color(
                "wind_power_density:Q",
                title="风功率密度(W/m²)",
                scale=alt.Scale(scheme="reds"),
            ),
            tooltip=["sector_name", "height_display", "frequency_pct", "wind_power_density"],
        ).properties(
            title=f"{self.meta.mast_name} 风功率玫瑰图",
            width=500,
            height=500,
        )

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of wind power patterns."""
        # Filter to >100m heights
        high_df = self.df.filter(pl.col("height") > 100)

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

        # Find dominant wind directions by power (considering both frequency and power density)
        # Filter out null power density values
        power_df = high_df.filter(pl.col("wind_power_density").is_not_null())

        if power_df.height > 0:
            # Calculate average power density by direction
            dominant_power = (
                power_df.group_by("sector_name")
                .agg(
                    pl.col("wind_power_density").mean().alias("avg_power"),
                    pl.col("frequency").mean().alias("avg_freq"),
                )
                .sort("avg_power", descending=True)
                .head(3)
            )
            dominant_directions = [
                row["sector_name"] for row in dominant_power.iter_rows(named=True)
            ]

            # Get average power density across all sectors and heights
            avg_power = power_df["wind_power_density"].mean()

            return (
                f"{self.meta.mast_name}测风塔风功率玫瑰图分析。"
                f"图表显示{', '.join(height_strs)}高度的风向频率与风功率密度分布，"
                f"主导能流方向为{'、'.join(dominant_directions)}，"
                f"平均风功率密度为{avg_power:.2f}W/m²，"
                f"为风电机组布局优化提供重要参考。"
            )
        else:
            # Fallback if no power density data available
            dominant_freq = (
                high_df.group_by("sector_name")
                .agg(pl.col("frequency").mean().alias("avg_freq"))
                .sort("avg_freq", descending=True)
                .head(3)
            )
            dominant_directions = [
                row["sector_name"] for row in dominant_freq.iter_rows(named=True)
            ]

            return (
                f"{self.meta.mast_name}测风塔风功率玫瑰图分析。"
                f"图表显示{', '.join(height_strs)}高度的风向频率分布，"
                f"主导风向为{'、'.join(dominant_directions)}。"
            )
