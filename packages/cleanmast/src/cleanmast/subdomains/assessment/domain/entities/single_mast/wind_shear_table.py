"""Wind shear table atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.schemas import WindShearSchema
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)


@dataclass
class SingleMastWindShearTableAtom(ReportAtom[WindShearSchema, SingleMastMeta]):
    """Renders wind shear statistics table with height pairs.

    - Table: Starting height, target height, mean alpha, std, min, max
    - Image: No image for table (returns empty Path)
    - Summary: Chinese description of wind shear analysis results
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with wind shear statistics by height pair.

        Columns: 起始高度(m) | 目标高度(m) | 平均α | 标准差 | 最小值 | 最大值
        """
        # Sort by from_height then to_height for consistent display
        sorted_df = self.df.sort(["from_height", "to_height"])

        # Build table rows
        rows = []
        for row in sorted_df.iter_rows(named=True):
            from_h = row["from_height"]
            to_h = row["to_height"]
            mean_alpha = row["alpha_mean"]
            std_alpha = row["alpha_std"]
            min_alpha = row["alpha_min"]
            max_alpha = row["alpha_max"]
            rows.append(
                f"  [{from_h:.0f}], [{to_h:.0f}], [{mean_alpha:.3f}], [{std_alpha:.3f}], [{min_alpha:.3f}], [{max_alpha:.3f}],"
            )

        return f"""#table(
  columns: (auto, auto, auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [起始高度(m)], [目标高度(m)], [平均α], [标准差], [最小值], [最大值]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for wind shear table.

        Wind shear data is displayed as a table only.
        Returns a placeholder Path.
        """
        # No image needed for wind shear table
        return Path()

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of wind shear analysis results."""
        # Handle empty data
        if self.df.height == 0:
            return f"{self.meta.mast_name}测风塔无风切变数据。"

        # Sort by from_height then to_height
        sorted_df = self.df.sort(["from_height", "to_height"])

        # Get total number of height pairs
        num_pairs = len(sorted_df)

        # Calculate overall statistics across all pairs
        _mean_val: Any = sorted_df["alpha_mean"].mean()
        _std_val: Any = sorted_df["alpha_std"].mean()
        overall_mean = float(cast(float | int, _mean_val)) if _mean_val is not None else 0.0
        overall_std = float(cast(float | int, _std_val)) if _std_val is not None else 0.0

        # Find extreme values
        max_alpha_row = sorted_df.sort("alpha_max", descending=True).row(0, named=True)
        min_alpha_row = sorted_df.sort("alpha_min", descending=False).row(0, named=True)

        # Find pair with highest mean alpha
        max_mean_row = sorted_df.sort("alpha_mean", descending=True).row(0, named=True)
        min_mean_row = sorted_df.sort("alpha_mean", descending=False).row(0, named=True)

        # Determine typical terrain type based on mean alpha
        terrain_type = "平坦开阔"
        if overall_mean > 0.25:
            terrain_type = "复杂粗糙"
        elif overall_mean > 0.16:
            terrain_type = "粗糙"
        elif overall_mean > 0.12:
            terrain_type = "开阔"

        return (
            f"{self.meta.mast_name}测风塔风切变分析结果。"
            f"共分析{num_pairs}个高度层组合。"
            f"整体平均风切变指数为{overall_mean:.3f}，标准差为{overall_std:.3f}，"
            f"表明测风塔所在区域为{terrain_type}地形。"
            f"风切变指数最大值{max_alpha_row['alpha_max']:.3f}出现在"
            f"{max_alpha_row['from_height']:.0f}m至{max_alpha_row['to_height']:.0f}m层，"
            f"最小值{min_alpha_row['alpha_min']:.3f}出现在"
            f"{min_alpha_row['from_height']:.0f}m至{min_alpha_row['to_height']:.0f}m层。"
            f"平均风切变最大值为{max_mean_row['alpha_mean']:.3f}（{max_mean_row['from_height']:.0f}m→{max_mean_row['to_height']:.0f}m），"
            f"最小值为{min_mean_row['alpha_mean']:.3f}（{min_mean_row['from_height']:.0f}m→{min_mean_row['to_height']:.0f}m）。"
            f"风切变指数在典型范围{'内' if 0.10 <= overall_mean <= 0.40 else '外'}，"
            f"{'适合' if 0.12 <= overall_mean <= 0.20 else '需谨慎评估'}风机轮毂高度选择。"
        )
