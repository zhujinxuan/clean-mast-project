"""Weibull parameters atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WeibullSchema,
)


@dataclass
class SingleMastWeibullParametersAtom(ReportAtom[WeibullSchema, SingleMastMeta]):
    """Renders Weibull parameter table per height.

    - Table: Height, shape_k, scale_c, mean_speed by height
    - Image: No image for parameters (returns empty Path)
    - Summary: Chinese description of Weibull fit results
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with Weibull parameters by height.

        Columns: 高度 | 形状参数k | 尺度参数c | 平均风速(m/s)
        """
        # Sort by height for consistent display
        sorted_df = self.df.sort("height")

        # Build table rows
        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            shape_k = row["shape_k"]
            scale_c = row["scale_c"]
            mean_speed = row["mean_speed"]
            rows.append(f"  [{height_display}], [{shape_k:.2f}], [{scale_c:.2f}], [{mean_speed:.2f}],")

        return f"""#table(
  columns: (auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [高度], [形状参数k], [尺度参数c], [平均风速(m/s)]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for Weibull parameters.

        Weibull parameters are displayed as a table only.
        Returns a placeholder Path.
        """
        # No image needed for Weibull parameters
        return Path()

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of Weibull parameter fitting results."""
        sorted_df = self.df.sort("height")

        # Get unique heights for mention
        heights = sorted_df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"] or "")
            for row in heights.iter_rows(named=True)
        ]

        # Calculate summary statistics
        avg_k = sorted_df["shape_k"].mean()
        avg_c = sorted_df["scale_c"].mean()
        avg_speed = sorted_df["mean_speed"].mean()

        # Find extreme values
        max_k_row = sorted_df.sort("shape_k", descending=True).row(0, named=True)
        min_k_row = sorted_df.sort("shape_k", descending=False).row(0, named=True)

        max_speed_row = sorted_df.sort("mean_speed", descending=True).row(0, named=True)
        min_speed_row = sorted_df.sort("mean_speed", descending=False).row(0, named=True)

        return (
            f"{self.meta.mast_name}测风塔Weibull分布参数拟合分析。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"各高度平均形状参数k={avg_k:.2f}，平均尺度参数c={avg_c:.2f}m/s，"
            f"平均风速{avg_speed:.2f}m/s。"
            f"形状参数k最大值{max_k_row['shape_k']:.2f}出现在"
            f"{get_height_display_name(max_k_row['height'], max_k_row['interpolation_marker'] or '')}，"
            f"最小值{min_k_row['shape_k']:.2f}出现在"
            f"{get_height_display_name(min_k_row['height'], min_k_row['interpolation_marker'] or '')}。"
            f"平均风速最大值{max_speed_row['mean_speed']:.2f}m/s出现在"
            f"{get_height_display_name(max_speed_row['height'], max_speed_row['interpolation_marker'] or '')}，"
            f"最小值{min_speed_row['mean_speed']:.2f}m/s出现在"
            f"{get_height_display_name(min_speed_row['height'], min_speed_row['interpolation_marker'] or '')}。"
            f"Weibull分布拟合良好，可用于风资源评估。"
        )
