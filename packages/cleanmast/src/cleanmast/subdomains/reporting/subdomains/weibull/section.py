"""Weibull section — implements the Section protocol.

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
from cleanmast.subdomains.reporting.subdomains.weibull.assemble import (
    build_weibull_atoms,
)
from cleanmast.subdomains.reporting.subdomains.weibull.compute import (
    fit_weibull,
)
from cleanmast.subdomains.reporting.subdomains.weibull.model.weibull_atom import (
    WeibullSubgridAtom,
)


@dataclass(frozen=True)
class WeibullSection:
    """Section for Weibull distribution fitting and visualization.

    Implements the Section protocol for use with ReportBuilder.
    """

    _atoms: Sequence[ReportAtom]
    title: str = "Weibull分布拟合"
    _mast_name: str = ""

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (WeibullSubgridAtom, True),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "WeibullSection":
        """Build section from standard mast input."""
        # Guard: weibull_heights must be non-empty for each item
        for item in items:
            if not item.parameters.weibull_heights:
                raise ValueError(
                    f"{cls.__name__} requires weibull_heights for mast "
                    f"'{item.mast_name}' but it is empty; regenerate the config "
                    f"with `cleanmast recommend`"
                )

        mast_data = [
            (item.time_series, item.mast_name, item.parameters.weibull_heights)
            for item in items
        ]
        return cls.from_time_series(mast_data)

    @classmethod
    def from_time_series(
        cls,
        mast_data: list[tuple[TimeSeriesData, str, list[float]]],
    ) -> "WeibullSection":
        """Build Weibull section from time series data.

        Args:
            mast_data: List of (time_series_data, mast_name, weibull_heights) tuples.

        Returns:
            WeibullSection with computed atoms.
        """
        all_atoms: list[ReportAtom] = []

        for ts_data, mast_name, heights in mast_data:
            ws_sensors = [
                s
                for s in ts_data.sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
            ]

            fit_results = []
            for sensor in ws_sensors:
                col = sensor.column_name
                if col not in ts_data.df.columns:
                    continue
                wind_speeds = ts_data.df[col].drop_nulls().to_list()
                result = fit_weibull(wind_speeds, sensor.height)
                if result is not None:
                    fit_results.append(result)

            # Filter to configured analysis heights
            heights_set = set(heights)
            fit_results = [r for r in fit_results if r.height in heights_set]

            if fit_results:
                atoms = build_weibull_atoms(mast_name, fit_results)
                all_atoms.extend(atoms)

        mast_name = mast_data[0][1] if mast_data else ""
        return cls(_atoms=all_atoms, _mast_name=mast_name)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
