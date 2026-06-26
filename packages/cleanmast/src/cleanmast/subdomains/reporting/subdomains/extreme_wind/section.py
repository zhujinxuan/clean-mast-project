"""Extreme wind section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Sequence, cast

import polars as pl
from typst_ir import TypstHeading, TypstSection

from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.assemble import (
    build_iec_standards_atom,
    build_method1_atom,
    build_method2_atoms,
    build_method3_atom,
    build_summary_atoms,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.compute import (
    calculate_method1,
    calculate_method2,
    calculate_method3,
    compute_method2_extreme_fallback,
    extract_five_day_maxima,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.iec_atom import (
    IECStandardsAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method1_atom import (
    Method1Atom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method2_atom import (
    Method2ParamsAtom,
    Method2QQExtremeAtom,
    Method2QQSustainedAtom,
    Method2ResultAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method3_atom import (
    Method3Atom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.summary_atom import (
    ComparisonExtremeAtom,
    ComparisonSustainedAtom,
    IECWindClassAtom,
)


@dataclass(frozen=True)
class ExtremeWindSection:
    """Section for multi-mast extreme wind (fifty-year max wind) analysis.

    Implements the Section protocol for use with ReportBuilder.
    Contains 4 subsections: IEC standards, Method 1, Method 2, Method 3, Summary.
    """

    method1_atoms: list[ReportAtom] = field(default_factory=list)
    method2_atoms: list[ReportAtom] = field(default_factory=list)
    method3_atoms: list[ReportAtom] = field(default_factory=list)
    summary_atoms: list[ReportAtom] = field(default_factory=list)
    iec_atoms: list[ReportAtom] = field(default_factory=list)
    title: str = "五十年一遇最大风速"

    iec_atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (IECStandardsAtom, True),
    ]
    method1_atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (Method1Atom, True),
    ]
    method2_atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (Method2ResultAtom, True),
        (Method2ParamsAtom, False),
        (Method2QQSustainedAtom, False),
        (Method2QQExtremeAtom, False),
    ]
    method3_atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (Method3Atom, True),
    ]
    summary_atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (ComparisonSustainedAtom, True),
        (ComparisonExtremeAtom, True),
        (IECWindClassAtom, False),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        result: list[ReportAtom] = []
        result.extend(self.iec_atoms)
        result.extend(self.method1_atoms)
        result.extend(self.method2_atoms)
        result.extend(self.method3_atoms)
        result.extend(self.summary_atoms)
        return result

    @classmethod
    def _from_computed_results(
        cls,
        mast_name: str,
        method1_df: "pl.DataFrame | None" = None,
        method2_wind_df: "pl.DataFrame | None" = None,
        method2_param_df: "pl.DataFrame | None" = None,
        method3_sustained_df: "pl.DataFrame | None" = None,
        method3_extreme_df: "pl.DataFrame | None" = None,
    ) -> "ExtremeWindSection":
        """Build ExtremeWindSection from computed DataFrames.

        Args:
            mast_name: Name of the mast.
            method1_df: Method 1 result DataFrame.
            method2_wind_df: Method 2 combined wind result DataFrame.
            method2_param_df: Method 2 combined parameters DataFrame.
            method3_sustained_df: Method 3 sustained result DataFrame.
            method3_extreme_df: Method 3 extreme result DataFrame.

        Returns:
            ExtremeWindSection with all atoms assembled.
        """
        m1_atoms: list[ReportAtom] = []
        m2_atoms: list[ReportAtom] = []
        m3_atoms: list[ReportAtom] = []
        summary_atoms: list[ReportAtom] = []

        if method1_df is not None:
            m1_atoms.append(build_method1_atom(mast_name, method1_df))

        if method2_wind_df is not None and method2_param_df is not None:
            m2_atoms = list(build_method2_atoms(mast_name, method2_wind_df, method2_param_df))

        if method3_sustained_df is not None and method3_extreme_df is not None:
            m3_atoms.append(
                build_method3_atom(
                    mast_name, method3_sustained_df, method3_extreme_df
                )
            )

        if method1_df is not None:
            m2_data = method2_wind_df if method2_wind_df is not None else pl.DataFrame()
            s_df = method3_sustained_df if method3_sustained_df is not None else pl.DataFrame()
            e_df = method3_extreme_df if method3_extreme_df is not None else pl.DataFrame()
            m3_data = pl.concat([s_df, e_df])
            summary_atoms = list(
                build_summary_atoms(
                    mast_name, method1_df, m2_data, m3_data
                )
            )

        iec_atoms = [build_iec_standards_atom()]

        return cls(
            method1_atoms=m1_atoms,
            method2_atoms=m2_atoms,
            method3_atoms=m3_atoms,
            summary_atoms=summary_atoms,
            iec_atoms=iec_atoms,
        )

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes.

        Each subsection is rendered as a nested TypstSection.
        """
        subsections = self._build_subsections(images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[],
            subsections=subsections,
        )

    def _build_subsections(self, images_dir: Path) -> list[TypstSection]:
        """Build TypstSection nodes for each subsection."""
        result: list[TypstSection] = []

        # IEC standards subsection
        if self.iec_atoms:
            body = render_subsection_content(
                self.iec_atoms, self.iec_atom_configs, images_dir
            )
            result.append(TypstSection(
                heading=TypstHeading(text="IEC 标准风况等级"),
                body=body,
                subsections=[],
            ))

        # Method 1 subsection
        if self.method1_atoms:
            body = render_subsection_content(
                self.method1_atoms, self.method1_atom_configs, images_dir
            )
            result.append(TypstSection(
                heading=TypstHeading(text="五倍风速法"),
                body=body,
                subsections=[],
            ))

        # Method 2 subsection
        if self.method2_atoms:
            body = render_subsection_content(
                self.method2_atoms, self.method2_atom_configs, images_dir
            )
            result.append(TypstSection(
                heading=TypstHeading(text="五日最大法"),
                body=body,
                subsections=[],
            ))

        # Method 3 subsection
        if self.method3_atoms:
            body = render_subsection_content(
                self.method3_atoms, self.method3_atom_configs, images_dir
            )
            result.append(TypstSection(
                heading=TypstHeading(text="极端风速模型（EWM）法"),
                body=body,
                subsections=[],
            ))

        # Summary subsection
        if self.summary_atoms:
            body = render_subsection_content(
                self.summary_atoms, self.summary_atom_configs, images_dir
            )
            result.append(TypstSection(
                heading=TypstHeading(text="五十年一遇风速总结"),
                body=body,
                subsections=[],
            ))

        return result

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "ExtremeWindSection":
        """Build extreme wind section from raw mast inputs.

        For each mast: extract wind-speed data from TimeSeriesData,
        compute Method 1/2/3, assemble atoms, and aggregate them into
        a single ExtremeWindSection with list-based fields.

        Returns:
            ExtremeWindSection with all atoms for multi-mast rendering.
        """
        all_iec_atoms: list[ReportAtom] = [build_iec_standards_atom()]
        all_m1_atoms: list[ReportAtom] = []
        all_m2_atoms: list[ReportAtom] = []
        all_m3_atoms: list[ReportAtom] = []
        all_summary_atoms: list[ReportAtom] = []

        for item in items:
            ts = item.time_series
            mast_name = item.mast_name
            air_density = item.parameters.air_density

            ws_sensors = [
                s for s in ts.sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
            ]
            if not ws_sensors:
                continue

            # Filter to interested heights: 120-160m, non-interpolated (assessment: lines 88-104)
            ws_sensors = [
                s for s in ws_sensors
                if 120.0 <= s.height <= 160.0 and s.detect_interpolation_marker() != "内插"
            ]
            if not ws_sensors:
                continue

            heights = [s.height for s in ws_sensors]
            reference_height = max(heights)
            interpolation_markers = {
                s.height: s.detect_interpolation_marker() for s in ws_sensors
            }
            wind_speed_avgs = [
                cast(float, ts.df[s.column_name].mean()) for s in ws_sensors
            ]

            # ── Method 1 ──
            method1_df = calculate_method1(
                wind_speed_avgs, heights, air_density,
                reference_height, interpolation_markers,
            )

            # ── Method 2 (per height, sustained only via Gumbel) ──
            m2_wind_rows: list[dict[str, Any]] = []
            m2_param_rows: list[dict[str, Any]] = []
            for sensor in ws_sensors:
                col = sensor.column_name
                ws_series = ts.df[col]
                ts_series = ts.df["timestamp"]
                five_day_max = extract_five_day_maxima(ws_series, ts_series)
                if five_day_max.len() == 0:
                    continue

                result = calculate_method2(
                    five_day_max.to_list(),
                    sensor.height,
                    air_density,
                    reference_height,
                    "sustained",
                    sensor.detect_interpolation_marker(),
                )
                if result is None:
                    continue

                m2_wind_rows.append({
                    "height": result["height"],
                    "interpolation_marker": result.get("interpolation_marker"),
                    "wind_speed_type": result["wind_speed_type"],
                    "method": result["method"],
                    "max_wind_speed": result["max_wind_speed"],
                    "standard_density_wind_speed": result["standard_density_wind_speed"],
                    "observed_max": result.get("observed_max"),
                })
                if "mu" in result:
                    m2_param_rows.append({
                        "height": result["height"],
                        "wind_speed_type": result["wind_speed_type"],
                        "mu": result["mu"],
                        "beta": result["beta"],
                        "sample_count": result["sample_count"],
                        "sample_mean": result["sample_mean"],
                        "sample_std": result["sample_std"],
                        "sample_data": result.get("sample_data"),
                    })

                # Extreme wind via 1.4x sustained fallback (matching assessment)
                extreme_result = compute_method2_extreme_fallback(
                    cast(float, result["max_wind_speed"]),
                    result["height"],
                    air_density,
                    reference_height,
                    sensor.detect_interpolation_marker(),
                )
                m2_wind_rows.append({
                    "height": extreme_result["height"],
                    "interpolation_marker": extreme_result.get("interpolation_marker"),
                    "wind_speed_type": extreme_result["wind_speed_type"],
                    "method": extreme_result["method"],
                    "max_wind_speed": extreme_result["max_wind_speed"],
                    "standard_density_wind_speed": extreme_result["standard_density_wind_speed"],
                    "observed_max": extreme_result.get("observed_max"),
                })

            m2_wind_df = pl.DataFrame(m2_wind_rows) if m2_wind_rows else pl.DataFrame()
            m2_param_df = pl.DataFrame(m2_param_rows) if m2_param_rows else pl.DataFrame()

            # ── Method 3 (per height, both sustained and extreme) ──
            m3_sustained_rows: list[dict[str, Any]] = []
            m3_extreme_rows: list[dict[str, Any]] = []
            for sensor in ws_sensors:
                col = sensor.column_name
                obs_max = ts.df[col].max()
                if obs_max is None:
                    continue
                obs_max_f = cast(float, obs_max)
                marker = sensor.detect_interpolation_marker()

                sustained = calculate_method3(
                    obs_max_f, sensor.height, air_density,
                    reference_height, "sustained", marker,
                )
                m3_sustained_rows.append(sustained)

                extreme = calculate_method3(
                    obs_max_f, sensor.height, air_density,
                    reference_height, "extreme", marker,
                )
                m3_extreme_rows.append(extreme)

            m3_sustained_df = pl.DataFrame(m3_sustained_rows)
            m3_extreme_df = pl.DataFrame(m3_extreme_rows)

            # ── Assemble via existing _from_computed_results ──
            section = cls._from_computed_results(
                mast_name=mast_name,
                method1_df=method1_df,
                method2_wind_df=m2_wind_df if not m2_wind_df.is_empty() else None,
                method2_param_df=m2_param_df if not m2_param_df.is_empty() else None,
                method3_sustained_df=m3_sustained_df if not m3_sustained_df.is_empty() else None,
                method3_extreme_df=m3_extreme_df if not m3_extreme_df.is_empty() else None,
            )

            if section.method1_atoms:
                all_m1_atoms.extend(section.method1_atoms)
            all_m2_atoms.extend(section.method2_atoms)
            if section.method3_atoms:
                all_m3_atoms.extend(section.method3_atoms)
            all_summary_atoms.extend(section.summary_atoms)

        return cls(
            method1_atoms=all_m1_atoms,
            method2_atoms=all_m2_atoms,
            method3_atoms=all_m3_atoms,
            summary_atoms=all_summary_atoms,
            iec_atoms=all_iec_atoms,
        )

