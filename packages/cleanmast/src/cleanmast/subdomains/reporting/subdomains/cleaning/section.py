"""Cleaning capability sections (2.3.2–2.3.7) — Wave 1 placeholders.

Each section implements the Section protocol. Wave 1 renders a one-line
Chinese placeholder per subsection so report generation succeeds
end-to-end; Wave 2 replaces ``from_inputs`` bodies with the real
compute → assemble pipelines.

Section input contract (Wave 2): ``from_inputs(items)`` receives one
``SingleMastAnalysisInput`` per mast of the ``cleaning_pipeline`` dataset.
The mast's ``time_series`` is the reconstruct-meso parquet clipped to the
rep-year analysis window; ``cleaning_payload`` carries the pipeline stage
sources (``raw_input`` / ``clean_input`` / ``tower_shading_input``,
project-relative paths), ``cleaning_heights`` (the ONLY heights source),
and the ``analysis_window`` used as the expected-points denominator.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Self, Sequence

from typst_ir import (
    TypstEquation,
    TypstHeading,
    TypstSection,
    TypstTable,
)

from cleanmast.subdomains.reporting.model.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.assemble import (
    build_cleaning_overview_atoms,
    build_cleaning_placeholder_atoms,
    build_cleaning_rules_atoms,
    build_cross_mast_atoms,
    build_meso_atoms,
    build_same_tower_atoms,
    build_tower_shading_atoms,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute import (
    analyze_cross_mast,
    analyze_meso,
    analyze_same_tower,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model import (
    CleaningCoverageAtom,
    CleaningFlowIntroAtom,
    CleaningPlaceholderAtom,
    CleaningRulesAtom,
    CleaningViolationsAtom,
    CorrelationMatrixAtom,
    ScatterRegressionAtom,
    TowerShadingMethodAtom,
    TowerShadingSectorTableAtom,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.rules_io import (
    discover_enabled_rules,
    load_violation_stats,
)


@dataclass(frozen=True)
class _CleaningSectionBase:
    """Shared machinery for the 2.3.x sections (Wave 1 placeholders)."""

    _atoms: Sequence[ReportAtom]
    title: str = ""

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (CleaningPlaceholderAtom, True),
    ]
    _placeholder_text: ClassVar[str] = ""

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> Self:
        """Build the placeholder section from standard mast inputs."""
        mast_names = [item.mast_name for item in items]
        return cls(
            _atoms=build_cleaning_placeholder_atoms(
                mast_names, cls._placeholder_text
            )
        )

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        body = render_subsection_content(
            self._atoms, self.atom_configs, images_dir
        )
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )


@dataclass(frozen=True)
class CleaningOverviewSection(_CleaningSectionBase):
    """2.3.2 数据清洗与插补总体概况.

    Renders the processing-flow intro paragraph (standards citations),
    the expected-points stats sentence, and the per-mast × per-height
    stage coverage table (原始 / 清洗后 / 插补后 vs 应有点数).
    """

    title: str = "数据清洗与插补总体概况"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (CleaningFlowIntroAtom, True),
        (CleaningCoverageAtom, True),
    ]

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> Self:
        """Build the 2.3.2 overview section (flow intro + coverage)."""
        return cls(_atoms=build_cleaning_overview_atoms(items))


@dataclass(frozen=True)
class CleaningRulesSection(_CleaningSectionBase):
    """2.3.3 缺测与不合理数据处理.

    Renders the enabled cleaning rules (process-clean.toml, GB/T
    37523-2019 intro) and the per-mast per-rule removal counts parsed
    from ``process-stats/process-clean-<mast>.yaml``.
    """

    title: str = "缺测与不合理数据处理"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (CleaningRulesAtom, True),
        (CleaningViolationsAtom, True),
        (CleaningPlaceholderAtom, True),
    ]

    @classmethod
    def from_inputs(
        cls,
        items: list[SingleMastAnalysisInput],
        project_dir: Path | None = None,
    ) -> Self:
        """Build the 2.3.3 rules + violations section.

        Args:
            items: One input per mast of the cleaning dataset.
            project_dir: Project directory holding process-clean.toml and
                process-stats/; None degrades to skip notes.
        """
        mast_names = [item.mast_name for item in items]
        enabled = discover_enabled_rules(project_dir)
        stats = [
            load_violation_stats(project_dir, mast_name)
            for mast_name in mast_names
        ]
        return cls(
            _atoms=build_cleaning_rules_atoms(mast_names, enabled, stats)
        )


@dataclass(frozen=True)
class TowerShadingSection(_CleaningSectionBase):
    """2.3.4 塔影效应处理.

    Method paragraph citing NB/T 31147-2018 with the max-merge display
    equation, followed by one per-height 16-sector before/after wind-speed
    comparison table (weighted overall row included) for every dual-channel
    height of each mast with a tower-shading stage. Masts without
    dual-channel heights contribute the method text only.
    """

    title: str = "塔影效应处理"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (TowerShadingMethodAtom, True),
        (TowerShadingSectorTableAtom, False),
    ]

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> Self:
        """Build the section from standard mast inputs."""
        return cls(_atoms=build_tower_shading_atoms(items))

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes: paragraphs, equation, then tables."""
        body = render_subsection_content(
            self._atoms, self.atom_configs, images_dir
        )
        equation = TypstEquation(
            latex="V_i = max(V_i^1, V_i^2)",
            display=True,
        )
        # Three-phase body order is summaries → tables → figures; slot the
        # display equation between the summary paragraphs and the tables.
        insert_at = next(
            (
                i
                for i, block in enumerate(body)
                if isinstance(block, TypstTable)
            ),
            len(body),
        )
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[*body[:insert_at], equation, *body[insert_at:]],
            subsections=[],
        )


