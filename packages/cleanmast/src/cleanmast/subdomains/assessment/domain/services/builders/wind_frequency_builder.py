"""Wind frequency section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_distribution_subgrid import (
    SingleMastWindDistributionSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_hours import (
    SingleMastWindFrequencyHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_power_hours import (
    SingleMastWindPowerHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_productive_range import (
    SingleMastWindProductiveRangeAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindFrequencySchema,
)


class WindFrequencySectionBuilder:
    """Builds wind frequency section from analysis results into report atoms.

    Bridges the analysis layer (WindFrequencyCalculator) with the reporting layer,
    converting analysis results into the 4 wind frequency-related report atoms.
    """

    def build(
        self,
        mast_name: str,
        results: list[AnalysisResult[WindFrequencySchema]],
    ) -> list[ReportAtom]:
        """Build wind frequency section from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            results: List of wind frequency results, one per height

        Returns:
            List of 4 report atoms in order:
            1. SingleMastWindFrequencyHoursAtom (wind frequency hours by speed bin)
            2. SingleMastWindPowerHoursAtom (power frequency hours by speed bin)
            3. SingleMastWindProductiveRangeAtom (productive range 3-25 m/s summary)
            4. SingleMastWindDistributionSubgridAtom (faceted distribution chart)
        """
        # Concatenate all results into single DataFrame
        df = pl.concat([r.data for r in results])
        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastWindFrequencyHoursAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
            SingleMastWindPowerHoursAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
            SingleMastWindProductiveRangeAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
            SingleMastWindDistributionSubgridAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
        ]

        return atoms
