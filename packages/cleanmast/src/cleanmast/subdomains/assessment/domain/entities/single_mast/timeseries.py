"""Wind timeseries atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from datetime import datetime
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
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)


@dataclass
class SingleMastWindTimeseriesAtom(ReportAtom[TemporalPatternSchema, SingleMastMeta]):
    """Renders wind speed time series for a single mast.

    - Table: Summary statistics by height
    - Image: Multi-line time series chart showing wind speed over time
    - Summary: Chinese description of time series patterns
    """

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 风速时间序列图"

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 风速时间序列表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node with summary statistics by height.

        Columns: 高度 | 平均风速 | 最大风速 | 最小风速 | 标准差
        """
        # Get unique heights and their display names
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Calculate summary statistics by height
        summary = (
            self.df.group_by(["height", "interpolation_marker"])
            .agg([
                pl.col("wind_speed").mean().alias("mean_speed"),
                pl.col("wind_speed").max().alias("max_speed"),
                pl.col("wind_speed").min().alias("min_speed"),
                pl.col("wind_speed").std().alias("std_speed"),
            ])
            .sort("height")
        )

        # Build the table rows
        rows = []
        for height, display in height_cols:
            row_data = summary.filter(pl.col("height") == height)
            if row_data.height == 0:
                continue
            
            data = row_data.row(0, named=True)
            mean_val = data["mean_speed"] if data["mean_speed"] is not None else 0
            max_val = data["max_speed"] if data["max_speed"] is not None else 0
            min_val = data["min_speed"] if data["min_speed"] is not None else 0
            std_val = data["std_speed"] if data["std_speed"] is not None else 0

            rows.append([
                display,
                f"{mean_val:.2f}",
                f"{max_val:.2f}",
                f"{min_val:.2f}",
                f"{std_val:.2f}",
            ])

        return TypstTable(
            headers=["高度", "平均风速(m/s)", "最大风速(m/s)", "最小风速(m/s)", "标准差"],
            data=rows,
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate multi-line time series chart with >=100m heights only.

        Uses Altair line chart, exports to PNG via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"wind_timeseries_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >=100m heights for visualization and valid wind speeds
        plot_df = self.df.filter(
            (pl.col("height") >= 100) & (pl.col("wind_speed").is_not_null())
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

        # Create Altair multi-line time series chart
        chart = alt.Chart(plot_df_pd).mark_line(opacity=0.7).encode(
            x=alt.X(
                "timestamp:T",
                title="时间",
                axis=alt.Axis(format="%Y-%m-%d", labelAngle=-45),
            ),
            y=alt.Y(
                "wind_speed:Q",
                title="风速(m/s)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "height_display:N",
                title="高度",
                legend=alt.Legend(orient="right"),
            ),
            tooltip=["timestamp", "height_display", "wind_speed"],
        ).properties(
            title=f"{self.meta.mast_name} 风速时间序列",
            width=700,
            height=400,
        ).interactive()

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of wind speed time series patterns."""
        # Filter to >=100m heights and valid wind speeds
        high_df = self.df.filter(
            (pl.col("height") >= 100) & (pl.col("wind_speed").is_not_null())
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

        # Calculate overall statistics
        if high_df.height > 0:
            mean_speed = high_df["wind_speed"].mean()
            max_speed = high_df["wind_speed"].max()
            min_speed = high_df["wind_speed"].min()

            # Get time range
            time_min = high_df["timestamp"].dt.min()
            time_max = high_df["timestamp"].dt.max()

            # Calculate statistics by height to mention variations
            by_height = (
                high_df.group_by(["height", "interpolation_marker"])
                .agg([
                    pl.col("wind_speed").mean().alias("avg_speed"),
                    pl.col("wind_speed").count().alias("count"),
                ])
                .sort("height")
            )

            # Find highest and lowest average speeds
            highest = by_height.sort("avg_speed", descending=True).row(0, named=True)
            lowest = by_height.sort("avg_speed", descending=False).row(0, named=True)

            highest_str = get_height_display_name(highest["height"], highest["interpolation_marker"])
            lowest_str = get_height_display_name(lowest["height"], lowest["interpolation_marker"])

            assert isinstance(time_min, datetime) and isinstance(time_max, datetime)

            text = (
                f"{self.meta.mast_name}测风塔风速时间序列分析。"
                f"时间范围：{time_min.strftime('%Y年%m月%d日')}至{time_max.strftime('%Y年%m月%d日')}，"
                f"分析高度包括{', '.join(height_strs)}。"
                f"平均风速{mean_speed:.2f}m/s，"
                f"最大风速{max_speed:.2f}m/s，"
                f"最小风速{min_speed:.2f}m/s。"
                f"{highest_str}平均风速最高({highest['avg_speed']:.2f}m/s)，"
                f"{lowest_str}平均风速最低({lowest['avg_speed']:.2f}m/s)，"
                f"展现了风速随高度的变化特征。"
            )
        else:
            text = (
                f"{self.meta.mast_name}测风塔风速时间序列分析。"
                f"分析高度包括{', '.join(height_strs)}。"
                f"暂无有效风速数据。"
            )

        return [TypstParagraph(text=text)]
