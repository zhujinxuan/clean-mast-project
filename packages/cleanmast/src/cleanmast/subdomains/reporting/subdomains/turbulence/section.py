"""Turbulence intensity section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Sequence

from typst_ir import TypstHeading, TypstSection

if TYPE_CHECKING:
    import polars as pl

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.assemble import (
    build_turbulence_atoms,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.compute import (
    analyze_by_wind_speed,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model import (
    SingleMastTurbulenceMultiHeightAtom,
    SingleMastTurbulencePerHeightAtom,
    SingleMastTurbulenceSummaryAtom,
)


@dataclass(frozen=True)
class TurbulenceSection:
    """Section for single-mast turbulence intensity analysis.

    Implements the Section protocol for use with ReportBuilder.
    """

    _atoms: Sequence[ReportAtom]
    title: str = "湍流强度分析"
    _mast_names: list[str] | None = None

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (SingleMastTurbulenceSummaryAtom, True),
        (SingleMastTurbulencePerHeightAtom, False),
        (SingleMastTurbulenceMultiHeightAtom, False),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "TurbulenceSection":
        """Build section from standard mast input."""
        mast_data = [(item.time_series, item.mast_name) for item in items]
        mast_turbulence_heights: dict[str, list[float]] = {}
        for item in items:
            if item.parameters.turbulence_heights:
                mast_turbulence_heights[item.mast_name] = item.parameters.turbulence_heights
        return cls.from_time_series(mast_data, mast_turbulence_heights=mast_turbulence_heights)

    @classmethod
    def from_time_series(
        cls,
        mast_data: list[tuple[TimeSeriesData, str]],
        mast_turbulence_heights: dict[str, list[float]],
    ) -> "TurbulenceSection":
        """Build turbulence section from time series data.

        Args:
            mast_data: List of (time_series_data, mast_name) tuples.
            mast_turbulence_heights: Per-mast selected heights.

        Returns:
            TurbulenceSection with computed atoms.
        """
        computed: list[tuple[str, "pl.DataFrame"]] = []
        mast_names: list[str] = []

        for ts_data, mast_name in mast_data:
            ti_df = analyze_by_wind_speed(ts_data.df, ts_data.sensors)
            computed.append((mast_name, ti_df))
            mast_names.append(mast_name)

        atoms = build_turbulence_atoms(
            computed,
            mast_turbulence_heights=mast_turbulence_heights,
        ) if computed else []
        return cls(_atoms=atoms, _mast_names=mast_names)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
