"""Wind power rose grid atom for monthly 3x4 grid visualization.

ADR-GUARDRAILS: ddd-t-001-aggregates, ddd-t-002-entities-value-objects, ddd-t-003-report-atoms
Compliance: Aggregate ✓ | Entity ✓ | Content-Addressable ✓
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import polars as pl
from matplotlib.figure import Figure
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import TypstParagraph, TypstTable
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindRoseSchema,
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

WIND_ROSE_COLORS = [
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#17becf",
    "#8c564b",
    "#e377c2",
]


@dataclass
class SingleMastMonthlyWindPowerRoseGridAtom(ReportAtom[WindRoseSchema, SingleMastMeta]):
    """Renders 3x4 grid of monthly wind power roses for all 12 months.

    - Table: Summary table of monthly dominant directions by power density
    - Image: 3x4 grid of polar charts (Jan-Dec)
    - Summary: Chinese description of seasonal wind power patterns
    """

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 各高度（100m 以上）各月风能玫瑰图"

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 月风能频率分布表"

    @override
    def renderTable(self) -> "TypstTable" | None:
        """Return None — this atom does not render a table."""
        return None

    def _build_monthly_grid_chart(self, plot_df: pl.DataFrame) -> Figure:
        """Build the 3x4 monthly wind power rose grid matplotlib chart.

        Args:
            plot_df: Filtered DataFrame with height_display column.

        Returns:
            Matplotlib Figure with 3 rows x 4 columns of polar subplots.
        """
        plot_df = plot_df.filter(pl.col("energy_frequency").is_not_null())
        height_order = (
            plot_df.select(["height", "height_display"])
            .unique()
            .sort("height", descending=True)["height_display"]
            .to_list()
        )

        months_info = plot_df.select(["month", "month_name"]).unique().sort("month")
        months = months_info["month"].to_list()
        month_names = months_info["month_name"].to_list()

        fig = plt.figure(figsize=(20, 15))

        for i, (month_num, month_name) in enumerate(zip(months, month_names), start=1):
            ax = fig.add_subplot(3, 4, i, projection="polar")
            ax.set_theta_zero_location("N")  # type: ignore[attr-defined]
            ax.set_theta_direction(-1)  # type: ignore[attr-defined]
            month_data = plot_df.filter(pl.col("month") == month_num)

            for h_idx, height_label in enumerate(height_order):
                color = WIND_ROSE_COLORS[h_idx % len(WIND_ROSE_COLORS)]
                group = month_data.filter(pl.col("height_display") == height_label).sort("sector")
                if group.height == 0:
                    continue
                group_sectors = group["sector"].to_numpy()
                energy_values = group["energy_frequency"].to_numpy()
                angles = 2 * np.pi * group_sectors / 16
                angles = np.append(angles, angles[0])
                energy_values = np.append(energy_values, energy_values[0])
                ax.plot(angles, energy_values, label=height_label if i == 1 else "", color=color, linewidth=1.5)

            ax.set_title(month_name, fontsize=11, pad=10)
            ax.set_yticklabels([])
            ax.set_xticklabels([])

        if fig.axes:
            handles, labels = fig.axes[0].get_legend_handles_labels()
            if handles:
                fig.legend(handles, labels, title="高度", loc="upper right", bbox_to_anchor=(0.98, 0.98))

        fig.suptitle(f"{self.meta.mast_name} 各月风能玫瑰图", fontsize=16, y=0.98)
        plt.tight_layout(rect=(0, 0, 1, 0.96))
        return fig

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 3x4 grid of monthly wind power roses.

        Creates a faceted chart with 12 subplots (3 rows x 4 columns),
        one for each month. Shows wind power density by direction.

        Args:
            output_dir: Directory to save the PNG file
            force: If True, regenerate even if cached file exists

        Returns:
            Path to the generated PNG file
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"windpowerroserose_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >=100m heights for visualization
        plot_df = self.df.filter(pl.col("height") >= 100)

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        chart = self._build_monthly_grid_chart(plot_df)

        output_dir.mkdir(parents=True, exist_ok=True)
        chart.savefig(image_path, format="png", dpi=150, bbox_inches="tight")
        plt.close(chart)

        return image_path

    @override
    def renderSummary(self) -> list["TypstParagraph"]:
        """Render Chinese narrative about seasonal wind power patterns.

        Summarizes the dominant wind directions and seasonal variations.
        """
        # Filter out null power density values
        power_df = self.df.filter(pl.col("wind_power_density").is_not_null())

        # Find dominant sector for each month by wind power density
        monthly_dominant = (
            power_df.group_by(["month", "month_name"])
            .agg([
                pl.col("sector_name").get(pl.col("wind_power_density").arg_max()).alias("dominant_sector"),
                pl.col("wind_power_density").max().alias("max_power_density"),
            ])
            .sort("month")
        )

        # Get overall dominant sectors across all months
        sector_counts = (
            monthly_dominant.group_by("dominant_sector")
            .len()
            .sort("len", descending=True)
        )

        dominant_sectors = sector_counts["dominant_sector"].to_list()[:3]
        sectors_str = "、".join(dominant_sectors)

        summary_text = f"{self.meta.mast_name}测风塔各月主导风能方向为{sectors_str}。"
        return [TypstParagraph(text=summary_text)]