@dataclass(frozen=True)
class ImputationSameTowerSection(_CleaningSectionBase):
    """2.3.5 同塔插补.

    Pairwise correlation among the mast's ``cleaning_heights`` on the
    corrected measured series (tower-shading output when present, else
    the process-clean output): correlation-matrix table + upper-triangle
    scatter grid with per-panel OLS annotations. Masts with fewer than
    two resolvable heights contribute no exhibits.
    """

    title: str = "同塔插补"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (CleaningPlaceholderAtom, True),
        (CorrelationMatrixAtom, False),
        (ScatterRegressionAtom, False),
    ]

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> Self:
        """Build the section from standard mast inputs."""
        return cls(_atoms=build_same_tower_atoms(analyze_same_tower(items)))


@dataclass(frozen=True)
class ImputationCrossMastSection(_CleaningSectionBase):
    """2.3.6 异塔插补.

    For each ordered mast pair, a scatter grid of ``mast_a`` heights
    (y) against ``mast_b`` heights (x) on overlapping timestamps of the
    corrected series, with per-panel OLS annotations. Pairs without a
    regressable panel contribute no exhibits.
    """

    title: str = "异塔插补"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (CleaningPlaceholderAtom, True),
        (ScatterRegressionAtom, False),
    ]

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> Self:
        """Build the section from standard mast inputs."""
        return cls(_atoms=build_cross_mast_atoms(analyze_cross_mast(items)))


@dataclass(frozen=True)
class ImputationMesoSection(_CleaningSectionBase):
    """2.3.7 中尺度插补.

    Per mast, scatter of each ``cleaning_height`` (y) against the
    experiment's selected ERA5 wind speed (x) — the meso source attached
    as the representative-year calibration payload — aligned per the
    representative-year convention (both series to the meso sampling
    interval, inner join on timestamps). Masts without a meso payload
    contribute no exhibits.
    """

    title: str = "中尺度插补"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (CleaningPlaceholderAtom, True),
        (ScatterRegressionAtom, False),
    ]

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> Self:
        """Build the section from standard mast inputs."""
        return cls(_atoms=build_meso_atoms(analyze_meso(items)))
