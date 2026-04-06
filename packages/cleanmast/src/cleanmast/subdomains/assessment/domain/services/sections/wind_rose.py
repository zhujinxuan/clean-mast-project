"""Wind rose section implementation with hardcoded layout.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstChild,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class WindRoseSection:
    """Specialized section for wind rose analysis."""

    atoms: AtomCollection
    title: str = "风向风能分布"
    level: int = 1

    def render(self, images_dir: Path) -> str:
        """Hardcoded optimal layout for wind roses."""
        lines = [f"== {self.title}", ""]

        # Combined summary
        summaries = []
        for mast in self.atoms.masts:
            freq = self.atoms.get(mast, SingleMastMonthlyWindFrequencyRoseAtom)
            power = self.atoms.get(mast, SingleMastWindPowerRoseAtom)
            if freq:
                summaries.append(freq.renderSummary())
            if power:
                summaries.append(power.renderSummary())

        if summaries:
            lines.append(" ".join(summaries))
            lines.append("")

        # All figures
        for mast in self.atoms.masts:
            freq = self.atoms.get(mast, SingleMastMonthlyWindFrequencyRoseAtom)
            power = self.atoms.get(mast, SingleMastWindPowerRoseAtom)
            if freq:
                lines.append(freq.renderImageTypst(images_dir))
            if power:
                lines.append(power.renderImageTypst(images_dir))

        # All tables
        for mast in self.atoms.masts:
            freq = self.atoms.get(mast, SingleMastMonthlyWindFrequencyRoseAtom)
            power = self.atoms.get(mast, SingleMastWindPowerRoseAtom)
            if freq:
                lines.append(freq.renderTable())
            if power:
                lines.append(power.renderTable())

        return "\n".join(lines)

    def render_ir(self, images_dir: Path) -> list[TypstChild]:
        """Render section as IR nodes for type-safe document assembly.

        Generates images (side effect) and returns structured IR nodes
        including heading, figures, tables, and summaries.

        Args:
            images_dir: Directory where images should be saved

        Returns:
            List of TypstChild nodes (heading, figures, tables, paragraphs)
        """
        children: list[TypstChild] = []

        children.append(TypstHeading(text=self.title, level=self.level))

        for mast in self.atoms.masts:
            freq = self.atoms.get(mast, SingleMastMonthlyWindFrequencyRoseAtom)
            power = self.atoms.get(mast, SingleMastWindPowerRoseAtom)

            if freq:
                children.append(TypstParagraph(text=freq.renderSummary()))
                image_path = freq.renderImage(images_dir)
                rel_path = image_path.relative_to(images_dir.parent)
                caption = getattr(freq.meta, "caption", "风向频率玫瑰图")
                children.append(
                    TypstFigure(content=rel_path.as_posix(), caption=caption)
                )
                children.append(self._build_frequency_table(freq))

            if power:
                children.append(TypstParagraph(text=power.renderSummary()))
                image_path = power.renderImage(images_dir)
                rel_path = image_path.relative_to(images_dir.parent)
                caption = getattr(power.meta, "caption", "风功率玫瑰图")
                children.append(
                    TypstFigure(content=rel_path.as_posix(), caption=caption)
                )
                children.append(self._build_power_table(power))

        return children

    def _build_frequency_table(
        self, freq: SingleMastMonthlyWindFrequencyRoseAtom
    ) -> TypstTable:
        """Build TypstTable from frequency rose data."""
        import polars as pl

        df = freq.df
        heights_df = df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
                get_height_display_name,
            )
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        headers = ["风向"] + [h[1] for h in height_cols]
        data: list[list[str]] = []
        sectors = sorted(df["sector"].unique().to_list())

        for sector in sectors:
            sector_df = df.filter(pl.col("sector") == sector)
            sector_name = sector_df["sector_name"].first()
            data_by_height = {}
            for row in sector_df.iter_rows(named=True):
                data_by_height[row["height"]] = f"{row['frequency'] * 100:.2f}"
            row_data = [str(sector_name)] + [
                data_by_height.get(height, "0.00") for height, _ in height_cols
            ]
            data.append(row_data)

        return TypstTable(headers=headers, data=data, caption="风向频率分布表")

    def _build_power_table(
        self, power: SingleMastWindPowerRoseAtom
    ) -> TypstTable:
        """Build TypstTable from power rose data."""
        import polars as pl

        df = power.df
        heights_df = df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
                get_height_display_name,
            )
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        headers = ["风向"] + [h[1] for h in height_cols]
        data: list[list[str]] = []
        sectors = sorted(df["sector"].unique().to_list())

        for sector in sectors:
            sector_df = df.filter(pl.col("sector") == sector)
            sector_name = sector_df["sector_name"].first()
            data_by_height = {}
            for row in sector_df.iter_rows(named=True):
                val = row["wind_power_density"]
                data_by_height[row["height"]] = f"{val:.2f}" if val is not None else "-"
            row_data = [str(sector_name)] + [
                data_by_height.get(height, "-") for height, _ in height_cols
            ]
            data.append(row_data)

        return TypstTable(headers=headers, data=data, caption="风功率密度分布表")
