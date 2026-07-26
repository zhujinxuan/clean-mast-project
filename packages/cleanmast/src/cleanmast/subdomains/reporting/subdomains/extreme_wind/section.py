"""Extreme wind section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Sequence, cast

import polars as pl
from typst_ir import TypstHeading, TypstSection

from cleanmast.shared.timeseries.sensor_column import SensorColumn
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
    GumbelParamRow,
    Method1Row,
    Method2WindRow,
    Method3Result,
    _compute_density_at_height,
    _convert_to_standard,
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

        Height selection is config-driven: all WindSpeed/avg sensors whose
        height appears in the ``extreme_wind_10min_heights`` list are used
        (including interpolated fills). Extreme (3s) variants are computed
        from real WindSpeed/max sensors where available; otherwise the
        per-height gust factor from ``extreme_wind_gust_factors`` converts
        the sustained value.

        Returns:
            ExtremeWindSection with all atoms for multi-mast rendering.
        """

        all_iec_atoms: list[ReportAtom] = [build_iec_standards_atom()]
        all_m1_atoms: list[ReportAtom] = []
        all_m2_atoms: list[ReportAtom] = []
        all_m3_atoms: list[ReportAtom] = []
        all_summary_atoms: list[ReportAtom] = []

        # ── Pre-validation: every mast MUST have extreme_wind_10min_heights ──
        for item in items:
            if not item.parameters.extreme_wind_10min_heights:
                raise ValueError(
                    f"{cls.__name__} requires extreme_wind_10min_heights "
                    f"for mast '{item.mast_name}' but it is empty; "
                    f"regenerate the config with `cleanmast recommend`"
                )

        for item in items:
            ts = item.time_series
            mast_name = item.mast_name
            air_density = item.parameters.air_density

            # ── Height selection (config-driven) ──
            ten_min_heights = set(item.parameters.extreme_wind_10min_heights)
            three_s_heights = set(item.parameters.extreme_wind_3s_heights)
            # All WindSpeed/avg sensors whose height is in the 10min list
            # (INCLUDING interpolated/fill heights — user requirement)
            ws_sensors = [
                s for s in ts.sensors
                if s.sensor_type == "WindSpeed"
                and s.stat_type == "avg"
                and s.height in ten_min_heights
            ]
            # WindSpeed/max sensors keyed by height
            max_sensor_by_height: dict[float, SensorColumn] = {}
            for s in ts.sensors:
                if s.sensor_type == "WindSpeed" and s.stat_type == "max":
                    max_sensor_by_height[s.height] = s
            # ── Common per-mast values ──
            reference_height = max(s.height for s in ws_sensors)
            interpolation_markers = {
                s.height: s.detect_interpolation_marker() for s in ws_sensors
            }

            # ── Per-height gust factor lookup ──
            gust_factor_by_height: dict[float, float] = {}
            if item.parameters.extreme_wind_gust_factors:
                for gf in item.parameters.extreme_wind_gust_factors:
                    gust_factor_by_height[gf.height] = gf.gust_factor

            def _gf(h: float) -> float:
                return gust_factor_by_height.get(h, 1.4)

            # ── Method 1 ──
            # Config-driven: per-height compute so max sensors can be used
            m1_rows: list[Method1Row] = []
            for sensor in ws_sensors:
                h = sensor.height
                avg_speed = cast(float, ts.df[sensor.column_name].mean())
                sustained = 5.0 * avg_speed
                marker = interpolation_markers.get(h)

                rho_h = _compute_density_at_height(h, air_density, reference_height)
                sustained_std = _convert_to_standard(sustained, rho_h)

                m1_rows.append({
                    "height": h,
                    "interpolation_marker": marker,
                    "wind_speed_type": "sustained",
                    "method": "method1",
                    "max_wind_speed": sustained,
                    "standard_density_wind_speed": sustained_std,
                    "average_wind_speed": avg_speed,
                    "air_density": rho_h,
                })

                # Extreme: from max sensor or gust-factor fallback
                max_sensor = max_sensor_by_height.get(h)
                if max_sensor is not None and h in three_s_heights:
                    # Method 1 from real max sensor: 5x mean, no ×1.4
                    max_avg = cast(
                        float, ts.df[max_sensor.column_name].mean()
                    )
                    extreme = 5.0 * max_avg
                else:
                    extreme = sustained * _gf(h)
                extreme_std = _convert_to_standard(extreme, rho_h)

                m1_rows.append({
                    "height": h,
                    "interpolation_marker": marker,
                    "wind_speed_type": "extreme",
                    "method": "method1",
                    "max_wind_speed": extreme,
                    "standard_density_wind_speed": extreme_std,
                    "average_wind_speed": avg_speed,
                    "air_density": rho_h,
                })
            method1_df = pl.DataFrame(m1_rows) if m1_rows else pl.DataFrame()

            # ── Method 2 (per height, sustained via Gumbel; extreme from
            #    max sensor or gust-factor fallback) ──
            m2_wind_rows: list[Method2WindRow] = []
            m2_param_rows: list[GumbelParamRow] = []
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

                h = sensor.height
                max_sensor = max_sensor_by_height.get(h)
                if max_sensor is not None and h in three_s_heights:
                    # Method 2 extreme from real max sensor:
                    # run the full Gumbel pipeline on the max series
                    max_col = max_sensor.column_name
                    max_series = ts.df[max_col]
                    five_day_max_ext = extract_five_day_maxima(
                        max_series, ts_series
                    )
                    if five_day_max_ext.len() > 0:
                        extreme_result = calculate_method2(
                            five_day_max_ext.to_list(),
                            h,
                            air_density,
                            reference_height,
                            "extreme",
                            sensor.detect_interpolation_marker(),
                        )
                        if extreme_result is not None:
                            m2_wind_rows.append({
                                "height": extreme_result["height"],
                                "interpolation_marker": extreme_result.get("interpolation_marker"),
                                "wind_speed_type": extreme_result["wind_speed_type"],
                                "method": extreme_result["method"],
                                "max_wind_speed": extreme_result["max_wind_speed"],
                                "standard_density_wind_speed": extreme_result["standard_density_wind_speed"],
                                "observed_max": extreme_result.get("observed_max"),
                            })
                            # No Q-Q params for extreme variant
                else:
                    # Fallback: sustained → extreme via per-height gust factor
                    extreme_result = compute_method2_extreme_fallback(
                        result["max_wind_speed"],
                        h,
                        air_density,
                        reference_height,
                        gust_factor=_gf(h),
                        interpolation_marker=sensor.detect_interpolation_marker(),
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

            # ── Method 3 (per height, sustained + extreme) ──
            # Sustained always from avg sensor; extreme from max sensor
            # where available (1.25 × observed_max of max series),
            # otherwise same formula on avg sensor (no gust factor —
            # Method 3's ×1.25 is the EWM core factor, not a 10min→3s
            # conversion).
            m3_sustained_rows: list[Method3Result] = []
            m3_extreme_rows: list[Method3Result] = []
            for sensor in ws_sensors:
                col = sensor.column_name
                obs_max = ts.df[col].max()
                if obs_max is None:
                    continue
                obs_max_f = cast(float, obs_max)
                marker = sensor.detect_interpolation_marker()
                h = sensor.height

                sustained = calculate_method3(
                    obs_max_f, h, air_density,
                    reference_height, "sustained", marker,
                )
                m3_sustained_rows.append(sustained)

                # Extreme: from max sensor or same formula on avg data
                max_sensor = max_sensor_by_height.get(h)
                if max_sensor is not None and h in three_s_heights:
                    max_obs = ts.df[max_sensor.column_name].max()
                    if max_obs is not None:
                        extreme = calculate_method3(
                            cast(float, max_obs), h, air_density,
                            reference_height, "extreme", marker,
                        )
                    else:
                        extreme = calculate_method3(
                            obs_max_f, h, air_density,
                            reference_height, "extreme", marker,
                        )
                else:
                    # Existing derivation: 1.25 × avg-sensor observed max
                    # (no gust factor — Method 3's core is the 1.25 EWM
                    # factor, not a 10min→3s conversion)
                    extreme = calculate_method3(
                        obs_max_f, h, air_density,
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

