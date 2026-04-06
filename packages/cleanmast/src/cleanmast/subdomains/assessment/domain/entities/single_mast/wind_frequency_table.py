"""Wind frequency table atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindFrequencySchema,
)


@dataclass
class SingleMastWindFrequencyTableAtom(ReportAtom[WindFrequencySchema, SingleMastMeta]):
    """Renders wind frequency distribution table per height.

    - Table: Pivoted format with wind speed bins as rows, heights as columns
    - Image: No image for frequency table (returns empty Path)
    - Summary: Chinese description of frequency distribution
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with pivoted wind frequency by height.

        Rows: wind speed bins (0-1, 1-2, ..., 27-28, 28+ m/s)
        Columns: 风速(m/s) | height1 | height2 | ... (one column per height)
        Values: frequency as percentage
        """
        # Create bin label column
        df_with_bin_label = self.df.with_columns(
            pl.when(pl.col("bin_end") == pl.col("bin_start") + 1)
            .then(pl.concat_str([
                pl.lit("["),
                pl.col("bin_start").cast(pl.Int64).cast(pl.String),
                pl.lit("-"),
                pl.col("bin_end").cast(pl.Int64).cast(pl.String),
                pl.lit(")")
            ]))
            .otherwise(pl.concat_str([
                pl.lit("["),
                pl.col("bin_start").cast(pl.Int64).cast(pl.String),
                pl.lit("+)")
            ]))
            .alias("bin_label")
        )

        # Get unique heights sorted
        heights_df = df_with_bin_label.select(
            ["height", "interpolation_marker"]
        ).unique().sort("height")
        heights = heights_df.iter_rows(named=True)

        # Create height display names for headers
        height_headers = []
        height_cols = []
        for row in heights:
            display_name = get_height_display_name(
                row["height"],
                row["interpolation_marker"] or ""
            )
            height_headers.append(f"[{display_name}]")
            height_cols.append((row["height"], display_name))

        # Pivot data: rows = bin_label, columns = height
        pivot_df = df_with_bin_label.pivot(
            values="frequency",
            index="bin_label",
            on="height"
        ).sort("bin_label")

        # Build table rows
        rows = []
        for row in pivot_df.iter_rows(named=True):
            bin_label = row["bin_label"]
            row_cells = [f"  [{bin_label}]"]

            for height, _ in height_cols:
                freq = row.get(height, 0.0)
                # Display as percentage
                row_cells.append(f"[{freq * 100:.1f}%]")

            rows.append(",".join(row_cells) + ",")

        # Calculate totals per height
        totals = []
        for height, _ in height_cols:
            total = df_with_bin_label.filter(
                pl.col("height") == height
            )["frequency"].sum()
            totals.append(f"[{total * 100:.0f}%]")

        # Add total row
        rows.append("  [合计]," + ",".join(totals) + ",")

        # Build column spec (auto for bin_label + auto per height)
        columns_spec = "(" + ", ".join(["auto"] * (len(height_cols) + 1)) + ")"

        # Build headers (风速(m/s) + each height display name)
        headers = "[风速(m/s)], " + ", ".join(height_headers)

        return f"""#table(
  columns: {columns_spec},
  inset: 8pt,
  align: center,
  table.header(
    {headers}
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for wind frequency table.

        Wind frequency distribution is displayed as a table only.
        Returns a placeholder Path.
        """
        return Path()

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of wind frequency distribution results."""
        # Get unique heights
        heights_df = self.df.select(
            ["height", "interpolation_marker"]
        ).unique().sort("height")
        height_strs = [
            get_height_display_name(
                row["height"],
                row["interpolation_marker"] or ""
            )
            for row in heights_df.iter_rows(named=True)
        ]

        # Calculate summary statistics for each height
        summaries = []
        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"] or ""

            height_data = self.df.filter(pl.col("height") == height)

            # Most frequent bin
            max_freq_row = height_data.sort("frequency", descending=True).row(0, named=True)
            most_freq_bin = f"[{max_freq_row['bin_start']:.0f}-{max_freq_row['bin_end']:.0f})"
            max_freq_pct = max_freq_row["frequency"] * 100

            # Calculate mean wind speed (weighted by frequency)
            mean_speed = (height_data["bin_center"] * height_data["frequency"]).sum()

            # Effective hours (bins with significant frequency, e.g., > 3 m/s)
            effective_hours = height_data.filter(
                pl.col("bin_start") >= 3
            )["occurrence_hours"].sum()

            height_name = get_height_display_name(height, marker)
            summaries.append(
                f"{height_name}平均风速{mean_speed:.2f}m/s，"
                f"频率最高区间为{most_freq_bin}（{max_freq_pct:.1f}%），"
                f"有效风速(≥3m/s)小时数约{effective_hours:.0f}小时"
            )

        # Overall summary
        return (
            f"{self.meta.mast_name}测风塔风速频率分布分析。"
            f"分析高度包括{', '.join(height_strs)}。"
            + "；".join(summaries) + "。"
        )
