"""Multi-mast air density atom for the reporting domain.

Compliance: Subdomain layout | Entity | Atom Pattern
"""

import math
from pathlib import Path
from typing import cast

from typing_extensions import override

from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.air_density.model.report_meta import (
    AirDensityAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.air_density.model.schemas import (
    AirDensitySchema,
)

# LOGIC-PRESERVATION: constants from assessment/shared/utils/air_density.py
_GAS_CONSTANT = 287.05  # J/(kg·K)
_GRAVITY = 9.81  # m/s²
_STD_TEMP_SEA_LEVEL = 288.15  # K
_LAPSE_RATE = 0.0065  # K/m


def _density_at_height(
    target_height: float,
    ground_density: float,
    reference_height: float,
) -> float:
    """Extrapolate air density from reference height to target height.

    LOGIC-PRESERVATION: ported from assessment calculate_air_density_for_height.
    """
    return ground_density * math.exp(
        -_GRAVITY
        * (target_height - reference_height)
        / (_GAS_CONSTANT * (_STD_TEMP_SEA_LEVEL - _LAPSE_RATE * reference_height))
    )


class MultiMastAirDensityAtom(ReportAtom[AirDensitySchema, AirDensityAtomMeta]):
    """Renders multi-mast air density table with height-adjusted values.

    - Table: mast name, avg temp, avg pressure, ground air density,
             125m, 140m, 160m air densities
    - Image: No image (returns empty Path)
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "各测风塔空气密度计算结果"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render multi-mast air density table."""
        rows: list[list[str]] = []

        for row in self.df.iter_rows(named=True):
            mast_name = cast(str, row["mast_name"])
            temperature = row["temperature"]
            pressure = row["pressure"]
            ground_air_density = cast(float, row["ground_air_density"])
            reference_height = cast(float, row.get("reference_height", 0.0))

            temp_str = f"{temperature:.2f}" if temperature is not None else "-"
            pressure_str = f"{pressure:.3f}" if pressure is not None else "-"
            rho0_str = f"{ground_air_density:.4f}"

            rho_125 = _density_at_height(125.0, ground_air_density, reference_height)
            rho_140 = _density_at_height(140.0, ground_air_density, reference_height)
            rho_160 = _density_at_height(160.0, ground_air_density, reference_height)

            rows.append(
                [
                    mast_name,
                    temp_str,
                    pressure_str,
                    rho0_str,
                    f"{rho_125:.4f}",
                    f"{rho_140:.4f}",
                    f"{rho_160:.4f}",
                ]
            )

        return TypstTable(
            headers=[
                "测风塔",
                "平均气温 (℃)",
                "平均气压 (kPa)",
                "地面空气密度 (kg/m³)",
                "125m空气密度 (kg/m³)",
                "140m空气密度 (kg/m³)",
                "160m空气密度 (kg/m³)",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for air density table."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """No summary for air density — handled at subsection level."""
        return []
