"""Vertical profile subsection.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.vertical_profile import (
    SingleMastVerticalProfileAtom,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstChild,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    get_height_display_name,
)


@dataclass(frozen=True)
class VerticalProfileSubsection:
    """Subsection for vertical wind profile analysis."""

    atoms: AtomCollection
    title: str = "垂直风廓线"
    level: int = 2

    def render(self, images_dir: Path) -> str:
        """Render subsection with narrative, tables, and figures."""
        lines = [self.title, ""]

        # Narrative for each mast
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, SingleMastVerticalProfileAtom)
            if atom:
                lines.append(atom.renderSummary())
                lines.append("")

        # All tables
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, SingleMastVerticalProfileAtom)
            if atom:
                lines.append(atom.renderTable())
                lines.append("")

        return "\n".join(lines)

    def render_ir(self, images_dir: Path) -> list[TypstChild]:
        """Render subsection to IR nodes.

        Returns a list of TypstChild nodes representing this section's content.

        Args:
            images_dir: Directory for generated images (unused for vertical profile)

        Returns:
            List of IR nodes (headings, paragraphs, tables)
        """
        children: list[TypstChild] = []

        # Heading - strip markdown prefix from title
        title_text = self.title.replace("## ", "")
        children.append(TypstHeading(text=title_text, level=self.level))

        # Narrative paragraph for each mast
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, SingleMastVerticalProfileAtom)
            if atom:
                children.append(TypstParagraph(text=atom.renderSummary()))

        # Table for each mast
        for mast in self.atoms.masts:
            atom = self.atoms.get(mast, SingleMastVerticalProfileAtom)
            if atom:
                table_node = self._atom_to_table(atom)
                if table_node:
                    children.append(table_node)

        return children

    def _atom_to_table(self, atom: SingleMastVerticalProfileAtom) -> TypstTable | None:
        """Convert atom data to TypstTable node.

        Args:
            atom: Vertical profile atom with dataframe

        Returns:
            TypstTable with headers and data, or None if empty
        """
        import polars as pl

        if atom.df.height == 0:
            return None

        # Sort by height for consistent ordering
        heights_df = atom.df.select(["height", "interpolation_marker"]).unique().sort("height")

        # Build table data - one row per height
        data: list[list[str]] = []
        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"]
            display = get_height_display_name(height, marker or "")

            # Get data for this height
            height_data = atom.df.filter(pl.col("height") == height).row(0, named=True)
            wind_speed_mean = height_data["wind_speed_mean"]
            alpha = height_data["alpha"]
            r_squared = height_data["r_squared"]

            # Format values
            alpha_str = f"{alpha:.3f}" if alpha is not None else "-"
            r_squared_str = f"{r_squared:.3f}" if r_squared is not None else "-"

            data.append([
                display,
                f"{wind_speed_mean:.2f}",
                alpha_str,
                r_squared_str,
            ])

        return TypstTable(
            data=data,
            headers=["高度", "平均风速(m/s)", "风切变指数α", "拟合优度R²"],
        )
