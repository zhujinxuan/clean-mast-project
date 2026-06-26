"""Wind rose section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Sequence

from typst_ir import TypstHeading, TypstSection

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.model.analysis_parameters import AnalysisParameters
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
        all_atoms: list[ReportAtom] = []
        mast_name = items[0].mast_name if items else ""
        for item in items:
            df = calculate_wind_rose(item.time_series, item.parameters.air_density)
            atoms = build_wind_rose_atoms(item.mast_name, df)
            all_atoms.extend(atoms)
        return cls(_atoms=all_atoms, _mast_name=mast_name)

    @classmethod
    def from_time_series(
        cls,
        time_series: TimeSeriesData,
        mast_name: str,
        air_density: float,
    ) -> "WindRoseSection":
        """Build wind rose section from a single mast's time series data.

        Args:
            time_series: TimeSeriesData with wind speed and direction sensors
            mast_name: Name of the mast
            air_density: Air density in kg/m³

        Returns:
            WindRoseSection with computed atoms.
        """
        return cls.from_inputs(
            [
                SingleMastAnalysisInput(
                    time_series=time_series,
                    parameters=AnalysisParameters(heights=[], air_density=air_density),
                    mast_name=mast_name,
                )
            ]
        )

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
