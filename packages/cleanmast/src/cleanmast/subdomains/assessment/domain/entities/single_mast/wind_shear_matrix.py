"""Wind shear exponent matrix atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.schemas import WindShearSchema
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)


@dataclass
class SingleMastWindShearExponentAtom(ReportAtom[WindShearSchema, SingleMastMeta]):
    """Renders wind shear exponent matrix between height levels.

    - Table: Square matrix showing shear exponent (α) between height pairs
    - Image: No image for shear matrix (returns empty Path)
    - Summary: Chinese description of shear exponent results
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst matrix table with shear exponents.

        Rows: from heights (lower reference heights)
        Columns: to heights (upper target heights)
        Diagonal: "◦" (no shear with self)
        Values: mean alpha (3 decimal places)
        Note: Values are antisymmetric (α_ij = -α_ji)
        """
        # Get unique heights sorted
        heights_from = self.df.select("from_height").unique().sort("from_height")
        heights_to = self.df.select("to_height").unique().sort("to_height")

        # Collect all unique heights for row/column headers
        all_heights = sorted(set(
            heights_from["from_height"].to_list() +
            heights_to["to_height"].to_list()
        ))

        # Build a lookup dictionary for alpha values
        alpha_lookup: dict[tuple[float, float], float] = {}
        for row in self.df.iter_rows(named=True):
            key = (row["from_height"], row["to_height"])
            alpha_lookup[key] = row["alpha_mean"]

        # Build table rows
        rows = []
        for from_h in all_heights:
            row_cells = [f"  [{int(from_h)}m]"]  # Row header

            for to_h in all_heights:
                if from_h == to_h:
                    # Diagonal - no shear with self
                    row_cells.append("[◦]")
                elif from_h < to_h:
                    # Lower to upper: use stored alpha (positive)
                    alpha = alpha_lookup.get((from_h, to_h))
                    if alpha is not None:
                        row_cells.append(f"[{alpha:.3f}]")
                    else:
                        row_cells.append("[-]")
                else:
                    # Upper to lower: invert alpha (negative)
                    alpha = alpha_lookup.get((to_h, from_h))
                    if alpha is not None:
                        row_cells.append(f"[{-alpha:.3f}]")
                    else:
                        row_cells.append("[-]")

            rows.append(",".join(row_cells) + ",")

        # Build column spec (auto for row header + auto per height column)
        columns_spec = "(" + ", ".join(["auto"] * (len(all_heights) + 1)) + ")"

        # Build column headers
        height_headers = [f"[{int(h)}m]" for h in all_heights]
        headers = "[高度], " + ", ".join(height_headers)

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
        """No image generation for wind shear matrix.

        Wind shear exponent is displayed as a table only.
        Returns a placeholder Path.
        """
        return Path()

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of wind shear analysis results."""
        # Handle empty data
        if self.df.height == 0:
            return f"{self.meta.mast_name}测风塔无风切变矩阵数据。"

        # Get unique heights
        all_heights = sorted(set(
            self.df["from_height"].to_list() +
            self.df["to_height"].to_list()
        ))
        height_strs = [f"{int(h)}m" for h in all_heights]

        # Calculate overall statistics
        alpha_values = self.df["alpha_mean"].to_list()
        avg_alpha = sum(alpha_values) / len(alpha_values) if alpha_values else 0
        min_alpha = min(alpha_values) if alpha_values else 0
        max_alpha = max(alpha_values) if alpha_values else 0

        # Find min/max height pairs
        min_row = self.df.sort("alpha_mean").row(0, named=True)
        max_row = self.df.sort("alpha_mean", descending=True).row(0, named=True)

        min_pair = f"{int(min_row['from_height'])}m-{int(min_row['to_height'])}m"
        max_pair = f"{int(max_row['from_height'])}m-{int(max_row['to_height'])}m"

        # Terrain characterization based on average alpha
        if avg_alpha < 0.12:
            terrain = "光滑地形（水面或平坦开阔地）"
        elif avg_alpha < 0.16:
            terrain = "开阔地形（草地或农田）"
        elif avg_alpha < 0.25:
            terrain = "粗糙地形（郊区或树林）"
        else:
            terrain = "非常粗糙地形（城市或密集建筑区）"

        return (
            f"{self.meta.mast_name}测风塔风切变指数分析。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"平均风切变指数为{avg_alpha:.3f}，"
            f"对应{terrain}。"
            f"最小风切变指数为{min_alpha:.3f}（{min_pair}），"
            f"最大风切变指数为{max_alpha:.3f}（{max_pair}）。"
            f"风切变指数矩阵显示了各高度层之间的风速垂直变化关系，"
            f"正值表示风速随高度增加，负值表示风速随高度降低。"
        )
