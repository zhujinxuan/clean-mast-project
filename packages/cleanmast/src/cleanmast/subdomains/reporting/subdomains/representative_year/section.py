"""Representative year calibration section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Sequence

import polars as pl
from typst_ir import TypstHeading, TypstSection

from cleanmast.shared.timeseries import align_to_interval
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.assemble import (
    build_rep_year_sector_atoms,
    build_rep_year_summary_atom,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.compute import (
    _parse_sampling_period,
    analyze_representative_year_calibration,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_sector_figure_atom import (
    RepYearSectorFigureAtom,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_sector_table_atom import (
    RepYearSectorTableAtom,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_summary_atom import (
    RepYearSummaryAtom,
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
        (RepYearSummaryAtom, True),
        (RepYearSectorTableAtom, False),
        (RepYearSectorFigureAtom, False),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list) -> RepresentativeYearSection:
        """Build section from SingleMastAnalysisInput items.

        Items must have representative_year_calibration_payload set.
        """
        from cleanmast.subdomains.reporting.model.analysis_input import (
            SingleMastAnalysisInput,
        )

        # Filter to items with payloads
        calibrated_items = [
            item for item in items
            if isinstance(item, SingleMastAnalysisInput)
            and item.representative_year_calibration_payload is not None
        ]

        if not calibrated_items:
            return cls(_atoms=[], _mast_names=[])

        # Compute — alignment happens inside compute.py for regression only
        summaries, results = analyze_representative_year_calibration(calibrated_items)

        # Assemble summary atom
        summary_atom = build_rep_year_summary_atom(summaries)

        # Align mast and meso for figure/table atoms (post-compute)
        aligned_mast_data: dict[str, pl.DataFrame] = {}
        aligned_meso_data: dict[str, pl.DataFrame] = {}
        aligned_mast_sensors: dict[str, list] = {}
        aligned_meso_sensors: dict[str, list] = {}
        for item in calibrated_items:
            payload = item.representative_year_calibration_payload
            sampling_minutes = _parse_sampling_period(payload.sampling_period)
            aligned_mast = align_to_interval(item.time_series, sampling_minutes)
            aligned_meso = align_to_interval(payload.meso_time_series, sampling_minutes)
            aligned_mast_data[item.mast_name] = aligned_mast.df
            aligned_meso_data[item.mast_name] = aligned_meso.df
            aligned_mast_sensors[item.mast_name] = aligned_mast.sensors
            aligned_meso_sensors[item.mast_name] = aligned_meso.sensors

        # Assemble sector atoms using ALIGNED data
        table_atoms, figure_atoms = build_rep_year_sector_atoms(
            results,
            mast_data=aligned_mast_data,
            meso_data=aligned_meso_data,
            mast_sensors=aligned_mast_sensors,
            meso_sensors=aligned_meso_sensors,
        )

        mast_names = [item.mast_name for item in calibrated_items]
        atoms: list[ReportAtom] = [summary_atom, *table_atoms, *figure_atoms]
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
