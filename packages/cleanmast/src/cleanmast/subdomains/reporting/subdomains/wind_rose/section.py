"""Wind rose section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Sequence

import polars as pl
from typst_ir import TypstHeading, TypstSection

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.assemble import (
    build_wind_rose_atoms,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.compute import (
    calculate_wind_rose,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_atom import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_grid_atom import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_power_grid_atom import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)


@dataclass(frozen=True)
class WindRoseSection:
    """Section for single-mast wind rose analysis.

    Implements the Section protocol for use with ReportBuilder.
    """

    _atoms: Sequence[ReportAtom] = field(default_factory=list)
    title: str = "风向风能分布"
    _mast_name: str = ""

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (SingleMastMonthlyWindFrequencyRoseAtom, True),
        (SingleMastWindPowerRoseAtom, True),
        (SingleMastMonthlyWindRoseGridAtom, False),
        (SingleMastMonthlyWindPowerRoseGridAtom, False),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "WindRoseSection":
        """Build section from standard mast input."""
        for item in items:
            if not item.parameters.wind_rose_heights:
                raise ValueError(
                    f"{cls.__name__} requires wind_rose_heights for mast '{item.mast_name}' "
                    "but it is empty; regenerate the config with `cleanmast recommend`"
                )
        mast_data = [
            (item.time_series, item.mast_name, item.parameters.air_density, item.parameters.wind_rose_heights)
            for item in items
        ]
        return cls.from_time_series(mast_data)

    @classmethod
    def from_time_series(
        cls,
        mast_data: list[tuple[TimeSeriesData, str, float, list[float]]],
    ) -> "WindRoseSection":
        """Build wind rose section from time series data.

        Args:
            mast_data: List of (time_series_data, mast_name, air_density,
                wind_rose_heights) tuples; wind_rose_heights restricts the
                computed frame to configured heights.

        Returns:
            WindRoseSection with computed atoms.
        """
        all_atoms: list[ReportAtom] = []
        mast_name = mast_data[0][1] if mast_data else ""
        for ts_data, name, air_density, heights in mast_data:
            df = calculate_wind_rose(ts_data, air_density)
            df = df.filter(pl.col("height").is_in(heights))
            all_atoms.extend(build_wind_rose_atoms(name, df))
        return cls(_atoms=all_atoms, _mast_name=mast_name)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes.

        Args:
            images_dir: Directory for generated images.

        Returns:
            TypstSection with heading, body, and subsections.
        """
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
