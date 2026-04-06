"""Wind power frequency table atom for single mast analysis.

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
class SingleMastWindPowerFrequencyTableAtom(ReportAtom[WindFrequencySchema, SingleMastMeta]):
    """Renders wind power frequency distribution table per height.

    Power frequency shows which wind speeds contribute most to energy production,
    typically peaking at higher speeds (8-12 m/s) due to the v³ relationship.

    - Table: Pivoted format with wind speed bins as rows, heights as columns
    - Image: No image for power frequency table (returns empty Path)
    - Summary: Chinese description of energy distribution by wind speed
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with pivoted wind power frequency by height.

        Rows: wind speed bins (0-1, 1-2, ..., 27-28, 28+ m/s)
        Columns: 风速(m/s) | height1 | height2 | ... (one column per height)
        Values: power_frequency as percentage (energy contribution)
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
            values="power_frequency",
            index="bin_label",
            on="height"
        ).sort("bin_label")

        # Build table rows
        rows = []
        for row in pivot_df.iter_rows(named=True):
            bin_label = row["bin_label"]
            row_cells = [f"  [{bin_label}]"]

            for height, _ in height_cols:
                p_freq = row.get(height, 0.0)
                # Display as percentage
                row_cells.append(f"[{p_freq * 100:.1f}%]")

            rows.append(",".join(row_cells) + ",")

        # Calculate totals per height (should sum to ~100%)
        totals = []
        for height, _ in height_cols:
            total = df_with_bin_label.filter(
                pl.col("height") == height
            )["power_frequency"].sum()
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
        """No image generation for wind power frequency table.

        Wind power frequency distribution is displayed as a table only.
        Returns an empty Path.
        """
        return Path()

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of wind power frequency distribution results."""
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

            # Most energy-contributing bin (highest power_frequency)
            max_power_row = height_data.sort("power_frequency", descending=True).row(0, named=True)
            most_power_bin = f"[{max_power_row['bin_start']:.0f}-{max_power_row['bin_end']:.0f})"
            max_power_pct = max_power_row["power_frequency"] * 100

            # Calculate weighted mean wind speed by energy contribution
            mean_speed_by_power = (height_data["bin_center"] * height_data["power_frequency"]).sum()

            # Effective energy hours (bins with significant power contribution, e.g., > 3 m/s)
            height_data.filter(
                pl.col("bin_start") >= 3
            )["power_hours"].sum()

            # Find productive range (3-25 m/s) energy contribution
            productive_data = height_data.filter(
                (pl.col("bin_start") >= 3) & (pl.col("bin_start") < 25)
            )
            productive_power_pct = productive_data["power_frequency"].sum() * 100

            height_name = get_height_display_name(height, marker)
            summaries.append(
                f"{height_name}风能加权平均风速{mean_speed_by_power:.2f}m/s，"
                f"能量贡献最大区间为{most_power_bin}（{max_power_pct:.1f}%），"
                f"有效风速(3-25m/s)能量占比{productive_power_pct:.1f}%"
            )

        # Overall summary
        return (
            f"{self.meta.mast_name}测风塔风能频率分布分析。"
            f"分析高度包括{', '.join(height_strs)}。"
            + "；".join(summaries) + "。"
            "由于风速与功率的三次方关系(v³)，风能分布峰值通常出现在较高风速区间(8-12m/s)，"
            "对风电机组选型与发电量估算具有重要参考价值。"
        )
