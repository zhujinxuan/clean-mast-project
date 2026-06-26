"""Air density subsection implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from typst_ir import TypstEquation

from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.air_density.entities.air_density_atom import (
    MultiMastAirDensityAtom,
)
from cleanmast.subdomains.assessment.subdomains.air_density.value_objects.report_meta import (
    MultiMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.air_density.value_objects.schemas import (
    MultiMastAirDensitySchema,
)
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstHeading,
    TypstParagraph,
    TypstSection,
)
from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)


@dataclass(frozen=True)
class AirDensityService:
    """Subsection for air density calculation."""

    atoms: AtomCollection
    title: str = "空气密度计算"

    @classmethod
    def generate(
        cls,
        analysis_inputs: list[tuple[SingleMastAnalysisInput, SingleMastMeta]],
    ) -> "AirDensityService":
        """Generate air density section from analysis inputs.

        Args:
            analysis_inputs: List of (input_data, meta) tuples for multi-mast aggregation.

        Returns:
            AirDensityService containing air density analysis
        """
        rows: list[dict[str, float | str | None]] = []
        mast_names: list[str] = []

        for input_data, meta in analysis_inputs:
            mast_name = meta.mast_name
            ground_air_density = meta.air_density

            sensors = input_data.time_series.sensors
            df = input_data.time_series.df

            temp_sensor = next(
                (s for s in sensors if s.sensor_type == "Temperature" and s.stat_type == "avg"),
                None,
            )
            pressure_sensor = next(
                (s for s in sensors if s.sensor_type == "Pressure" and s.stat_type == "avg"),
                None,
            )

            temp_mean = df[temp_sensor.column_name].mean() if temp_sensor is not None else None
            pressure_mean = df[pressure_sensor.column_name].mean() if pressure_sensor is not None else None

            temperature = float(temp_mean) if temp_mean is not None else None
            pressure = float(pressure_mean) if pressure_mean is not None else None

            heights: list[float] = []
            if temp_sensor is not None:
                heights.append(temp_sensor.height)
            if pressure_sensor is not None:
                heights.append(pressure_sensor.height)
            reference_height = min(heights) if heights else 0.0

            rows.append({
                "mast_name": mast_name,
                "temperature": temperature,
                "pressure": pressure,
                "ground_air_density": ground_air_density,
                "reference_height": reference_height,
            })
            mast_names.append(mast_name)

        air_density_df = pl.DataFrame(rows)
        atom = MultiMastAirDensityAtom.create(
            MultiMastAirDensitySchema,
            air_density_df,
            MultiMastMeta(mast_names=mast_names),
        )
        collection = AtomCollection.from_dict({"_all_masts": [atom]})
        return AirDensityService(atoms=collection)

    def render_ir(self, images_dir: Path) -> TypstSection:
        """Render section to IR nodes."""
        atom_configs = [
            (MultiMastAirDensityAtom, False),
        ]

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
        body = render_subsection_content(self.atoms, atom_configs, images_dir)
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[methodology, equation, *body],
            subsections=[],
        )


AirDensitySubsection = AirDensityService
