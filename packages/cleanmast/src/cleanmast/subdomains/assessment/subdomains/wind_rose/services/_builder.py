"""Wind rose section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_atom import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_grid_atom import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_power_grid_atom import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.value_objects.schemas import (
    WindRoseSchema,
)


class WindRoseSectionBuilder:
    """Builds wind rose section from analysis results into report atoms.

    Bridges the analysis layer (WindRoseCalculator) with the reporting layer,
    converting analysis results into the 4 wind rose-related report atoms.
    """

    def build(
        self,
        mast_name: str,
        results: list[AnalysisResult[WindRoseSchema]],
    ) -> list[ReportAtom]:
        """Build wind rose section from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            results: List of wind rose results, one per height

        Returns:
            List of 4 report atoms in order:
            1. SingleMastMonthlyWindFrequencyRoseAtom (wind frequency by direction sector)
            2. SingleMastWindPowerRoseAtom (wind power density by direction sector)
            3. SingleMastMonthlyWindRoseGridAtom (monthly 3x4 grid of wind frequency roses)
            4. SingleMastMonthlyWindPowerRoseGridAtom (monthly 3x4 grid of wind power density roses)
        """
        # Concatenate all results into single DataFrame
        df = pl.concat([r.data for r in results])
        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastMonthlyWindFrequencyRoseAtom.create(
                schema=WindRoseSchema,
                df=df,
                meta=meta,
            ),
            SingleMastWindPowerRoseAtom.create(
                schema=WindRoseSchema,
                df=df,
                meta=meta,
            ),
            SingleMastMonthlyWindRoseGridAtom.create(
                schema=WindRoseSchema,
                df=df,
                meta=meta,
            ),
            SingleMastMonthlyWindPowerRoseGridAtom.create(
                schema=WindRoseSchema,
                df=df,
                meta=meta,
            ),
        ]

        return atoms
