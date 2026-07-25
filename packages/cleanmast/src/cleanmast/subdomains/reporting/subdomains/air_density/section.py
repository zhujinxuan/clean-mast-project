"""Air density section — implements the Section protocol.

Orchestrates: receive input → call compute → call assemble → return result.
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Sequence

from typst_ir import TypstEquation, TypstHeading, TypstParagraph, TypstSection

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.render.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.reporting.subdomains.air_density.assemble import (
    build_air_density_atoms,
)
from cleanmast.subdomains.reporting.subdomains.air_density.compute import (
    calculate_air_density,
)
from cleanmast.subdomains.reporting.subdomains.air_density.model.air_density_atom import (
    MultiMastAirDensityAtom,
)


@dataclass(frozen=True)
class AirDensitySection:
    """Section for multi-mast air density calculation.

    Implements the Section protocol for use with ReportBuilder.
    """

    _atoms: Sequence[ReportAtom]
    title: str = "空气密度计算"
    _mast_names: list[str] | None = None

    atom_configs: ClassVar[list[tuple[type[ReportAtom], bool]]] = [
        (MultiMastAirDensityAtom, False),
    ]

    @property
    def atoms(self) -> Sequence[ReportAtom]:
        return self._atoms

    @classmethod
    def from_inputs(cls, items: list[SingleMastAnalysisInput]) -> "AirDensitySection":
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
    ) -> "AirDensitySection":
        """Build air density section from time series data.

        Args:
            mast_data: List of (time_series_data, mast_name, mast_air_density) tuples.

        Returns:
            AirDensitySection with computed atoms.
        """
        rows: list[dict[str, str | float | None]] = []
        mast_names: list[str] = []

        for ts_data, mast_name, mast_air_density in mast_data:
            rho_ground = calculate_air_density(ts_data)
            sensors = ts_data.sensors

            heights: list[float] = []
            for s in sensors:
                if s.sensor_type in ("Temperature", "Pressure") and s.stat_type == "avg":
                    heights.append(s.height)
            reference_height = min(heights) if heights else 0.0

            rows.append(
                {
                    "mast_name": mast_name,
                    "temperature": _extract_mean_temp(ts_data),
                    "pressure": _extract_mean_pressure(ts_data),
                    "ground_air_density": rho_ground,
                    "reference_height": reference_height,
                }
            )
            mast_names.append(mast_name)

        atoms = build_air_density_atoms(rows)
        return cls(_atoms=atoms, _mast_names=mast_names)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes.

        Args:
            images_dir: Directory for generated images.

        Returns:
            TypstSection with heading and rendered atoms.
        """
        methodology = TypstParagraph(
            text=(
                "空气密度直接影响风能的大小，是风资源评估中的重要参数。"
                "根据《风电场风能资源评估方法》（GB/T 18710-2002），"
                "空气密度采用理想气体状态方程计算。"
                "不同高度空气密度按气压高度公式进行高度修正，"
                "其中 T = 288.15 - 0.0065 × h₀。"
            )
        )
        equation = TypstEquation(
            latex=r"rho = rho_0 times exp(- frac(g times (h - h_0), R times T))",
            display=True,
        )
        body = render_subsection_content(self._atoms, self.atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[methodology, equation, *body],
            subsections=[],
        )


def _extract_mean_temp(data: TimeSeriesData) -> float | None:
    """Extract mean temperature from time series sensors."""
    sensors = data.sensors
    df = data.df
    temp_sensor = next(
        (s for s in sensors if s.sensor_type == "Temperature" and s.stat_type == "avg"),
        None,
    )
    if temp_sensor is None or temp_sensor.column_name not in df.columns:
        return None
    val = df[temp_sensor.column_name].mean()
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return float(val)


def _extract_mean_pressure(data: TimeSeriesData) -> float | None:
    """Extract mean pressure from time series sensors."""
    sensors = data.sensors
    df = data.df
    pressure_sensor = next(
        (s for s in sensors if s.sensor_type == "Pressure" and s.stat_type == "avg"),
        None,
    )
    if pressure_sensor is None or pressure_sensor.column_name not in df.columns:
        return None
    val = df[pressure_sensor.column_name].mean()
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return float(val)
