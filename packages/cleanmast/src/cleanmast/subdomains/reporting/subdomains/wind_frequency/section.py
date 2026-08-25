"""Wind frequency section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass
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
from cleanmast.subdomains.reporting.subdomains.wind_frequency.assemble import (
    build_wind_frequency_atoms,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.compute import (
    compute_wind_frequency,
)
from cleanmast.subdomains.reporting.subdomains.wind_frequency.model import (
    SingleMastWindDistributionSubgridAtom,
    SingleMastWindFrequencyHoursAtom,
    SingleMastWindPowerHoursAtom,
    SingleMastWindProductiveRangeAtom,
)


@dataclass(frozen=True)
class WindFrequencySection:
    """Section for single-mast wind frequency analysis.

    Implements the Section protocol for use with ReportBuilder.
    """

    _atoms: Sequence[ReportAtom]
    title: str = "风速频率分析"

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (SingleMastWindFrequencyHoursAtom, True),
        (SingleMastWindPowerHoursAtom, True),
        (SingleMastWindDistributionSubgridAtom, True),
        (SingleMastWindProductiveRangeAtom, True),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "WindFrequencySection":
        """Build section from standard mast input."""
        for item in items:
            if not item.parameters.wind_frequency_heights:
                raise ValueError(
                    f"{cls.__name__} requires wind_frequency_heights for mast '{item.mast_name}' "
                    "but it is empty; regenerate the config with `cleanmast recommend`"
                )
        mast_data = [
            (item.time_series, item.mast_name, item.parameters.air_density, item.parameters.wind_frequency_heights)
            for item in items
        ]
        return cls.from_time_series(mast_data)

    @classmethod
    def from_time_series(
        cls,
        mast_data: list[tuple[TimeSeriesData, str, float, list[float]]],
    ) -> "WindFrequencySection":
        """Build wind frequency section from time series data.

        Args:
            mast_data: List of (time_series_data, mast_name, air_density, wind_frequency_heights)
                tuples; air_density is the mast ground density from config,
                wind_frequency_heights restricts output to configured heights.

        Returns:
            WindFrequencySection with computed atoms.
        """
        computed: list[tuple[str, pl.DataFrame]] = [
            (mast_name, compute_wind_frequency(ts_data, air_density).filter(
                pl.col("height").is_in(heights)
            ))
            for ts_data, mast_name, air_density, heights in mast_data
        ]
        atoms = build_wind_frequency_atoms(computed)
        return cls(_atoms=atoms)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes.

        Args:
            images_dir: Directory for generated images.

        Returns:
            TypstSection with heading and rendered atoms.
        """
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
