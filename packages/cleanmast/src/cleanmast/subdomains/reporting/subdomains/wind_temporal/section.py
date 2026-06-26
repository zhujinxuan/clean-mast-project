"""Wind temporal section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Sequence

from typst_ir import TypstHeading, TypstSection

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.assemble import (
    build_wind_temporal_atoms,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.compute import (
    analyze_daily_pattern,
    analyze_monthly_daily_pattern,
    analyze_monthly_pattern,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model import (
    SingleMastDailyPatternAtom,
    SingleMastDailyPowerPatternAtom,
    SingleMastMonthlyDailyPowerAtom,
    SingleMastMonthlyDailyWindAtom,
    SingleMastMonthlyPatternAtom,
    SingleMastMonthlyPowerPatternAtom,
)


@dataclass(frozen=True)
class WindTemporalSection:
    """Section for single-mast wind temporal pattern analysis.

    Implements the Section protocol for use with ReportBuilder.
    """

    _atoms: Sequence[ReportAtom]
    title: str = "风速时序分析"
    _mast_names: list[str] | None = None

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (SingleMastMonthlyPatternAtom, True),
        (SingleMastMonthlyPowerPatternAtom, True),
        (SingleMastDailyPatternAtom, True),
        (SingleMastDailyPowerPatternAtom, True),
        (SingleMastMonthlyDailyWindAtom, False),
        (SingleMastMonthlyDailyPowerAtom, False),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "WindTemporalSection":
        """Build section from standard mast input."""
        mast_data = [
            (item.time_series, item.mast_name, item.parameters.air_density)
            for item in items
        ]
        return cls.from_time_series(mast_data)

    @classmethod
    def from_time_series(
        cls,
        mast_data: list[tuple[TimeSeriesData, str, float]],
    ) -> "WindTemporalSection":
        """Build wind temporal section from time series data.

        Args:
            mast_data: List of (time_series_data, mast_name, air_density) tuples.

        Returns:
            WindTemporalSection with computed atoms.
        """
        all_atoms: list[ReportAtom] = []
        mast_names: list[str] = []

        for ts_data, mast_name, air_density in mast_data:
            daily_df = analyze_daily_pattern(ts_data.df, ts_data.sensors, air_density)
            monthly_df = analyze_monthly_pattern(ts_data.df, ts_data.sensors, air_density)
            monthly_daily_df = analyze_monthly_daily_pattern(
                ts_data.df, ts_data.sensors, air_density
            )

            atoms = build_wind_temporal_atoms(
                mast_name=mast_name,
                daily_df=daily_df,
                monthly_df=monthly_df,
                monthly_daily_df=monthly_daily_df,
            )
            all_atoms.extend(atoms)
            mast_names.append(mast_name)

        return cls(_atoms=all_atoms, _mast_names=mast_names)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )


__all__ = ["WindTemporalSection"]
