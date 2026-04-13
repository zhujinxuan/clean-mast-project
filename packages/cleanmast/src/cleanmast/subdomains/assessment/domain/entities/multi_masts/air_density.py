"""Multi-mast air density atom.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import TypstParagraph, TypstTable
from cleanmast.subdomains.assessment.domain.value_objects.air_density import (
    calculate_air_density_for_height,
)
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.report_meta import (
    MultiMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.schemas import (
    MultiMastAirDensitySchema,
)


@dataclass
class MultiMastAirDensityAtom(ReportAtom[MultiMastAirDensitySchema, MultiMastMeta]):
    """Renders multi-mast air density table with height-adjusted values.

    - Table: 测风塔, 平均气温(℃), 平均气压(kPa), 地面空气密度(kg/m³),
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

            rho_125 = calculate_air_density_for_height(
                125.0, ground_air_density, reference_height
            )
            rho_140 = calculate_air_density_for_height(
                140.0, ground_air_density, reference_height
            )
            rho_160 = calculate_air_density_for_height(
                160.0, ground_air_density, reference_height
            )

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
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for air density table."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """No summary for air density — handled at subsection level."""
        return []


