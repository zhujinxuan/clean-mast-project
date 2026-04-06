"""Wind frequency section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_distribution import (
    SingleMastWindFrequencyDistributionAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_table import (
    SingleMastWindFrequencyTableAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_power_frequency_table import (
    SingleMastWindPowerFrequencyTableAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_range_summary import (
    SingleMastWindRangeSummaryAtom,
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
            1. SingleMastWindFrequencyTableAtom (wind frequency by speed bin)
            2. SingleMastWindPowerFrequencyTableAtom (power frequency by speed bin)
            3. SingleMastWindFrequencyDistributionAtom (visualization chart)
            4. SingleMastWindRangeSummaryAtom (productive range 3-25 m/s summary)
        """
        # Concatenate all results into single DataFrame
        df = pl.concat([r.data for r in results])
        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastWindFrequencyTableAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
            SingleMastWindPowerFrequencyTableAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
            SingleMastWindFrequencyDistributionAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
            SingleMastWindRangeSummaryAtom.create(
                schema=WindFrequencySchema,
                df=df,
                meta=meta,
            ),
        ]

        return atoms
