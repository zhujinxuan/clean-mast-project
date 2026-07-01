"""Wind rose atoms for single mast analysis.

Compliance: Subdomain layout | Entity | Atom Pattern

LOGIC-PRESERVATION: Ported from assessment/subdomains/wind_rose/entities/wind_rose_atom.py.
All chart rendering, table formatting, and summary logic preserved exactly.
"""

from __future__ import annotations

import typing
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import polars as pl
from matplotlib.figure import Figure
from matplotlib.projections.polar import PolarAxes
from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.report_meta import (
    WindRoseAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.schemas import (
    WindRoseSchema,
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

SECTOR_COUNT = 16
SECTOR_WIDTH = 360.0 / SECTOR_COUNT  # 22.5 degrees per sector

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

SECTOR_LABELS = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]


class SingleMastMonthlyWindFrequencyRoseAtom(ReportAtom[WindRoseSchema, WindRoseAtomMeta]):
    """Renders wind frequency rose for a single mast.

    - Table: All heights with sector frequencies
    - Image: Polar chart showing >=100m heights only
    - Summary: Chinese description of wind direction patterns
    """

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 风向频率玫瑰图"

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 风向频率分布表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node."""
        table_df = self.df.filter(pl.col("height") >= 100)
        table_df = table_df.group_by([
            "sector",
            "sector_name",
            "height",
            "interpolation_marker",
        ]).agg(pl.col("frequency").mean().alias("frequency"))

        heights_df = table_df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols: list[tuple[float, str]] = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        headers = ["风向"] + [h[1] for h in height_cols]

        data: list[list[str]] = []
        sectors = sorted(table_df["sector"].unique().to_list())

        for sector in sectors:
            sector_df = table_df.filter(pl.col("sector") == sector)
            sector_name = sector_df["sector_name"].first()
            data_by_height: dict[float, str] = {}
            for row in sector_df.iter_rows(named=True):
                data_by_height[row["height"]] = f"{row['frequency'] * 100:.2f}"

            row_data = [str(sector_name)] + [
                data_by_height.get(height, "0.00") for height, _ in height_cols
            ]
            data.append(row_data)

        return TypstTable(headers=headers, data=data, caption=self.default_table_caption)

    def _build_frequency_rose_chart(self, plot_df: pl.DataFrame) -> Figure:
        plot_df = plot_df.with_columns(
            pl.when(pl.col("frequency_pct") == 0)
            .then(0.01)
            .otherwise(pl.col("frequency_pct"))
            .alias("frequency_pct")
        )
        height_order = (
            plot_df.select(["height", "height_display"])
            .unique()
            .sort("height", descending=True)["height_display"]
            .to_list()
        )

        _fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection="polar"))
        polar_ax = typing.cast(PolarAxes, ax)

        for idx, height_label in enumerate(height_order):
            color = WIND_ROSE_COLORS[idx % len(WIND_ROSE_COLORS)]
            group = plot_df.filter(pl.col("height_display") == height_label).sort("sector")
            group_sectors = group["sector"].to_numpy()
            freqs = group["frequency_pct"].to_numpy()
            angles = 2 * np.pi * group_sectors / SECTOR_COUNT
            angles = np.append(angles, angles[0])
            freqs = np.append(freqs, freqs[0])
            polar_ax.plot(angles, freqs, label=height_label, color=color, linewidth=2)

        polar_ax.set_theta_zero_location("N")
        polar_ax.set_theta_direction(-1)
        polar_ax.set_xticks(np.linspace(0, 2 * np.pi, SECTOR_COUNT, endpoint=False))
        polar_ax.set_xticklabels(SECTOR_LABELS)
        polar_ax.set_title(f"{self.meta.mast_name} 风向频率玫瑰图", pad=20)
        polar_ax.legend(title="高度", loc="upper left", bbox_to_anchor=(1.05, 1))
        plt.tight_layout()
        return _fig

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate wind frequency rose polar chart with >=100m heights only."""
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"windfreqrose_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        plot_df = self.df.filter(pl.col("height") >= 100)

        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        plot_df = plot_df.with_columns(
            (pl.col("frequency") * 100).alias("frequency_pct")
        )
        plot_df = (
            plot_df.group_by(["sector", "sector_name", "height", "height_display"])
            .agg(pl.col("frequency_pct").mean().alias("frequency_pct"))
        )

        chart = self._build_frequency_rose_chart(plot_df)

        output_dir.mkdir(parents=True, exist_ok=True)
        chart.savefig(image_path, format="png", dpi=150, bbox_inches="tight")
        plt.close(chart)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        summary_df = self.df.filter(
            (pl.col("height") >= 125) & (pl.col("height") <= 160)
        )

        heights = (
            summary_df.select(["height", "interpolation_marker"])
            .unique()
            .sort("height", descending=True)
        )

        parts: list[str] = []
        for idx, row in enumerate(heights.iter_rows(named=True)):
            height = row["height"]
            marker = row["interpolation_marker"]
            height_label = f"{int(height)}m({marker})" if marker else f"{int(height)}m"

            top_sectors = (
                summary_df.filter(pl.col("height") == height)
                .group_by("sector_name")
                .agg(pl.col("frequency").mean().alias("avg_freq"))
                .sort("avg_freq", descending=True)
                .head(2)
            )

            rows_list = list(top_sectors.iter_rows(named=True))
            if len(rows_list) < 2:
                continue

            sector1 = rows_list[0]["sector_name"]
            pct1 = rows_list[0]["avg_freq"] * 100
            sector2 = rows_list[1]["sector_name"]
            pct2 = rows_list[1]["avg_freq"] * 100

            if idx == 0:
                parts.append(
                    f"{self.meta.mast_name}测风塔在{height_label}主风向为 {sector1}({pct1:.1f}%)，"
                    f"次主风向为 {sector2}({pct2:.1f}%)。"
                )
            else:
                parts.append(
                    f"其{height_label}主风向为 {sector1}({pct1:.1f}%)，"
                    f"次主风向为 {sector2}({pct2:.1f}%)。"
                )

        summary_text = "".join(parts) if parts else f"{self.meta.mast_name}测风塔无125m~160m高度风向频率数据。"
        return [TypstParagraph(text=summary_text)]


class SingleMastWindPowerRoseAtom(ReportAtom[WindRoseSchema, WindRoseAtomMeta]):
    """Renders wind energy frequency rose for a single mast.

    - Table: All heights with sector energy frequencies
    - Image: Polar chart showing >=100m heights only
    - Summary: Chinese description of wind energy patterns
    """

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 风能频率玫瑰图"

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 风能频率分布表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node with energy frequency values."""
        table_df = self.df.filter(pl.col("height") >= 100)
        table_df = table_df.group_by([
            "sector",
            "sector_name",
            "height",
            "interpolation_marker",
        ]).agg(pl.col("energy_frequency").mean().alias("energy_frequency"))

        heights_df = table_df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols: list[tuple[float, str]] = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        headers = ["风向"] + [h[1] for h in height_cols]

        data: list[list[str]] = []
        sectors = sorted(table_df["sector"].unique().to_list())

        for sector in sectors:
            sector_df = table_df.filter(pl.col("sector") == sector)
            sector_name = sector_df["sector_name"].first()
            data_by_height: dict[float, str] = {}
            for row in sector_df.iter_rows(named=True):
                val = row["energy_frequency"]
                data_by_height[row["height"]] = f"{val * 100:.2f}" if val is not None else "—"

            row_data = [str(sector_name)] + [
                data_by_height.get(height, "0.00") for height, _ in height_cols
            ]
            data.append(row_data)

        return TypstTable(headers=headers, data=data, caption=self.default_table_caption)

    def _build_power_rose_chart(self, plot_df: pl.DataFrame) -> Figure:
        """Build matplotlib wind power rose chart from prepared data."""
        plot_df = plot_df.with_columns(
            pl.when(pl.col("frequency_pct") == 0)
            .then(0.01)
            .otherwise(pl.col("frequency_pct"))
            .alias("frequency_pct")
        )
        height_order = (
            plot_df.select(["height", "height_display"])
            .unique()
            .sort("height", descending=True)["height_display"]
            .to_list()
        )

        _fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection="polar"))
        polar_ax = typing.cast(PolarAxes, ax)

        for idx, height_label in enumerate(height_order):
            color = WIND_ROSE_COLORS[idx % len(WIND_ROSE_COLORS)]
            group = plot_df.filter(pl.col("height_display") == height_label).sort("sector")
            group_sectors = group["sector"].to_numpy()
            freqs = group["frequency_pct"].to_numpy()
            angles = 2 * np.pi * group_sectors / SECTOR_COUNT
            angles = np.append(angles, angles[0])
            freqs = np.append(freqs, freqs[0])
            polar_ax.plot(angles, freqs, label=height_label, color=color, linewidth=2)

        polar_ax.set_theta_zero_location("N")
        polar_ax.set_theta_direction(-1)
        polar_ax.set_xticks(np.linspace(0, 2 * np.pi, SECTOR_COUNT, endpoint=False))
        polar_ax.set_xticklabels(SECTOR_LABELS)
        polar_ax.set_title(f"{self.meta.mast_name} 风能频率玫瑰图", pad=20)
        polar_ax.legend(title="高度", loc="upper left", bbox_to_anchor=(1.05, 1))
        plt.tight_layout()
        return _fig

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate wind energy frequency rose polar chart with >=100m heights only."""
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"windpowerrose_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        plot_df = self.df.filter(pl.col("height") >= 100)

        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        plot_df = plot_df.with_columns(
            (pl.col("energy_frequency") * 100).alias("frequency_pct")
        )
        plot_df = (
            plot_df.group_by(["sector", "sector_name", "height", "height_display"])
            .agg(pl.col("frequency_pct").mean().alias("frequency_pct"))
        )

        chart = self._build_power_rose_chart(plot_df)

        output_dir.mkdir(parents=True, exist_ok=True)
        chart.savefig(image_path, format="png", dpi=150, bbox_inches="tight")
        plt.close(chart)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        summary_df = self.df.filter(
            (pl.col("height") >= 125) & (pl.col("height") <= 160)
        )

        heights = (
            summary_df.select(["height", "interpolation_marker"])
            .unique()
            .sort("height", descending=True)
        )

        parts: list[str] = []
        for idx, row in enumerate(heights.iter_rows(named=True)):
            height = row["height"]
            marker = row["interpolation_marker"]
            height_label = f"{int(height)}m({marker})" if marker else f"{int(height)}m"

            top_sectors = (
                summary_df.filter(pl.col("height") == height)
                .group_by("sector_name")
                .agg(pl.col("energy_frequency").mean().alias("avg_energy_freq"))
                .sort("avg_energy_freq", descending=True)
                .head(2)
            )

            rows_list = list(top_sectors.iter_rows(named=True))
            if len(rows_list) < 2:
                continue

            sector1 = rows_list[0]["sector_name"]
            pct1 = rows_list[0]["avg_energy_freq"] * 100
            sector2 = rows_list[1]["sector_name"]
            pct2 = rows_list[1]["avg_energy_freq"] * 100

            if idx == 0:
                parts.append(
                    f"{self.meta.mast_name}测风塔在{height_label}主导风能方向为 {sector1}({pct1:.1f}%)，"
                    f"次主导风能方向为 {sector2}({pct2:.1f}%)。"
                )
            else:
                parts.append(
                    f"其{height_label}主导风能方向为 {sector1}({pct1:.1f}%)，"
                    f"次主导风能方向为 {sector2}({pct2:.1f}%)。"
                )

        summary_text = "".join(parts) if parts else f"{self.meta.mast_name}测风塔无125m~160m高度风能频率数据。"
        return [TypstParagraph(text=summary_text)]
