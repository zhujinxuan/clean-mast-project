"""Wind frequency hours atom for single mast analysis."""

from pathlib import Path
from typing import cast

import polars as pl
from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.report_meta import (
    WindFrequencyAtomMeta,
    _height_label,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model.schemas import (
    WindFrequencySchema,
)


class SingleMastWindFrequencyHoursAtom(ReportAtom[WindFrequencySchema, WindFrequencyAtomMeta]):
    """Renders wind frequency occurrence hours table per interested height.

    - Table: Pivoted format with wind speed bins as rows, interested heights as columns
    - Image: No image (returns empty Path)
    - Summary: Chinese description mentioning mast name, interested heights,
      and 3~25 m/s occurrence frequency + hours
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 各风速区间风速频率和出现小时数"

    def _interested_heights(self) -> list[dict[str, object]]:
        """Return unique interested heights (>120m and ≤160m) sorted ascending."""
        filtered = self.df.filter(
            (pl.col("height") > 120.0) & (pl.col("height") <= 160.0)
        )
        return list(
            filtered.select(["height", "interpolation_marker"])
            .unique()
            .sort("height")
            .iter_rows(named=True)
        )

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as Typst table with frequency % and occurrence hours per height."""
        heights = self._interested_heights()

        height_headers: list[str] = []
        height_cols: list[float] = []
        for row in heights:
            height = cast(float, row["height"])
            marker = cast(str | None, row["interpolation_marker"])
            display_name = _height_label(height, marker)
            height_headers.append(f"{display_name} 频率")
            height_headers.append(f"{display_name} 出现小时数")
            height_cols.append(height)

        interested_df = self.df.filter(
            (pl.col("height") > 120.0)
            & (pl.col("height") <= 160.0)
            & (pl.col("bin_end") <= 25.0)
        ).sort("bin_start")

        data: list[list[str]] = []
        for (bin_start, bin_end), group in interested_df.group_by(
            ["bin_start", "bin_end"], maintain_order=True
        ):
            bin_end_display = (
                "∞" if float(bin_end) >= 100.0 else f"{float(bin_end):.0f}"
            )
            row_cells = [f"{float(bin_start):.0f}-{bin_end_display}"]

            for height in height_cols:
                height_row = group.filter(pl.col("height") == height)
                if height_row.is_empty():
                    freq_str = "0.00%"
                    hours_str = "0"
                else:
                    freq = float(height_row["frequency"][0])
                    hours = float(height_row["occurrence_hours"][0])
                    freq_str = f"{freq * 100:.2f}%"
                    hours_str = f"{int(round(hours))}"
                row_cells.extend([freq_str, hours_str])

            data.append(row_cells)

        headers = ["风速区间"] + height_headers
        return TypstTable(headers=headers, data=data, caption=self.default_table_caption)

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for wind frequency hours table."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of wind frequency occurrence hours."""
        heights = self._interested_heights()
        height_strs = [
            _height_label(cast(float, row["height"]), cast(str | None, row["interpolation_marker"]))
            for row in heights
        ]

        hours_freq_list: list[str] = []
        for row in heights:
            height = cast(float, row["height"])
            range_df = self.df.filter(
                (pl.col("height") == height)
                & (pl.col("bin_start") >= 3)
                & (pl.col("bin_start") < 25)
            )
            hours = range_df["occurrence_hours"].sum()
            freq = range_df["frequency"].sum()
            hours_freq_list.append(f"{int(round(hours))} ({freq * 100:.1f}%)")

        summary_text = (
            f"{self.meta.mast_name}测风塔在{'、'.join(height_strs)}测风年数据有效风速（3m/s~25m/s）出现小时数（频率）为"
            f"{', '.join(hours_freq_list)}小时。"
        )
        return [TypstParagraph(text=summary_text)]
