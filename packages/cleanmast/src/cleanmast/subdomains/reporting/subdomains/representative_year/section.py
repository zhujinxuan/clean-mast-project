"""Representative year calibration section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Sequence

from typst_ir import TypstHeading, TypstSection
from typst_ir.nodes import TypstBodyBlock

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.reporting.model.section_input import MesoSectionInput
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.assemble import (
    build_representative_year_atoms,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.compute import (
    RepresentativeYearMastInput,
    analyze_representative_year_calibration,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_atom import (
    MultiMastRepYearCalibrationAtom,
)


@dataclass(frozen=True)
class RepresentativeYearSection:
    """Section for multi-mast representative year calibration analysis.

    Implements the Section protocol for use with ReportBuilder.
    """

    _atoms: Sequence[ReportAtom]
    title: str = "代表年订正"
    _mast_names: list[str] | None = None

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (MultiMastRepYearCalibrationAtom, True),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[MesoSectionInput]) -> "RepresentativeYearSection":
        """Build section from mesoscale input."""
        mast_data = [
            (
                item.meso_time_series,
                item.mast_name,
                item.meso_name,
                item.rep_year_min,
                item.rep_year_max,
            )
            for item in items
        ]
        return cls.from_mast_data(mast_data)

    @classmethod
    def from_mast_data(
        cls,
        mast_data: list[tuple[TimeSeriesData, str, str, datetime, datetime]],
    ) -> "RepresentativeYearSection":
        """Build section from per-mast mesoscale time series and rep-year ranges.

        Args:
            mast_data: List of (
                meso_time_series,
                mast_name,
                meso_name,
                rep_year_min,
                rep_year_max,
            ) tuples.

        Returns:
            RepresentativeYearSection with computed atoms.
        """
        inputs: list[RepresentativeYearMastInput] = []
        mast_names: list[str] = []

        for meso_data, mast_name, meso_name, rep_min, rep_max in mast_data:
            inputs.append(
                RepresentativeYearMastInput(
                    mast_name=mast_name,
                    meso_name=meso_name,
                    meso_data=meso_data,
                    rep_year_min=rep_min,
                    rep_year_max=rep_max,
                )
            )
            mast_names.append(mast_name)

        df = analyze_representative_year_calibration(inputs)
        atoms = build_representative_year_atoms(df)
        return cls(_atoms=atoms, _mast_names=mast_names)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes.

        Args:
            images_dir: Directory for generated images.

        Returns:
            TypstSection with heading, table, and summary.
        """
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=body,
            subsections=[],
        )
